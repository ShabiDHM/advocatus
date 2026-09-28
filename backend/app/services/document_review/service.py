# FILE: backend/app/services/document_review/service.py
# PHOENIX PROTOCOL - DOCUMENT REVIEW SERVICE V5.29
# V5.29: DYNAMIC DB LAWS — Integrim i get_all_law_numbers_from_db().
#        Në fillim të hallucination check, lexon të gjitha ligjet e njohura
#        nga legal_knowledge_base dhe i kalon si extra_allowed_laws tek
#        check_all_sections. Zero hardcoding — çdo ligj i shtuar në DB
#        automatikisht i lejuar.
# V5.28: QUALITY METRICS.
# V5.27: PROFESSIONAL LANGUAGE.
# V5.26: (P1 fix).
# V5.25: FORENSIC FINDINGS.
# V5.24: CASE CONTEXT.
# V5.23: BATCH MERGE.

import os
import re
import time
import logging
import threading
import concurrent.futures
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Callable, Tuple, Set

from .citation_extractor import build_citation_profile
from .fact_extractor import build_fact_profile
from .case_profile import build_case_profile
from .forensic_service import (
    run_forensic_analysis,
    extract_allowed_values_from_flags,
)
from .mongo_verifier import verify_all
from .mongo_verifier.laws import get_all_law_numbers_from_db
from .prompts import (
    DOCUMENT_REVIEW_PROMPTS,
    build_verified_context,
    SECTION_CONTEXT_MAP,
)
from .streaming import synthesize_section_streaming
from .report_builder import build_full_report
from .hallucination_checker import check_all_sections
from .quality_metrics import compute_quality_metrics, log_quality_metrics
from .precedent_search import (
    build_precedent_query,
    search_relevant_precedents,
    PRECEDENT_SIMILARITY_THRESHOLD,
    PRECEDENT_TOP_K,
)
from .persistence import (
    load_document, load_extraction, persist, empty_result,
)

logger = logging.getLogger(__name__)

MAX_CONCURRENT_SECTIONS = int(os.getenv("DOC_REVIEW_MAX_WORKERS", "3"))
DEFAULT_SECTION_MAX_TOKENS = 3000

ARTICLE_VERIFICATION_SPLIT_THRESHOLD = int(
    os.getenv("ARTICLE_VERIFICATION_SPLIT_THRESHOLD", "10")
)
ARTICLE_VERIFICATION_BATCHES = int(
    os.getenv("ARTICLE_VERIFICATION_BATCHES", "3")
)

# ═══════════════════════════════════════════════════════════════════════════
# CONCISE SUFFIXES
# ═══════════════════════════════════════════════════════════════════════════

ARTICLE_VERIFICATION_CONCISE_SUFFIX = """

═══════════════════════════════════════════════════════════════════════════
⚡ UDHËZIM KONCIZIONI (VETËM PËR KËTË SEKSION)
═══════════════════════════════════════════════════════════════════════════
Për ÇDO nen të listuar, jep VETËM: Numrin + ligjin, Statusin, Arsyetim me NJË FJALI.
MAKSIMUM 2 rreshta për nen.
"""

ACTION_STEPS_CONCISE_SUFFIX = """

═══════════════════════════════════════════════════════════════════════════
⚡ UDHËZIM KONCIZIONI (VETËM PËR KËTË SEKSION)
═══════════════════════════════════════════════════════════════════════════
Për ÇDO veprim: emri (5-10 fjalë), bazë ligjore (1 fjali), prioritet.

STRUKTURA:
### A. Vlerësimi i Situatës (2-3 fjali)
### B. Hapat e Menjëhershëm (1-7 ditë)
### C. Hapat Afatgjatë (1-3 muaj)
### D. Mundësitë Procedurale
### E. Rreziqet
### F. Referencat Konkrete
### G. Veprime Kritike që Mund të Mungojnë
"""

