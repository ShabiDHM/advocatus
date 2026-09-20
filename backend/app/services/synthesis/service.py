# FILE: backend/app/services/synthesis/service.py
# PHOENIX PROTOCOL - SYNTHESIS SERVICE V4.2 (modular + parallel + role fix)
# V4.2: Shtuar forbidden_parties detection — fëmijët dhe anëtarët familjarë
#       nuk klasifikohen si palë nga post-processing. Deterministik, jo-LLM.
# V4.1: PARALLEL SECTIONS — ThreadPoolExecutor me max_workers=5 (env override).
# V4.0: Modularizuar nga synthesis_service.py V3.8 — ZERO ndryshim funksional.

import os
import re
import time
import logging
import concurrent.futures
from typing import Any, Dict, List, Optional, Callable, Set
from datetime import datetime, timezone

from .canonical import CanonicalEntities
from .case_types import detect_case_type
from .citation_extraction import (
    extract_verified_citations_from_documents,
    extract_articles_by_law,
)
from .digest import build_digest
from .guardrails import (
    verify_citations_word_by_word,
    verify_attribution_word_by_word,
    detect_deadline_contradictions,
    correct_citations_with_llm,
)
from .post_processing import post_process_output
from .streaming import synthesize_section_streaming
from .persistence import (
    load_case,
    load_extractions,
    load_cross_refs,
    persist,
    empty_result,
    load as load_synthesis,
)
from .prompts import SECTION_PROMPTS

logger = logging.getLogger(__name__)


# V4.1: Konfigurim paralelizmi
MAX_CONCURRENT_SECTIONS = int(os.environ.get("SYNTHESIS_MAX_WORKERS", "3"))

# Seksionet qe kane guardrails (korrigjim pas generimit)
GUARDRAIL_SECTIONS = {
    "legal_framework",
    "recommendations",
    "executive_summary",
    "key_findings_contradictions",
}


# ═══════════════════════════════════════════════════════════════════════════
# V4.2: FORBIDDEN PARTY NAMES — nga metadata.parties me role "Fëmijët"
# ═══════════════════════════════════════════════════════════════════════════

def _extract_forbidden_party_names(
    extractions: List[Dict[str, Any]],
) -> Set[str]:
    """
    V4.2: Nxjerr emrat që NUK duhet të klasifikohen si palë ndërgjyqëse.
    Bazuar në rolet "Fëmijët" / "Fëmijë" nga metadata.parties.

    Kthen: set me emra (lowercase, emri i parë + emri i plotë).
    """
    forbidden: Set[str] = set()
    for ext in extractions or []:
        meta = ext.get("metadata") or {}
        if not isinstance(meta, dict):
            continue
        for p in meta.get("parties", []) or []:
            if not isinstance(p, dict):
                continue
            role = (p.get("role") or "").lower()
            name = (p.get("name") or "").strip()
            if not name:
                continue
            if "fëmij" in role or "femij" in role:
                # Split "Elda dhe Andi" → ["Elda", "Andi"]
                parts = re.split(
                    r'\s+(?:dhe|dhe\/ose|,|e)\s+',
                    name,
                    flags=re.IGNORECASE,
                )
                for part in parts:
                    part = part.strip(" .,;:")
                    if not part:
                        continue
                    forbidden.add(part)
                    # Gjithashtu shto emrin e parë
                    first = part.split()[0] if part.split() else ""
                    if first and len(first) >= 3:
                        forbidden.add(first)
    return forbidden


