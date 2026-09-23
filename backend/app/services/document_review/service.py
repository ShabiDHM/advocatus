# FILE: backend/app/services/document_review/service.py
# PHOENIX PROTOCOL - DOCUMENT REVIEW SERVICE V5.10
# V5.10: Pass file_name te build_fact_profile() — qe deadlines te kene
#        source_document. Mundeson citimin e saktë te burimit:
#        "Sipas Vendimi_i_Apelit.pdf, afati është 8 ditë."
# V5.9: precedentet e gjetur kalojne te hallucination_checker.
# V5.8: INTEGRIMI I PRECEDENTEVE TE VERTETA.
# V5.7: PARALLEL SECTIONS — ThreadPoolExecutor me max_workers=3.

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

# V5.7: Konfigurim paralelizmi
MAX_CONCURRENT_SECTIONS = int(os.getenv("DOC_REVIEW_MAX_WORKERS", "3"))
DEFAULT_SECTION_MAX_TOKENS = 3000


class DocumentReviewService:
    """
    V5.10 — Orkestruesi paralel me buffered output + hallucination check
    + precedent search + deadline sources.
    """

    def __init__(self, db):
        self.db = db

    def review(
        self,
        case_id: str,
        user_id: str,
        document_id: str,
        progress_callback: Optional[Callable] = None,
        section_stream_callback: Optional[Callable[[str, str], None]] = None,
    ) -> Dict[str, Any]:
        start = time.time()

        def _lap(label: str, t_start: float) -> float:
            elapsed = time.time() - t_start
            logger.warning(f"⏱️ [TIMING] {label}: {elapsed:.2f}s")
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
            f"🔍 [DOC_REVIEW V5.10] Starting: doc={document_id}, "
            f"file={file_name}, type={document_type}, "
            f"len={len(doc_text)} chars, parallel x{MAX_CONCURRENT_SECTIONS}"
        )

        # ═══ 2. LABORATORI ═══
        if progress_callback:
            try:
                progress_callback("section_started", {
                    "section_key": "extraction",
                    "section_title": "Duke nxjerrë citimet nga dokumenti...",
                })
            except Exception:
                pass

        t0 = time.time()
        citation_profile = build_citation_profile(doc_text)
        citation_time = _lap("build_citation_profile", t0)

        # ═══════════════════════════════════════════════════════════════════════
        # V5.10: Pass file_name si source_document per deadlines
        # ═══════════════════════════════════════════════════════════════════════
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
                progress_callback("section_started", {
                    "section_key": "verification",
                    "section_title": "Duke verifikuar citimet në bazën ligjore...",
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

        logger.warning(
            f"🚀 [PARALLEL V5.10] Duke nisur {len(DOCUMENT_REVIEW_PROMPTS)} "
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

        def _run_section(
            section_key: str,
            section_cfg: Dict[str, Any],
        ) -> Tuple[str, Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
            """
            V5.10: Ekzekuton nje seksion te vetem ne thread te pavarur.
            """
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
                        self.db,
                        query,
                        top_k=PRECEDENT_TOP_K,
                        threshold=PRECEDENT_SIMILARITY_THRESHOLD,
                    )
                    logger.info(
                        f"🏛️ [SECTION {section_key}] Precedent search: "
                        f"{len(precedents) if precedents else 0} rezultate "
                        f"(top_k={PRECEDENT_TOP_K}, "
                        f"threshold={PRECEDENT_SIMILARITY_THRESHOLD})"
                    )

                    if precedents:
                        with _precedent_lock:
                            for p in precedents:
                                cn = (p.get("case_number") or "").strip()
                                if cn:
                                    found_precedent_cases.add(cn)
                except Exception as e:
                    logger.error(
                        f"❌ [SECTION {section_key}] Precedent search failed: {e}"
                    )
                    precedents = []
                precedent_search_time = time.time() - t_prec

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
                )
            except Exception as e:
                logger.error(f"❌ [SECTION {section_key}] Context build failed: {e}")
                return (
                    section_key,
                    {
                        "title": section_title,
                        "content": "",
                        "error": f"context_build_failed: {e}",
                    },
                    {
                        "duration_sec": round(time.time() - section_start, 2),
                        "error": f"context_build_failed: {e}",
                        "max_tokens": section_max_tokens,
                        "precedent_search_sec": round(precedent_search_time, 2),
                        "precedents_found": len(precedents) if precedents else 0,
                    },
                    {
                        "context_build_time": 0.0,
                        "precedent_search_time": precedent_search_time,
                    },
                )

            context_build_time = time.time() - t_ctx

            logger.warning(
                f"▶️ [SECTION START] {section_key} "
                f"(max_tokens={section_max_tokens}, context={len(verified_context)} chars, "
                f"ctx_build={context_build_time*1000:.1f}ms, "
                f"precedent_search={precedent_search_time*1000:.1f}ms) — {section_title}"
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

                logger.warning(
                    f"✅ [SECTION DONE] {section_key}: {elapsed}s, "
                    f"{len(content)} chars out (context={len(verified_context)} in, "
                    f"max_tokens={section_max_tokens})"
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
                    },
                    {
                        "context_build_time": context_build_time,
                        "precedent_search_time": precedent_search_time,
                    },
                )

            except Exception as e:
                elapsed = round(time.time() - section_start, 2)
                logger.error(
                    f"❌ [DOC_REVIEW] Section {section_key} failed after {elapsed}s: {e}"
                )
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
                    {
                        "context_build_time": context_build_time,
                        "precedent_search_time": precedent_search_time,
                    },
                )

        # ═══ Ekzekutim paralel ═══
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
                        logger.error(
                            f"❌ [PARALLEL V5.10] Future failed for {section_key}: {e}"
                        )

        except Exception as e:
            logger.error(f"❌ [PARALLEL V5.10] ThreadPoolExecutor failed: {e}")
            logger.warning(f"🔄 [PARALLEL V5.10] Fallback në sequential mode")
            for section_key, section_cfg in DOCUMENT_REVIEW_PROMPTS.items():
                try:
                    key, sec_entry, stat_entry, _timing = _run_section(
                        section_key, section_cfg
                    )
                    sections[key] = sec_entry
                    section_stats[key] = stat_entry
                    if sec_entry.get("content"):
                        _emit_section(key, sec_entry["content"])
                except Exception as e2:
                    logger.error(f"❌ [SEQUENTIAL FALLBACK] {section_key}: {e2}")

        sections = {
            k: sections[k] for k in DOCUMENT_REVIEW_PROMPTS.keys() if k in sections
        }
        section_stats = {
            k: section_stats[k] for k in DOCUMENT_REVIEW_PROMPTS.keys() if k in section_stats
        }

        sections_total_time = round(time.time() - sections_start, 2)
        logger.warning(
            f"⏱️ [TIMING] sections_total (parallel x{MAX_CONCURRENT_SECTIONS}): "
            f"{sections_total_time}s"
        )

        logger.info(
            f"🏛️ [V5.10] Precedent cases qe do te lejohen: "
            f"{len(found_precedent_cases)} -> {sorted(found_precedent_cases)[:5]}"
        )

        # ═══ 4b. ANTI-HALLUCINATION CHECK ═══
        if progress_callback:
            try:
                progress_callback("section_started", {
                    "section_key": "hallucination_check",
                    "section_title": "Duke kontrolluar saktësinë e fakteve...",
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

        logger.warning(
            f"🧪 [HALLUCINATION] status={hallucination_report['status']}, "
            f"issues={hallucination_report['total_issues']} "
            f"(high={hallucination_report['severity_totals']['high']}, "
            f"medium={hallucination_report['severity_totals']['medium']}, "
            f"low={hallucination_report['severity_totals']['low']}), "
            f"suspicious={hallucination_report['suspicious_sections']}"
        )

        # ═══ 5. MONTIMI FINAL ═══
        document_meta = {
            "file_name": file_name,
            "document_type": document_type,
        }

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

        # ═══ 6. RESULT ═══
        result = {
            "case_id": case_id,
            "document_id": document_id,
            "scope": "document",
            "document_ids": [document_id],
            "document_type": document_type,
            "file_name": file_name,
            "built_at": datetime.now(timezone.utc).isoformat(),
            "full_report": full_report,
            "sections": sections,
            "stats": {
                "case_id": case_id,
                "scope": "document",
                "document_id": document_id,
                "file_name": file_name,
                "document_type": document_type,
                "text_length": len(doc_text),
                "citation_stats": citation_profile.get("stats", {}),
                "fact_stats": fact_profile.get("stats", {}),
                "verification_stats": verification_report.get("stats", {}),
                "sections_generated": len(
                    [s for s in sections.values() if s.get("content")]
                ),
                "sections_total": len(DOCUMENT_REVIEW_PROMPTS),
                "report_chars": len(full_report),
                "duration_sec": duration,
                "execution_mode": f"parallel_buffered_x{MAX_CONCURRENT_SECTIONS}",
                "hallucination_status": hallucination_report["status"],
                "hallucination_issues": hallucination_report["total_issues"],
                "hallucination_suspicious_sections": hallucination_report[
                    "suspicious_sections"
                ],
                "precedents_found": precedents_found_total,
                "precedent_threshold": PRECEDENT_SIMILARITY_THRESHOLD,
                "precedent_top_k": PRECEDENT_TOP_K,
                "timing_breakdown": {
                    "citation_extract_sec": round(citation_time, 2),
                    "fact_extract_sec": round(fact_time, 2),
                    "verify_mongo_sec": round(verify_time, 2),
                    "sections_total_sec": sections_total_time,
                    "hallucination_check_sec": round(hallucination_time, 2),
                },
            },
            "verification_details": {
                "citation_profile": citation_profile,
                "fact_profile": fact_profile,
                "verification_report": verification_report,
            },
            "hallucination_report": hallucination_report,
            "section_stats": section_stats,
            "status": "completed",
        }

        # ═══ 7. PERSIST ═══
        t0 = time.time()
        persist(self.db, result)
        _lap("persist", t0)

        logger.info(
            f"✅ [DOC_REVIEW V5.10] Complete: "
            f"sections={result['stats']['sections_generated']}/{result['stats']['sections_total']}, "
            f"articles_verified={verification_report['stats']['articles_verified']}, "
            f"precedents_found={precedents_found_total}, "
            f"hallucination={hallucination_report['status']} "
            f"({hallucination_report['total_issues']} issues), "
            f"report_chars={len(full_report)}, "
            f"duration={duration}s, mode={result['stats']['execution_mode']}"
        )

        return result


# ═══════════════════════════════════════════════════════════════════════════
# FACTORY
# ═══════════════════════════════════════════════════════════════════════════

def get_document_review_service(db) -> DocumentReviewService:
    return DocumentReviewService(db)