ANALIZA_E_THELLUAR_CONCISE_SUFFIX = """

═══════════════════════════════════════════════════════════════════════════
⚡ UDHËZIM KONCIZIONI (VETËM PËR KËTË SEKSION)
═══════════════════════════════════════════════════════════════════════════
Për ÇDO shenjë: titull (3-7 fjalë), vëzhgim (1-2 fjali), bazë në fakte.
MAKSIMUM 3 rreshta për shenjë. 5-7 shenja TOTAL.
"""

SECTION_CONCISE_SUFFIXES: Dict[str, str] = {
    "article_verification": ARTICLE_VERIFICATION_CONCISE_SUFFIX,
    "action_steps": ACTION_STEPS_CONCISE_SUFFIX,
    "analiza_e_thelluar": ANALIZA_E_THELLUAR_CONCISE_SUFFIX,
}


# ═══════════════════════════════════════════════════════════════════════════
# V5.23: MERGE ARTICLES BY HEADING
# ═══════════════════════════════════════════════════════════════════════════

_HEADING_RE = re.compile(r'^###\s+([A-G])\.\s*(.+)$', re.MULTILINE)

_SECTION_TITLES = {
    "A": "### A. Nene problematike",
    "B": "### B. Nene që mund të mungojnë",
    "C": "### C. Përmbledhje statistikore",
}


def _parse_batch_sections(content: str) -> Dict[str, str]:
    if not content:
        return {}
    matches = list(_HEADING_RE.finditer(content))
    if not matches:
        return {}
    result: Dict[str, str] = {}
    for i, m in enumerate(matches):
        letter = m.group(1)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        sc = content[start:end].strip()
        if sc:
            result[letter] = sc
    return result


def _merge_article_verification_batches(contents: List[str]) -> str:
    non_empty = [c for c in contents if c and c.strip()]
    if not non_empty:
        return ""
    if len(non_empty) == 1:
        return non_empty[0].strip()

    parsed = [_parse_batch_sections(c) for c in non_empty]
    out_lines: List[str] = []

    for letter in ("A", "B", "C"):
        all_content = [p.get(letter, "").strip() for p in parsed if p.get(letter)]
        if not all_content:
            continue
        combined = "\n\n".join(all_content)
        paragraphs = re.split(r'\n\s*\n', combined)
        seen: Set[str] = set()
        unique: List[str] = []
        for para in paragraphs:
            para_clean = para.strip()
            if not para_clean:
                continue
            key = re.sub(r'\s+', ' ', para_clean.lower())[:400]
            if key in seen:
                continue
            seen.add(key)
            unique.append(para_clean)
        if not unique:
            continue
        out_lines.append(_SECTION_TITLES.get(letter, f"### {letter}."))
        out_lines.append("")
        for u in unique:
            out_lines.append(u)
            out_lines.append("")

    result = "\n".join(out_lines).strip()
    logger.info(f"🧹 [V5.29 MERGE] {len(non_empty)} batches → {len(result)} chars")
    return result


# ═══════════════════════════════════════════════════════════════════════════
# SERVICE
# ═══════════════════════════════════════════════════════════════════════════