class SynthesisService:
    """
    V4.2 (modular + parallel + role fix) — orchestration vetem.
    """

    def __init__(self, db):
        self.db = db
        # Lazy import për të shmangur ciklin
        from app.services.defendant_group_extractor import get_defendant_group_extractor
        self.defendant_extractor = get_defendant_group_extractor(db)

    # ────────────────────────────────────────────────────────────────────
    # PUBLIC — synthesize
    # ────────────────────────────────────────────────────────────────────

    def synthesize(
        self,
        case_id: str,
        user_id: str = "",
        progress_callback: Optional[Callable] = None,
        section_stream_callback: Optional[Callable[[str, str], None]] = None,
    ) -> Dict[str, Any]:
        start = time.time()

        case = load_case(self.db, case_id)
        extractions = load_extractions(self.db, case_id)
        xrefs = load_cross_refs(self.db, case_id)

        if not extractions:
            return empty_result(case_id, "No extractions found.")

        defendants_groups = self.defendant_extractor.extract_for_case(
            case_id, force=False
        )

        case_type = detect_case_type(self.db, case_id, extractions)
        logger.info(f"🎯 [SYNTHESIS V4.2] Case type detected: {case_type}")

        canonical = self._build_canonical_entities(extractions, defendants_groups)
        logger.info(f"🎯 [SYNTHESIS V4.2] Canonical entities: {canonical.stats()}")

        articles_by_law = extract_articles_by_law(self.db, case_id)
        total_articles = sum(len(v) for v in articles_by_law.values())

        verified_citations = extract_verified_citations_from_documents(self.db, case_id)
        logger.info(
            f"🔒 [GUARDRAIL #2b] Verified citations: "
            f"laws={verified_citations['total_laws']}, "
            f"articles={verified_citations['total_articles']}, "
            f"pairs={verified_citations['total_pairs']}"
        )

        doc_articles_available: Set[str] = {
            a["number"] for a in verified_citations.get("articles", [])
        }

        digest = build_digest(
            case, extractions, xrefs, defendants_groups,
            articles_by_law, case_type, verified_citations
        )
        logger.info(
            f"🔍 [SYNTHESIS V4.2] Digest built: {len(digest)} chars, "
            f"case_type={case_type or 'unknown'}, "
            f"docs={len(extractions)}, "
            f"verified_laws={verified_citations['total_laws']}, "
            f"verified_articles={verified_citations['total_articles']}, "
            f"verified_pairs={verified_citations['total_pairs']}, "
            f"case={case_id}"
        )

        # ═══════════════════════════════════════════════════════════════
        # V4.2: Forbidden parties (fëmijët) — për post-processing
        # ═══════════════════════════════════════════════════════════════
        forbidden_parties = _extract_forbidden_party_names(extractions)
        if forbidden_parties:
            logger.info(
                f"🚫 [SYNTHESIS V4.2] Forbidden party names (children): "
                f"{sorted(forbidden_parties)}"
            )
        else:
            logger.info(
                f"🚫 [SYNTHESIS V4.2] No forbidden party names detected"
            )

        # ═══════════════════════════════════════════════════════════════
        # V4.1: Procesim PARALEL i seksioneve
        # ═══════════════════════════════════════════════════════════════

        sections: Dict[str, Any] = {}
        section_stats: Dict[str, Any] = {}
        guardrail_reports: Dict[str, Any] = {}
        all_deadline_contradictions: List[Dict[str, Any]] = []

        total_hallucinations_fixed = 0
        total_institutions_fixed = 0
        total_prefix_fixes = 0
        total_citation_fixes = 0
        total_attribution_fixes = 0
        total_misattributed_roles_fixed = 0

        logger.warning(
            f"🚀 [SYNTHESIS V4.2] Nisur {len(SECTION_PROMPTS)} seksione "
            f"me max_workers={MAX_CONCURRENT_SECTIONS}"
        )

        def _run_section_worker(
            section_key: str,
            section_cfg: Dict[str, Any],
        ) -> Dict[str, Any]:
            """
            V4.1: Ekzekuton nje seksion te vetem ne thread te pavarur.
            Kthen dict me rezultatet per merge ne main thread.
            """
            section_start = time.time()
            section_title = section_cfg["title"]

            if progress_callback:
                try:
                    progress_callback("section_started", {
                        "section_key": section_key,
                        "section_title": section_title,
                    })
                except Exception:
                    pass

            section_entry: Dict[str, Any] = {}
            stat_entry: Dict[str, Any] = {}
            gr_report: Optional[Dict[str, Any]] = None
            fixes: Dict[str, int] = {}
            deadline_contradictions: List[Dict[str, Any]] = []

            try:
                raw_content = synthesize_section_streaming(
                    section_key=section_key,
                    section_cfg=section_cfg,
                    digest=digest,
                    case=case,
                    stream_callback=section_stream_callback,
                )

                # ═══════════════════════════════════════════════════════
                # V4.2: post_process_output me forbidden_parties
                # ═══════════════════════════════════════════════════════
                content, fix_stats = post_process_output(
                    raw_content,
                    canonical,
                    forbidden_parties=forbidden_parties,
                )

                fixes = {
                    "hallucinations_fixed": fix_stats.get("hallucinations_fixed", 0),
                    "institutions_fixed": fix_stats.get("institutions_fixed", 0),
                    "prefix_fixes": fix_stats.get("prefix_fixes", 0),
                    "misattributed_roles_fixed": fix_stats.get("misattributed_roles_fixed", 0),
                    "citation_fixes": 0,
                    "attribution_fixes": 0,
                }

                if section_key in GUARDRAIL_SECTIONS and content:
                    logger.info(f"🔍 [GUARDRAILS] Checking {section_key}...")

                    checker_report = verify_citations_word_by_word(
                        content, doc_articles_available
                    )
                    attribution_report = verify_attribution_word_by_word(
                        content, verified_citations
                    )
                    deadline_report = detect_deadline_contradictions(content)

                    gr_report = {
                        "citations": checker_report,
                        "attributions": attribution_report,
                        "deadlines": deadline_report,
                    }

                    logger.info(
                        f"📊 [GUARDRAIL #4] {section_key}: "
                        f"citations_verified={len(checker_report['verified'])}, "
                        f"citations_unverified={len(checker_report['unverified'])}, "
                        f"attributions_unverified={len(attribution_report.get('unverified', []))}, "
                        f"deadlines_contradictions={len(deadline_report.get('contradictions', []))}"
                    )

                    if deadline_report.get("contradictions"):
                        deadline_contradictions = [
                            {**c, "section": section_key}
                            for c in deadline_report["contradictions"]
                        ]

                    has_citation_issues = bool(checker_report.get("unverified"))
                    has_attribution_issues = bool(attribution_report.get("unverified"))

                    if has_citation_issues or has_attribution_issues:
                        logger.info(
                            f"🔧 [GUARDRAIL #3] Correcting {section_key} — "
                            f"citations={len(checker_report.get('unverified', []))}, "
                            f"attributions={len(attribution_report.get('unverified', []))}"
                        )
                        corrected_content = correct_citations_with_llm(
                            content, checker_report, attribution_report, verified_citations
                        )

                        report_after_cit = verify_citations_word_by_word(
                            corrected_content, doc_articles_available
                        )
                        report_after_attr = verify_attribution_word_by_word(
                            corrected_content, verified_citations
                        )
                        logger.info(
                            f"✅ [GUARDRAIL #3] {section_key} after correction: "
                            f"citations_hall_rate={report_after_cit['hallucination_rate']}%, "
                            f"attributions_hall_rate={report_after_attr.get('hallucination_rate', 0)}%"
                        )

                        fixes["citation_fixes"] = len(checker_report.get("unverified", []))
                        fixes["attribution_fixes"] = len(attribution_report.get("unverified", []))
                        content = corrected_content
                        gr_report["after_correction"] = {
                            "citations": report_after_cit,
                            "attributions": report_after_attr,
                        }

                section_entry = {
                    "title": section_title,
                    "content": content,
                }
                stat_entry = {
                    "duration_sec": round(time.time() - section_start, 2),
                    "content_length": len(content),
                    "hallucinations_fixed": fixes["hallucinations_fixed"],
                    "institutions_fixed": fixes["institutions_fixed"],
                    "prefix_fixes": fixes["prefix_fixes"],
                    "misattributed_roles_fixed": fixes["misattributed_roles_fixed"],
                }

                if progress_callback:
                    try:
                        progress_callback("section_completed", {
                            "section_key": section_key,
                            "section_title": section_title,
                            "content_length": len(content),
                        })
                    except Exception:
                        pass

            except Exception as e:
                logger.error(f"❌ [SYNTHESIS V4.2] Section {section_key} failed: {e}")
                section_entry = {
                    "title": section_title,
                    "content": "",
                    "error": str(e),
                }
                stat_entry = {
                    "duration_sec": round(time.time() - section_start, 2),
                    "error": str(e),
                }

            return {
                "section_key": section_key,
                "section_entry": section_entry,
                "stat_entry": stat_entry,
                "guardrail_report": gr_report,
                "fixes": fixes,
                "deadline_contradictions": deadline_contradictions,
            }

        # ──────────────────────────────────────────────────────────────
        # Ekzekutim paralel me ThreadPoolExecutor
        # ──────────────────────────────────────────────────────────────
        try:
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=MAX_CONCURRENT_SECTIONS,
                thread_name_prefix="synth",
            ) as executor:
                futures = {
                    executor.submit(_run_section_worker, k, c): k
                    for k, c in SECTION_PROMPTS.items()
                }

                for fut in concurrent.futures.as_completed(futures):
                    section_key = futures[fut]
                    try:
                        res = fut.result()
                    except Exception as e:
                        logger.error(
                            f"❌ [SYNTHESIS V4.2] Future failed for {section_key}: {e}"
                        )
                        sections[section_key] = {
                            "title": SECTION_PROMPTS[section_key]["title"],
                            "content": "",
                            "error": str(e),
                        }
                        section_stats[section_key] = {"error": str(e)}
                        continue

                    sections[res["section_key"]] = res["section_entry"]
                    section_stats[res["section_key"]] = res["stat_entry"]

                    if res.get("guardrail_report"):
                        guardrail_reports[res["section_key"]] = res["guardrail_report"]

                    fixes = res.get("fixes", {}) or {}
                    total_hallucinations_fixed += fixes.get("hallucinations_fixed", 0)
                    total_institutions_fixed += fixes.get("institutions_fixed", 0)
                    total_prefix_fixes += fixes.get("prefix_fixes", 0)
                    total_citation_fixes += fixes.get("citation_fixes", 0)
                    total_attribution_fixes += fixes.get("attribution_fixes", 0)
                    total_misattributed_roles_fixed += fixes.get("misattributed_roles_fixed", 0)

                    if res.get("deadline_contradictions"):
                        all_deadline_contradictions.extend(res["deadline_contradictions"])

        except Exception as e:
            logger.error(f"❌ [SYNTHESIS V4.2] ThreadPoolExecutor failed: {e}")
            # Fallback: sequential
            logger.warning("🔄 [SYNTHESIS V4.2] Fallback në sequential mode")
            for section_key, section_cfg in SECTION_PROMPTS.items():
                try:
                    res = _run_section_worker(section_key, section_cfg)
                    sections[section_key] = res["section_entry"]
                    section_stats[section_key] = res["stat_entry"]
                    if res.get("guardrail_report"):
                        guardrail_reports[section_key] = res["guardrail_report"]
                    fixes = res.get("fixes", {}) or {}
                    total_hallucinations_fixed += fixes.get("hallucinations_fixed", 0)
                    total_institutions_fixed += fixes.get("institutions_fixed", 0)
                    total_prefix_fixes += fixes.get("prefix_fixes", 0)
                    total_citation_fixes += fixes.get("citation_fixes", 0)
                    total_attribution_fixes += fixes.get("attribution_fixes", 0)
                    total_misattributed_roles_fixed += fixes.get("misattributed_roles_fixed", 0)
                    if res.get("deadline_contradictions"):
                        all_deadline_contradictions.extend(res["deadline_contradictions"])
                except Exception as e2:
                    logger.error(f"❌ [SEQUENTIAL FALLBACK] {section_key}: {e2}")

        # V4.1: Rendit seksionet sipas definicionit
        sections = {k: sections[k] for k in SECTION_PROMPTS.keys() if k in sections}
        section_stats = {
            k: section_stats[k] for k in SECTION_PROMPTS.keys() if k in section_stats
        }

        duration = round(time.time() - start, 2)

        result = {
            "case_id": case_id,
            "scope": "case",
            "case_type": case_type,
            "built_at": datetime.now(timezone.utc).isoformat(),
            "case_title": case.get("title") or case.get("case_name"),
            "sections": sections,
            "stats": {
                "case_id": case_id,
                "scope": "case",
                "case_type": case_type,
                "documents_analyzed": len(extractions),
                "digest_chars": len(digest),
                "defendant_groups_count": len(defendants_groups),
                "defendants_total": sum(
                    len(g.get("defendants", [])) for g in defendants_groups
                ),
                "article_laws_count": len(articles_by_law),
                "article_descriptions_count": total_articles,
                "verified_laws_count": verified_citations["total_laws"],
                "verified_articles_count": verified_citations["total_articles"],
                "verified_pairs_count": verified_citations["total_pairs"],
                "canonical_persons": canonical.stats()["persons"],
                "canonical_organizations": canonical.stats()["organizations"],
                "hallucinations_fixed": total_hallucinations_fixed,
                "institutions_fixed": total_institutions_fixed,
                "prefix_fixes": total_prefix_fixes,
                "misattributed_roles_fixed": total_misattributed_roles_fixed,
                "citation_hallucinations_fixed": total_citation_fixes,
                "attribution_hallucinations_fixed": total_attribution_fixes,
                "deadline_contradictions": len(all_deadline_contradictions),
                "sections_generated": len(
                    [s for s in sections.values() if s.get("content")]
                ),
                "sections_total": len(SECTION_PROMPTS),
                "duration_sec": duration,
                "execution_mode": f"parallel_x{MAX_CONCURRENT_SECTIONS}",
                "forbidden_parties": sorted(forbidden_parties) if forbidden_parties else [],
            },
            "guardrail_reports": guardrail_reports,
            "regex_verified_citations": verified_citations,
            "deadline_contradictions": all_deadline_contradictions,
            "section_stats": section_stats,
            "status": "completed",
        }

        persist(self.db, result)

        logger.info(
            f"✅ [SYNTHESIS V4.2] Complete: case={case_id}, "
            f"case_type={case_type}, "
            f"hallucinations_fixed={total_hallucinations_fixed}, "
            f"misattributed_roles_fixed={total_misattributed_roles_fixed}, "
            f"citation_hallucinations_fixed={total_citation_fixes}, "
            f"attribution_hallucinations_fixed={total_attribution_fixes}, "
            f"deadline_contradictions={len(all_deadline_contradictions)}, "
            f"sections={result['stats']['sections_generated']}/{result['stats']['sections_total']}, "
            f"duration={duration}s, mode={result['stats']['execution_mode']}"
        )

        return result

    # ────────────────────────────────────────────────────────────────────
    # CANONICAL ENTITIES BUILDER
    # ────────────────────────────────────────────────────────────────────

    def _build_canonical_entities(self, extractions, defendants_groups):
        canonical = CanonicalEntities()

        for ext in extractions:
            ebt = ext.get("entities_by_type", {})
            for label, role_name in [
                ("PARTY", "Palë"),
                ("JUDGE", "Gjyqtar"),
                ("PROSECUTOR", "Prokuror"),
                ("LAWYER", "Avokat"),
                ("WITNESS", "Dëshmitar"),
            ]:
                for item in ebt.get(label, []):
                    name = (item.get("text") or "").strip()
                    if name:
                        canonical.add_person(name, role=role_name)

            for item in ebt.get("ORGANIZATION", []):
                name = (item.get("text") or "").strip()
                if name:
                    canonical.add_organization(name)

            for item in ebt.get("CASE_NUMBER", []):
                cn = (item.get("text") or "").strip()
                if cn:
                    canonical.add_case_number(cn)

        for ext in extractions:
            meta = ext.get("metadata") or {}
            for p in meta.get("parties", []):
                if not isinstance(p, dict):
                    continue
                name = (p.get("name") or "").strip()
                role = (p.get("role") or "").strip()
                if name:
                    canonical.add_person(name, role=role)

            court = meta.get("court")
            if court:
                canonical.add_organization(str(court).strip())

            judge = meta.get("judge")
            if judge:
                canonical.add_person(str(judge).strip(), role="Gjyqtar")

        for group in defendants_groups:
            for d in group.get("defendants", []):
                name = (d.get("name") or "").strip()
                role = (d.get("role") or "").strip()
                if name:
                    canonical.add_person(name, role=role)

        return canonical

    # ────────────────────────────────────────────────────────────────────
    # PUBLIC — load
    # ────────────────────────────────────────────────────────────────────

    def load(self, case_id: str) -> Optional[Dict[str, Any]]:
        return load_synthesis(self.db, case_id)


# ────────────────────────────────────────────────────────────────────────
# FACTORY
# ────────────────────────────────────────────────────────────────────────

def get_synthesis_service(db) -> SynthesisService:
    return SynthesisService(db)