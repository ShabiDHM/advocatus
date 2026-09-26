# FILE: backend/app/services/document_review/service.py
# PHOENIX PROTOCOL - DOCUMENT REVIEW SERVICE V5.21
# V5.21: CONCISE FOR MULTIPLE SECTIONS — Bazuar në matje reale V5.20:
#        - action_steps: 111.38s → target ~30-40s me concise
#        - analiza_e_thelluar: 62.16s → target ~25-35s me concise
#        Dictionary SECTION_CONCISE_SUFFIXES për konfigurim të pastër.
# V5.20: SPLIT THRESHOLD 30 → 10.
# V5.19: ARTICLE_VERIFICATION CONCISE.

import os
import time
import logging
import threading
import concurrent.futures
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Callable, Tuple, Set

from .citation_extractor import build_citation_profile
from .fact_extractor import build_fact_profile
from .mongo_verifier import verify_all
from .prompts import DOCUMENT_REVIEW_PROMPTS, build_verified_context
from .streaming import synthesize_section_streaming
from .report_builder import build_full_report
from .hallucination_checker import check_all_sections
from .precedent_search import (
    build_precedent_query,
    search_relevant_precedents,
    PRECEDENT_SIMILARITY_THRESHOLD,
    PRECEDENT_TOP_K,
)
from .persistence import (
    load_document,
    load_extraction,
    persist,
    empty_result,
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
# V5.21: CONCISE SUFFIXES — Dictionary i pastër
# ═══════════════════════════════════════════════════════════════════════════

ARTICLE_VERIFICATION_CONCISE_SUFFIX = """

═══════════════════════════════════════════════════════════════════════════
⚡ UDHËZIM KONCIZIONI (VETËM PËR KËTË SEKSION)
═══════════════════════════════════════════════════════════════════════════
Për ÇDO nen të listuar, jep VETËM:
  - Numrin + ligjin (p.sh. "Neni 78 i KPPRK Nr. 08/L-032")
  - Statusin (Verified / Not Found / Replaced / Alias)
  - Arsyetim me NJË FJALI të shkurtër (~10-20 fjalë)

KUFIZIME ABSOLUTE:
  - MOS përsërit tekstin e nenit.
  - MOS përsërit kontekstin.
  - MOS shkruaj paragrafë të gjatë për nenin.
  - MOS shto seksione ekstra si "Përfundim" / "Rekomandim" brenda listës.
  - MAKSIMUM 2 rreshta për nen.
  - MAKSIMUM 1 tabelë përmbledhëse në fund (statusi agregat).
"""

ACTION_STEPS_CONCISE_SUFFIX = """

═══════════════════════════════════════════════════════════════════════════
⚡ UDHËZIM KONCIZIONI (VETËM PËR KËTË SEKSION)
═══════════════════════════════════════════════════════════════════════════
Për ÇDO rekomandim / veprim / hap:
  - Emri i veprimit (5-10 fjalë)
  - Bazë ligjore / procedurale (1 fjali, me referencë)
  - Prioriteti (i menjëhershëm / afatgjatë)

KUFIZIME ABSOLUTE:
  - MOS shkruaj paragrafë të gjatë.
  - MOS përsërit faktet nga konteksti — citoji vetëm si referencë.
  - MAKSIMUM 3 rreshta për veprim.
  - Fokus në VEPRIME, jo në analizë.

STRUKTURA:
### A. Vlerësimi i Situatës (2-3 fjali)
### B. Hapat e Menjëhershëm (1-7 ditë) — 3-4 veprime bullet-point
### C. Hapat Afatgjatë (1-3 muaj) — 3-4 veprime bullet-point
### D. Mundësitë Procedurale — 3-4 veprime bullet-point
### E. Rreziqet — 3-4 pika bullet
### F. Referencat Konkrete — 3-4 nene me numër
### G. Veprime Kritike që Mund të Mungojnë — 2-3 pika bullet
"""

ANALIZA_E_THELLUAR_CONCISE_SUFFIX = """

═══════════════════════════════════════════════════════════════════════════
⚡ UDHËZIM KONCIZIONI (VETËM PËR KËTË SEKSION)
═══════════════════════════════════════════════════════════════════════════
Për ÇDO shenjë / model / boshllëk:
  - Titull i shkurtër (3-7 fjalë)
  - Vëzhgimi (1-2 fjali)
  - Baza në fakte (cito referencën e saktë)

KUFIZIME ABSOLUTE:
  - MOS përsërit analizën që gjendet në seksionet e tjera (drafting_quality, errors_corrections).
  - MAKSIMUM 3 rreshta për shenjë.
  - 5-7 shenja TOTAL — jo më shumë.
  - Cilësia > Sasia.

STRUKTURA:
### A. Modele dhe Shenja të Fshehta (2-3)
### B. Omissions dhe Boshllëqe Kritike (2-3)
### C. Standarde Provash (1-2)
### D. Arme të Mundshme të Kundërshtarit (1-2)
### E. Veprime Kritike që Mund të Mungojnë (1-2)
"""

# V5.21: Dictionary — section_key → concise suffix
SECTION_CONCISE_SUFFIXES: Dict[str, str] = {
    "article_verification": ARTICLE_VERIFICATION_CONCISE_SUFFIX,
    "action_steps": ACTION_STEPS_CONCISE_SUFFIX,
    "analiza_e_thelluar": ANALIZA_E_THELLUAR_CONCISE_SUFFIX,
}


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
            f"🔍 [DOC_REVIEW V5.21] Starting: doc={document_id}, "
            f"file={file_name}, type={document_type}, "
            f"len={len(doc_text)} chars, client={client_name or '?'} "
            f"({client_position or '?'}), parallel x{MAX_CONCURRENT_SECTIONS}, "
            f"article_threshold={ARTICLE_VERIFICATION_SPLIT_THRESHOLD}, "
            f"concise_sections={list(SECTION_CONCISE_SUFFIXES.keys())}"
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
            f"Dates={fact_profile['stats']['total_dates']}, "
            f"Parties={fact_profile['stats']['total_parties']}"
        )

        # ═══ 3. ARKIVA ═══
        if progress_callback:
            try:
                progress_callback("step_started", {
                    "step_key": "verification",
                    "step_title": "Duke verifikuar citimet në bazën ligjore...",
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
            f"🚀 [PARALLEL V5.21] Duke nisur {len(DOCUMENT_REVIEW_PROMPTS)} "
            f"seksione me max_workers={MAX_CONCURRENT_SECTIONS}"
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
            section_key: str,
            section_cfg: Dict[str, Any],
            section_title: str,
            section_max_tokens: int,
            section_start: float,
            precedent_search_time: float,
        ) -> Tuple[str, Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
            verified_articles = verification_report.get("articles", [])
            total_articles = len(verified_articles)

            batch_size = (total_articles + ARTICLE_VERIFICATION_BATCHES - 1) // ARTICLE_VERIFICATION_BATCHES
            batches: List[List[Dict[str, Any]]] = [
                verified_articles[i:i + batch_size]
                for i in range(0, total_articles, batch_size)
            ]

            logger.info(
                f"⚡ [V5.21 BATCH] article_verification: {total_articles} nene "
                f"→ {len(batches)} batches (size≈{batch_size})"
            )

            def _run_one_batch(batch_idx: int, batch_articles: List[Dict[str, Any]]) -> str:
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
                )

                concise_suffix = SECTION_CONCISE_SUFFIXES.get(section_key, "")
                if concise_suffix:
                    partial_context = partial_context + concise_suffix

                logger.info(
                    f"▶️ [V5.21 BATCH {batch_idx + 1}/{len(batches)}] "
                    f"article_verification — {len(batch_articles)} nene, "
                    f"context={len(partial_context)} chars (concise=ON)"
                )

                try:
                    content = synthesize_section_streaming(
                        section_key=section_key,
                        section_cfg=section_cfg,
                        verified_context=partial_context,
                        file_name=file_name,
                        document_type=document_type,
                        stream_callback=None,
                    )
                    logger.info(
                        f"✅ [V5.21 BATCH {batch_idx + 1}/{len(batches)}] "
                        f"Përfundoi: {len(content)} chars"
                    )
                    return content
                except Exception as e:
                    logger.error(
                        f"❌ [V5.21 BATCH {batch_idx + 1}/{len(batches)}] "
                        f"Dështoi: {e}"
                    )
                    return f"[Seksioni batch {batch_idx + 1} dështoi: {e}]"

            contents: List[str] = [""] * len(batches)
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
                        logger.error(f"❌ [V5.21 BATCH] Future {idx} error: {e}")
                        contents[idx] = f"[Batch {idx + 1} dështoi]"

            combined = "\n\n".join(c for c in contents if c).strip()
            elapsed = round(time.time() - section_start, 2)

            logger.info(
                f"✅ [SECTION DONE V5.21] {section_key}: {elapsed}s, "
                f"{len(combined)} chars combined (batches={len(batches)}, concise=ON)"
            )

            return (
                section_key,
                {"title": section_title, "content": combined},
                {
                    "duration_sec": elapsed,
                    "content_length": len(combined),
                    "max_tokens": section_max_tokens,
                    "precedent_search_sec": round(precedent_search_time, 2),
                    "precedents_found": 0,
                    "batched": True,
                    "batch_count": len(batches),
                    "concise_mode": True,
                },
                {
                    "context_build_time": 0.0,
                    "precedent_search_time": precedent_search_time,
                },
            )

        def _run_section(
            section_key: str,
            section_cfg: Dict[str, Any],
        ) -> Tuple[str, Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
            section_start = time.time()
            section_title = section_cfg["title"]
            section_max_tokens = section_cfg.get("max_tokens", DEFAULT_SECTION_MAX_TOKENS)

            precedents: Optional[List[Dict[str, Any]]] = None
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
                    logger.info(
                        f"🏛️ [SECTION {section_key}] Precedent search: "
                        f"{len(precedents) if precedents else 0} rezultate "
                        f"(top_k={PRECEDENT_TOP_K}, threshold={PRECEDENT_SIMILARITY_THRESHOLD})"
                    )

                    if precedents:
                        with _precedent_lock:
                            for p in precedents:
                                cn = (p.get("case_number") or "").strip()
                                if cn:
                                    found_precedent_cases.add(cn)
                except Exception as e:
                    logger.error(f"❌ [SECTION {section_key}] Precedent search failed: {e}")
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
                        section_key=section_key,
                        section_cfg=section_cfg,
                        section_title=section_title,
                        section_max_tokens=section_max_tokens,
                        section_start=section_start,
                        precedent_search_time=precedent_search_time,
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
                )
            except Exception as e:
                logger.error(f"❌ [SECTION {section_key}] Context build failed: {e}")
                return (
                    section_key,
                    {"title": section_title, "content": "", "error": f"context_build_failed: {e}"},
                    {
                        "duration_sec": round(time.time() - section_start, 2),
                        "error": f"context_build_failed: {e}",
                        "max_tokens": section_max_tokens,
                        "precedent_search_sec": round(precedent_search_time, 2),
                        "precedents_found": len(precedents) if precedents else 0,
                    },
                    {"context_build_time": 0.0, "precedent_search_time": precedent_search_time},
                )

            context_build_time = time.time() - t_ctx

            # V5.21: Apliko concise suffix për section-t e konfiguruara
            concise_suffix = SECTION_CONCISE_SUFFIXES.get(section_key, "")
            concise_applied = bool(concise_suffix)
            if concise_applied:
                verified_context = verified_context + concise_suffix

            logger.info(
                f"▶️ [SECTION START] {section_key} "
                f"(max_tokens={section_max_tokens}, context={len(verified_context)} chars, "
                f"ctx_build={context_build_time*1000:.1f}ms, "
                f"precedent_search={precedent_search_time*1000:.1f}ms, "
                f"concise={'ON' if concise_applied else 'off'}) — {section_title}"
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

                logger.info(
                    f"✅ [SECTION DONE] {section_key}: {elapsed}s, "
                    f"{len(content)} chars out (context={len(verified_context)} in, "
                    f"max_tokens={section_max_tokens}, concise={'ON' if concise_applied else 'off'})"
                )

                return (
                    section_key,
                    {"title": section_title, "content": content},
                    {
                        "duration_sec": elapsed,
                        "content_length": len(content),
                        "context_chars": len(verified_context),
                        "max_tokens": section_max_tokens,
                        "precedent_search_sec": round(precedent_search_time, 2),
                        "precedents_found": len(precedents) if precedents else 0,
                        "concise_mode": concise_applied,
                    },
                    {"context_build_time": context_build_time, "precedent_search_time": precedent_search_time},
                )

            except Exception as e:
                elapsed = round(time.time() - section_start, 2)
                logger.error(f"❌ [DOC_REVIEW] Section {section_key} failed after {elapsed}s: {e}")
                return (
                    section_key,
                    {"title": section_title, "content": "", "error": str(e)},
                    {
                        "duration_sec": elapsed,
                        "error": str(e),
                        "max_tokens": section_max_tokens,
                        "precedent_search_sec": round(precedent_search_time, 2),
                        "precedents_found": len(precedents) if precedents else 0,
                    },
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
                        logger.error(f"❌ [PARALLEL V5.21] Future failed for {section_key}: {e}")

        except Exception as e:
            logger.error(f"❌ [PARALLEL V5.21] ThreadPoolExecutor failed: {e}")
            logger.info("🔄 [PARALLEL V5.21] Fallback në sequential mode")
            for section_key, section_cfg in DOCUMENT_REVIEW_PROMPTS.items():
                try:
                    key, sec_entry, stat_entry, _timing = _run_section(section_key, section_cfg)
                    sections[key] = sec_entry
                    section_stats[key] = stat_entry
                    if sec_entry.get("content"):
                        _emit_section(key, sec_entry["content"])
                except Exception as e2:
                    logger.error(f"❌ [SEQUENTIAL FALLBACK] {section_key}: {e2}")

        sections = {k: sections[k] for k in DOCUMENT_REVIEW_PROMPTS.keys() if k in sections}
        section_stats = {k: section_stats[k] for k in DOCUMENT_REVIEW_PROMPTS.keys() if k in section_stats}

        sections_total_time = round(time.time() - sections_start, 2)
        logger.info(
            f"⏱️ [TIMING] sections_total (parallel x{MAX_CONCURRENT_SECTIONS}): "
            f"{sections_total_time}s"
        )

        logger.info(
            f"🏛️ [V5.21] Precedent cases qe do te lejohen: "
            f"{len(found_precedent_cases)} -> {sorted(found_precedent_cases)[:5]}"
        )

        # ANTI-HALLUCINATION CHECK
        if progress_callback:
            try:
                progress_callback("step_started", {
                    "step_key": "hallucination_check",
                    "step_title": "Duke kontrolluar saktësinë e fakteve...",
                })
            except Exception:
                pass

        t0 = time.time()
        hallucination_report = check_all_sections(
            sections=sections,
            citation_profile=citation_profile,
            fact_profile=fact_profile,
            verification_report=verification_report,
            extra_allowed_cases=found_precedent_cases,
        )
        hallucination_time = _lap("hallucination_check", t0)

        logger.info(
            f"🧪 [HALLUCINATION] status={hallucination_report['status']}, "
            f"issues={hallucination_report['total_issues']} "
            f"(high={hallucination_report['severity_totals']['high']}, "
            f"medium={hallucination_report['severity_totals']['medium']}, "
            f"low={hallucination_report['severity_totals']['low']}), "
            f"suspicious={hallucination_report['suspicious_sections']}"
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
                    "> Sistemi zbuloi vlera që NUK shfaqen në dokumentin origjinal:",
                ]
                for issue in (high_issues + medium_issues)[:5]:
                    warning_lines.append(f">   - **{issue.get('type', '?')}**: {issue.get('value', '?')}")
                    warning_lines.append(f">     {issue.get('message', '')}")
                if len(high_issues) + len(medium_issues) > 5:
                    remaining = len(high_issues) + len(medium_issues) - 5
                    warning_lines.append(f">   - _...dhe {remaining} probleme të tjera_")
                warning_lines.append(">")
                warning_lines.append("> **Kërkohet verifikim manual nga avokati.**")

                warning = "\n".join(warning_lines)
                sec["_original_content"] = sec["content"]
                sec["_blocked_by_hallucination"] = True
                sec["content"] = (
                    warning + "\n\n---\n\n"
                    + "**Përmbajtja e gjeneruar u refuzua. Klikoni \"Rianalizo\" për të provuar përsëri.**"
                )
                blocked_count += 1

            logger.warning(f"🛡️ [V5.21 GATE] Bllokuan {blocked_count} seksione suspect: {sorted(suspicious_keys)}")

        # MONTIMI FINAL
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

        # V5.21: Lista e section-eve me concise aktiv
        concise_sections = [
            k for k, s in section_stats.items()
            if s.get("concise_mode")
        ]

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
                "execution_mode": f"parallel_buffered_x{MAX_CONCURRENT_SECTIONS}_v5.21",
                "hallucination_status": hallucination_report["status"],
                "hallucination_issues": hallucination_report["total_issues"],
                "hallucination_suspicious_sections": hallucination_report["suspicious_sections"],
                "precedents_found": precedents_found_total,
                "precedent_threshold": PRECEDENT_SIMILARITY_THRESHOLD,
                "precedent_top_k": PRECEDENT_TOP_K,
                "article_verification_threshold": ARTICLE_VERIFICATION_SPLIT_THRESHOLD,
                "article_verification_batched": (
                    section_stats.get("article_verification", {}).get("batched", False)
                ),
                "concise_sections": concise_sections,
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
            f"✅ [DOC_REVIEW V5.21] Complete: "
            f"sections={result['stats']['sections_generated']}/{result['stats']['sections_total']}, "
            f"blocked={result['stats']['sections_blocked']}, "
            f"articles_verified={verification_report['stats']['articles_verified']}, "
            f"precedents_found={precedents_found_total}, "
            f"hallucination={hallucination_report['status']} "
            f"({hallucination_report['total_issues']} issues), "
            f"concise_sections={concise_sections}, "
            f"report_chars={len(full_report)}, duration={duration}s, mode={result['stats']['execution_mode']}"
        )

        return result


def get_document_review_service(db) -> DocumentReviewService:
    return DocumentReviewService(db)