class DocumentReviewService:

    def __init__(self, db):
        self.db = db

    def review(
        self,
        case_id: str,
        user_id: str,
        document_id: str,
        progress_callback: Optional[Callable] = None,
        section_stream_callback: Optional[Callable[[str, str], None]] = None,
        client_name: Optional[str] = None,
        client_position: Optional[str] = None,
    ) -> Dict[str, Any]:
        start = time.time()

        def _lap(label: str, t_start: float) -> float:
            elapsed = time.time() - t_start
            logger.info(f"⏱️ [TIMING] {label}: {elapsed:.2f}s")
            return elapsed

        # ═══ 1. LOAD ═══
        t0 = time.time()
        document = load_document(self.db, case_id, document_id)
        extraction = load_extraction(self.db, case_id, document_id)
        _lap("load_document+extraction", t0)

        if not document and not extraction:
            return empty_result(case_id, document_id, "Document not found.")

        doc_text = (
            (extraction or {}).get("text")
            or document.get("content")
            or document.get("extracted_text")
            or document.get("text")
            or ""
        )
        if not doc_text.strip():
            return empty_result(case_id, document_id, "No text content.")

        document_type = (
            (extraction or {}).get("document_type")
            or document.get("document_type")
            or "Dokument"
        )
        file_name = document.get("file_name", "Dokument")

        logger.info(
            f"🔍 [DOC_REVIEW V5.29] Starting: doc={document_id}, "
            f"file={file_name}, type={document_type}, len={len(doc_text)} chars, "
            f"client={client_name or '?'} ({client_position or '?'}), "
            f"parallel x{MAX_CONCURRENT_SECTIONS}"
        )

        # ═══ 2. LABORATORI ═══
        if progress_callback:
            try:
                progress_callback("step_started", {
                    "step_key": "extraction",
                    "step_title": "Duke nxjerrë citimet nga dokumenti...",
                })
            except Exception:
                pass

        t0 = time.time()
        citation_profile = build_citation_profile(doc_text)
        citation_time = _lap("build_citation_profile", t0)

        t0 = time.time()
        fact_profile = build_fact_profile(doc_text, source_document=file_name)
        fact_time = _lap("build_fact_profile", t0)

        logger.info(
            f"🔬 [EXTRACT] Articles={citation_profile['stats']['total_articles']}, "
            f"Laws={citation_profile['stats']['total_laws_by_number']}, "
            f"CaseNumbers={citation_profile['stats']['total_case_numbers']}, "
            f"Dates={fact_profile['stats']['total_dates']}"
        )

        # ═══ 2.5 CASE PROFILE ═══
        t0 = time.time()
        case_profile: Dict[str, Any] = {}
        try:
            case_profile = build_case_profile(
                self.db, case_id, exclude_doc_id=document_id,
            )
            if case_profile.get("has_context"):
                logger.info(
                    f"📚 [CASE_PROFILE V5.29] Aktiv: "
                    f"docs={case_profile['stats']['documents_scanned']}, "
                    f"subjects={case_profile['stats']['unique_subjects']}, "
                    f"block_chars={len(case_profile.get('block', ''))}"
                )
        except Exception as e:
            logger.warning(f"⚠️ [CASE_PROFILE] Dështoi: {e}")
            case_profile = {}
        _lap("build_case_profile", t0)

        # ═══ 2.6 KONSTATIMET E ANALIZËS ═══
        t0 = time.time()
        forensic_result = None
        forensic_dict: Dict[str, Any] = {}
        try:
            forensic_result = run_forensic_analysis(
                self.db, case_id,
                exclude_doc_id=document_id,
                document_type=document_type,
            )
            if forensic_result.has_findings:
                forensic_dict = forensic_result.to_dict()
                logger.info(
                    f"🔴 [KONSTATIMET V5.29] Aktive: "
                    f"profile={forensic_result.profile_used}, "
                    f"total={len(forensic_result.flags)}, "
                    f"block_chars={len(forensic_result.block)}"
                )
            else:
                logger.info(f"ℹ️ [KONSTATIMET V5.29] Pa konstatime.")
        except Exception as e:
            logger.warning(f"⚠️ [KONSTATIMET V5.29] Dështoi: {e}")
            forensic_result = None
        _lap("run_forensic_analysis", t0)

        # ═══ 3. ARKIVA ═══
        if progress_callback:
            try:
                progress_callback("step_started", {
                    "step_key": "verification",
                    "step_title": "Duke verifikuar citimet...",
                })
            except Exception:
                pass

        t0 = time.time()
        verification_report = verify_all(self.db, citation_profile)
        verify_time = _lap("verify_all (MongoDB)", t0)

        logger.info(
            f"📚 [VERIFY] Articles {verification_report['stats']['articles_verified']}/"
            f"{verification_report['stats']['articles_total']}, "
            f"Laws {verification_report['stats']['laws_verified']}/"
            f"{verification_report['stats']['laws_total']}, "
            f"Precedents {verification_report['stats']['precedents_verified']}/"
            f"{verification_report['stats']['case_numbers_cited']}"
        )

        # ═══ 4. NARRATIVE — PARALLEL ═══
        sections: Dict[str, Any] = {}
        section_stats: Dict[str, Any] = {}
        sections_start = time.time()

        logger.info(
            f"🚀 [PARALLEL V5.29] {len(DOCUMENT_REVIEW_PROMPTS)} seksione, "
            f"max_workers={MAX_CONCURRENT_SECTIONS}"
        )

        _callback_lock = threading.Lock()
        found_precedent_cases: Set[str] = set()
        _precedent_lock = threading.Lock()

        def _emit_progress(event: str, payload: Dict[str, Any]) -> None:
            if not progress_callback:
                return
            with _callback_lock:
                try:
                    progress_callback(event, payload)
                except Exception:
                    pass

        def _emit_section(section_key: str, content: str) -> None:
            if not section_stream_callback or not content:
                return
            with _callback_lock:
                try:
                    section_stream_callback(section_key, content)
                except Exception:
                    pass

        def _run_article_verification_batched(
            section_key, section_cfg, section_title,
            section_max_tokens, section_start, precedent_search_time,
        ):
            verified_articles = verification_report.get("articles", [])
            total_articles = len(verified_articles)

            batch_size = (total_articles + ARTICLE_VERIFICATION_BATCHES - 1) // ARTICLE_VERIFICATION_BATCHES
            batches = [
                verified_articles[i:i + batch_size]
                for i in range(0, total_articles, batch_size)
            ]

            logger.info(
                f"⚡ [V5.29 BATCH] article_verification: {total_articles} nene "
                f"→ {len(batches)} batches"
            )

            def _run_one_batch(batch_idx, batch_articles):
                partial_report = dict(verification_report)
                partial_report["articles"] = batch_articles

                partial_context = build_verified_context(
                    citation_profile=citation_profile,
                    fact_profile=fact_profile,
                    verification_report=partial_report,
                    document_type=document_type,
                    file_name=file_name,
                    section_key=section_key,
                    precedents=None,
                    doc_text=None,
                    client_name=client_name,
                    client_position=client_position,
                    case_profile=case_profile,
                    forensic_findings=forensic_dict,
                )

                concise_suffix = SECTION_CONCISE_SUFFIXES.get(section_key, "")
                if concise_suffix:
                    partial_context = partial_context + concise_suffix

                try:
                    content = synthesize_section_streaming(
                        section_key=section_key,
                        section_cfg=section_cfg,
                        verified_context=partial_context,
                        file_name=file_name,
                        document_type=document_type,
                        stream_callback=None,
                    )
                    return content
                except Exception as e:
                    logger.error(f"❌ BATCH {batch_idx + 1} dështoi: {e}")
                    return f"[Seksioni batch {batch_idx + 1} dështoi: {e}]"

            contents = [""] * len(batches)
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=len(batches),
                thread_name_prefix="art_verif_batch",
            ) as exec_inner:
                futures_inner = {
                    exec_inner.submit(_run_one_batch, i, batch): i
                    for i, batch in enumerate(batches)
                }
                for fut in concurrent.futures.as_completed(futures_inner):
                    idx = futures_inner[fut]
                    try:
                        contents[idx] = fut.result()
                    except Exception as e:
                        contents[idx] = f"[Batch {idx + 1} dështoi]"

            combined = _merge_article_verification_batches(contents)
            elapsed = round(time.time() - section_start, 2)

            return (
                section_key,
                {"title": section_title, "content": combined},
                {
                    "duration_sec": elapsed,
                    "content_length": len(combined),
                    "max_tokens": section_max_tokens,
                    "batched": True,
                    "batch_count": len(batches),
                },
                {"context_build_time": 0.0, "precedent_search_time": precedent_search_time},
            )

        def _run_section(section_key, section_cfg):
            section_start = time.time()
            section_title = section_cfg["title"]
            section_max_tokens = section_cfg.get("max_tokens", DEFAULT_SECTION_MAX_TOKENS)

            precedents = None
            precedent_search_time = 0.0

            if section_key == "supreme_court_precedents":
                t_prec = time.time()
                try:
                    query = build_precedent_query(
                        document_type=document_type,
                        file_name=file_name,
                        doc_text=doc_text,
                        case_type=None,
                    )
                    precedents = search_relevant_precedents(
                        self.db, query,
                        top_k=PRECEDENT_TOP_K,
                        threshold=PRECEDENT_SIMILARITY_THRESHOLD,
                    )
                    if precedents:
                        with _precedent_lock:
                            for p in precedents:
                                cn = (p.get("case_number") or "").strip()
                                if cn:
                                    found_precedent_cases.add(cn)
                except Exception as e:
                    logger.error(f"❌ {section_key} precedent search: {e}")
                    precedents = []
                precedent_search_time = time.time() - t_prec

            if section_key == "article_verification":
                verified_articles = verification_report.get("articles", [])
                if len(verified_articles) >= ARTICLE_VERIFICATION_SPLIT_THRESHOLD:
                    _emit_progress("section_started", {
                        "section_key": section_key,
                        "section_title": section_title,
                    })
                    return _run_article_verification_batched(
                        section_key, section_cfg, section_title,
                        section_max_tokens, section_start, precedent_search_time,
                    )

            t_ctx = time.time()
            try:
                verified_context = build_verified_context(
                    citation_profile=citation_profile,
                    fact_profile=fact_profile,
                    verification_report=verification_report,
                    document_type=document_type,
                    file_name=file_name,
                    section_key=section_key,
                    precedents=precedents,
                    doc_text=doc_text,
                    client_name=client_name,
                    client_position=client_position,
                    case_profile=case_profile,
                    forensic_findings=forensic_dict,
                )
            except Exception as e:
                logger.error(f"❌ {section_key} context build: {e}")
                return (
                    section_key,
                    {"title": section_title, "content": "", "error": str(e)},
                    {"duration_sec": round(time.time() - section_start, 2), "error": str(e)},
                    {"context_build_time": 0.0, "precedent_search_time": precedent_search_time},
                )
            context_build_time = time.time() - t_ctx

            concise_suffix = SECTION_CONCISE_SUFFIXES.get(section_key, "")
            concise_applied = bool(concise_suffix)
            if concise_applied:
                verified_context = verified_context + concise_suffix

            case_context_active = (
                "case_context" in SECTION_CONTEXT_MAP.get(section_key, [])
                and case_profile.get("has_context")
            )
            forensic_context_active = (
                "forensic_findings" in SECTION_CONTEXT_MAP.get(section_key, [])
                and bool(forensic_dict)
            )

            logger.info(
                f"▶️ [SECTION START V5.29] {section_key} "
                f"(ctx={len(verified_context)}, concise={'ON' if concise_applied else 'off'}, "
                f"case_context={'ON' if case_context_active else 'off'}, "
                f"konstatime={'ON' if forensic_context_active else 'off'})"
            )

            _emit_progress("section_started", {
                "section_key": section_key,
                "section_title": section_title,
            })

            try:
                content = synthesize_section_streaming(
                    section_key=section_key,
                    section_cfg=section_cfg,
                    verified_context=verified_context,
                    file_name=file_name,
                    document_type=document_type,
                    stream_callback=None,
                )
                elapsed = round(time.time() - section_start, 2)
                logger.info(f"✅ [SECTION DONE V5.29] {section_key}: {elapsed}s, {len(content)} chars")
                return (
                    section_key,
                    {"title": section_title, "content": content},
                    {
                        "duration_sec": elapsed,
                        "content_length": len(content),
                        "context_chars": len(verified_context),
                        "max_tokens": section_max_tokens,
                        "concise_mode": concise_applied,
                        "case_context_active": case_context_active,
                        "forensic_context_active": forensic_context_active,
                    },
                    {"context_build_time": context_build_time, "precedent_search_time": precedent_search_time},
                )
            except Exception as e:
                elapsed = round(time.time() - section_start, 2)
                logger.error(f"❌ {section_key} failed after {elapsed}s: {e}")
                return (
                    section_key,
                    {"title": section_title, "content": "", "error": str(e)},
                    {"duration_sec": elapsed, "error": str(e)},
                    {"context_build_time": context_build_time, "precedent_search_time": precedent_search_time},
                )

        try:
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=MAX_CONCURRENT_SECTIONS,
                thread_name_prefix="doc_review",
            ) as executor:
                futures = {
                    executor.submit(_run_section, k, c): k
                    for k, c in DOCUMENT_REVIEW_PROMPTS.items()
                }
                for fut in concurrent.futures.as_completed(futures):
                    section_key = futures[fut]
                    try:
                        key, sec_entry, stat_entry, _timing = fut.result()
                        sections[key] = sec_entry
                        section_stats[key] = stat_entry
                        if sec_entry.get("content"):
                            _emit_section(key, sec_entry["content"])
                        if not sec_entry.get("error"):
                            _emit_progress("section_completed", {
                                "section_key": key,
                                "section_title": sec_entry["title"],
                                "content_length": stat_entry.get("content_length", 0),
                            })
                    except Exception as e:
                        logger.error(f"❌ PARALLEL future failed for {section_key}: {e}")

        except Exception as e:
            logger.error(f"❌ ThreadPoolExecutor failed: {e}")
            for section_key, section_cfg in DOCUMENT_REVIEW_PROMPTS.items():
                try:
                    key, sec_entry, stat_entry, _timing = _run_section(section_key, section_cfg)
                    sections[key] = sec_entry
                    section_stats[key] = stat_entry
                    if sec_entry.get("content"):
                        _emit_section(key, sec_entry["content"])
                except Exception as e2:
                    logger.error(f"❌ SEQUENTIAL {section_key}: {e2}")

        sections = {k: sections[k] for k in DOCUMENT_REVIEW_PROMPTS.keys() if k in sections}
        section_stats = {k: section_stats[k] for k in DOCUMENT_REVIEW_PROMPTS.keys() if k in section_stats}

        sections_total_time = round(time.time() - sections_start, 2)
        logger.info(f"⏱️ [TIMING] sections_total (parallel x{MAX_CONCURRENT_SECTIONS}): {sections_total_time}s")

        # ═══ ANTI-HALLUCINATION ═══
        if progress_callback:
            try:
                progress_callback("step_started", {
                    "step_key": "hallucination_check",
                    "step_title": "Duke kontrolluar saktësinë...",
                })
            except Exception:
                pass

        extra_cases = set(found_precedent_cases)
        extra_dates: Set[str] = set()
        extra_articles: Set[str] = set()

        if case_profile and case_profile.get("has_context"):
            cp_dates = case_profile.get("dates_set") or set()
            cp_cases = case_profile.get("cases_set") or set()
            cp_articles = case_profile.get("articles_set") or set()
            extra_cases = extra_cases | cp_cases
            extra_dates = extra_dates | cp_dates
            extra_articles = extra_articles | cp_articles

        if forensic_result and forensic_result.flags:
            try:
                forensic_allowed = extract_allowed_values_from_flags(forensic_result.flags)
                fc_cases = forensic_allowed.get("cases") or set()
                fc_dates = forensic_allowed.get("dates") or set()
                fc_articles = forensic_allowed.get("articles") or set()

                new_cases = fc_cases - extra_cases
                new_dates = fc_dates - extra_dates
                new_articles = fc_articles - extra_articles

                if new_cases or new_dates or new_articles:
                    logger.info(
                        f"📅 [V5.29 HALLUCINATION] Vlera nga konstatimet: "
                        f"cases +{len(new_cases)}, dates +{len(new_dates)}, "
                        f"articles +{len(new_articles)}"
                    )

                extra_cases = extra_cases | fc_cases
                extra_dates = extra_dates | fc_dates
                extra_articles = extra_articles | fc_articles
            except Exception as e:
                logger.warning(f"⚠️ [V5.29] extract_allowed_values_from_flags dështoi: {e}")

        # ═══ V5.29: DYNAMIC DB LAWS ═══
        t_db = time.time()
        try:
            db_laws = get_all_law_numbers_from_db(self.db)
        except Exception as e:
            logger.warning(f"⚠️ [V5.29] get_all_law_numbers_from_db dështoi: {e}")
            db_laws = set()
        logger.info(
            f"⏱️ [TIMING] db_laws_fetch: {time.time() - t_db:.2f}s "
            f"({len(db_laws)} ligje nga DB)"
        )

        t0 = time.time()
        hallucination_report = check_all_sections(
            sections=sections,
            citation_profile=citation_profile,
            fact_profile=fact_profile,
            verification_report=verification_report,
            extra_allowed_cases=extra_cases,
            extra_allowed_dates=extra_dates,
            extra_allowed_articles=extra_articles,
            extra_allowed_laws=db_laws,   # V5.29
        )
        hallucination_time = _lap("hallucination_check", t0)

        logger.info(
            f"🧪 [HALLUCINATION V5.29] status={hallucination_report['status']}, "
            f"issues={hallucination_report['total_issues']}"
        )

        if hallucination_report["status"] == "suspect":
            suspicious_keys = set(hallucination_report.get("suspicious_sections", []))
            blocked_count = 0
            for key in suspicious_keys:
                sec = sections.get(key)
                if not sec or not sec.get("content"):
                    continue
                per_sec = hallucination_report["per_section"].get(key, {})
                issues = per_sec.get("issues", [])
                high_issues = [i for i in issues if i.get("severity") == "high"]
                medium_issues = [i for i in issues if i.get("severity") == "medium"]

                warning_lines = [
                    "> ⚠️ **KY SEKSION U REFUZUA NGA SISTEMI ANTI-HALLUCINATION**",
                    ">",
                    "> U zbuluan vlera që NUK shfaqen në dokumentin origjinal:",
                ]
                for issue in (high_issues + medium_issues)[:5]:
                    warning_lines.append(f">   - **{issue.get('type', '?')}**: {issue.get('value', '?')}")
                warning_lines.append(">")
                warning_lines.append("> **Kërkohet verifikim manual.**")

                sec["_original_content"] = sec["content"]
                sec["_blocked_by_hallucination"] = True
                sec["content"] = (
                    "\n".join(warning_lines) + "\n\n---\n\n"
                    + "**Përmbajtja u refuzua. Rianalizo.**"
                )
                blocked_count += 1

            logger.warning(f"🛡️ [V5.29 GATE] Bllokuan {blocked_count} seksione")

        # ═══ V5.29: QUALITY METRICS ═══
        t0 = time.time()
        quality_metrics = compute_quality_metrics(
            sections=sections,
            section_stats=section_stats,
            hallucination_report=hallucination_report,
        )
        _lap("quality_metrics", t0)
        log_quality_metrics(quality_metrics)

        # ═══ MONTIMI FINAL ═══
        document_meta = {"file_name": file_name, "document_type": document_type}
        t0 = time.time()
        full_report = build_full_report(
            sections=sections,
            citation_profile=citation_profile,
            fact_profile=fact_profile,
            verification_report=verification_report,
            document_meta=document_meta,
        )
        _lap("build_full_report", t0)

        duration = round(time.time() - start, 2)
        precedents_found_total = (
            section_stats.get("supreme_court_precedents", {}).get("precedents_found", 0)
        )

        concise_sections = [k for k, s in section_stats.items() if s.get("concise_mode")]
        case_context_sections = [k for k, s in section_stats.items() if s.get("case_context_active")]
        forensic_context_sections = [k for k, s in section_stats.items() if s.get("forensic_context_active")]

        forensic_stats = forensic_result.stats if forensic_result else {}

        result = {
            "case_id": case_id,
            "document_id": document_id,
            "scope": "document",
            "document_ids": [document_id],
            "document_type": document_type,
            "file_name": file_name,
            "client_name": client_name,
            "client_position": client_position,
            "built_at": datetime.now(timezone.utc).isoformat(),
            "full_report": full_report,
            "sections": sections,
            "stats": {
                "case_id": case_id,
                "scope": "document",
                "document_id": document_id,
                "file_name": file_name,
                "document_type": document_type,
                "client_name": client_name,
                "client_position": client_position,
                "text_length": len(doc_text),
                "citation_stats": citation_profile.get("stats", {}),
                "fact_stats": fact_profile.get("stats", {}),
                "verification_stats": verification_report.get("stats", {}),
                "sections_generated": len([s for s in sections.values() if s.get("content")]),
                "sections_total": len(DOCUMENT_REVIEW_PROMPTS),
                "sections_blocked": len(hallucination_report.get("suspicious_sections", [])),
                "report_chars": len(full_report),
                "duration_sec": duration,
                "execution_mode": f"parallel_buffered_x{MAX_CONCURRENT_SECTIONS}_v5.29",
                "hallucination_status": hallucination_report["status"],
                "hallucination_issues": hallucination_report["total_issues"],
                "hallucination_suspicious_sections": hallucination_report["suspicious_sections"],
                "precedents_found": precedents_found_total,
                "article_verification_threshold": ARTICLE_VERIFICATION_SPLIT_THRESHOLD,
                "article_verification_batched": (
                    section_stats.get("article_verification", {}).get("batched", False)
                ),
                "concise_sections": concise_sections,
                "case_context_sections": case_context_sections,
                "case_profile_active": bool(case_profile.get("has_context")),
                "case_profile_stats": case_profile.get("stats", {}),
                "forensic_context_sections": forensic_context_sections,
                "forensic_profile_used": forensic_result.profile_used if forensic_result else None,
                "forensic_stats": forensic_stats,
                "forensic_flags_summary": [
                    {"rule_id": f.rule_id, "severity": f.severity, "message": f.message}
                    for f in (forensic_result.flags if forensic_result else [])[:20]
                ],
                "db_laws_count": len(db_laws),   # V5.29
                "quality_metrics": quality_metrics,
                "timing_breakdown": {
                    "citation_extract_sec": round(citation_time, 2),
                    "fact_extract_sec": round(fact_time, 2),
                    "verify_mongo_sec": round(verify_time, 2),
                    "sections_total_sec": sections_total_time,
                    "hallucination_check_sec": round(hallucination_time, 2),
                },
            },
            "hallucination_report": hallucination_report,
            "section_stats": section_stats,
            "status": "completed",
        }

        t0 = time.time()
        persist(self.db, result)
        _lap("persist", t0)

        logger.info(
            f"✅ [DOC_REVIEW V5.29] Complete: "
            f"sections={result['stats']['sections_generated']}/{result['stats']['sections_total']}, "
            f"blocked={result['stats']['sections_blocked']}, "
            f"hallucination={hallucination_report['status']}, "
            f"quality_score={quality_metrics['quality_score']}/100, "
            f"cost=${quality_metrics['cost_estimate_usd']}, "
            f"db_laws={len(db_laws)}, "
            f"case_profile={result['stats']['case_profile_active']}, "
            f"konstatime={forensic_stats.get('flags_total', 0)} "
            f"(kritike={forensic_stats.get('flags_critical', 0)}, "
            f"te rendesishme={forensic_stats.get('flags_high', 0)}), "
            f"report_chars={len(full_report)}, duration={duration}s"
        )

        return result


def get_document_review_service(db) -> DocumentReviewService:
    return DocumentReviewService(db)