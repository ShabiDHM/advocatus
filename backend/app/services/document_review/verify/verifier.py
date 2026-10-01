# FILE: backend/app/services/document_review/verify/verifier.py
# PHOENIX PROTOCOL - VERIFY / VERIFIER V2.6
# V2.6: CRITICAL FIX — db_laws INIT —
#       - `db_laws` definohej VETËM brenda `if HALLUCINATION_GATE_ENABLED
#         and fact_profile:` bllokut, por lexohej jashtë tij (në dict `stats`
#         dhe log final). Skenar: nëse `build_fact_profile` dështon →
#         `fact_profile = {}` → degë `elif not fact_profile` → `db_laws`
#         NUK definohet → NameError gjatë ndërtimit të `stats`, PAS
#         përfundimit të të gjitha thirrjeve LLM (humbje totale e kostos).
#         Fix: inicializim `db_laws: Set[str] = set()` para if-block.
# V2.5: DYNAMIC DB LAWS — Integrim i get_all_law_numbers_from_db().
# V2.4: QUALITY METRICS.
# V2.3: VERSION CONSISTENCY.
# V2.2: CASE CONTEXT.
# V2.1: PERF SPLIT.
# V2.0: MODULARIZIM.

import time
import logging
import threading
import concurrent.futures
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Callable, Tuple, Set

from ..citation_extractor import build_citation_profile
from ..fact_extractor import build_fact_profile
from ..case_profile import build_case_profile
from ..mongo_verifier import verify_all
from ..mongo_verifier.laws import get_all_law_numbers_from_db
from ..streaming import synthesize_section_streaming
from ..persistence import load_document, load_extraction
from ..hallucination_checker import check_all_sections, _extract_dates_iso
from ..quality_metrics import compute_quality_metrics, log_quality_metrics
from ..precedent_search import (
    build_precedent_query,
    search_relevant_precedents,
    PRECEDENT_SIMILARITY_THRESHOLD,
    PRECEDENT_TOP_K,
)

from .config import (
    MAX_CONCURRENT_VERIFY_SECTIONS,
    HALLUCINATION_GATE_ENABLED,
)
from .prompt_constants import VERIFY_SECTION_KEYS
from .prompt_doc_types import VERIFY_DOC_TYPES
from .prompt_sections import VERIFY_SECTION_PROMPTS
from .context_builders import build_verify_context
from .cited_summary import (
    summarize_cited_precedents,
    extract_precedent_articles,
    extract_precedent_cases,
)
from .warnings import (
    build_cited_precedents_warning,
    build_hallucination_warning,
)
from .readiness import (
    parse_readiness,
    count_critical_recommendations,
    maybe_override_readiness,
    maybe_override_readiness_for_critical,
)
from .scoring import calculate_score
from .section_builders import post_process_section
from .report_builder import empty_verify_result, build_full_report
from .persistence import persist_verification

logger = logging.getLogger(__name__)


class DraftVerifier:
    def __init__(self, db):
        self.db = db

    def verify(
        self,
        case_id: str,
        document_id: str,
        doc_type: str,
        user_id: Optional[str] = None,
        progress_callback: Optional[Callable] = None,
        section_stream_callback: Optional[Callable[[str, str], None]] = None,
    ) -> Dict[str, Any]:
        start = time.time()

        def _lap(label: str, t_start: float) -> float:
            elapsed = time.time() - t_start
            logger.info(f"⏱️ [VERIFY TIMING] {label}: {elapsed:.2f}s")
            return elapsed

        if doc_type not in VERIFY_DOC_TYPES:
            msg = (
                f"Lloj dokumenti i panjohur: '{doc_type}'. "
                f"Të lejuara: {sorted(VERIFY_DOC_TYPES.keys())}"
            )
            logger.error(f"❌ [VERIFY] {msg}")
            return empty_verify_result(case_id, document_id, msg, doc_type)

        doc_type_label = VERIFY_DOC_TYPES[doc_type]

        t0 = time.time()
        try:
            document = load_document(self.db, case_id, document_id)
            extraction = load_extraction(self.db, case_id, document_id)
        except Exception as e:
            logger.error(f"❌ [VERIFY] Load failed: {e}")
            return empty_verify_result(
                case_id, document_id, f"Gabim gjatë leximit: {e}", doc_type
            )
        _lap("load_document+extraction", t0)

        if not document and not extraction:
            return empty_verify_result(
                case_id, document_id, "Drafti nuk u gjet në bazë.", doc_type
            )

        doc_text = (
            (extraction or {}).get("text")
            or (document or {}).get("content")
            or (document or {}).get("extracted_text")
            or (document or {}).get("text")
            or ""
        )
        if not doc_text.strip():
            return empty_verify_result(
                case_id, document_id, "Drafti nuk ka tekst për verifikim.", doc_type
            )

        file_name = (document or {}).get("file_name", "draft")

        logger.info(
            f"🔎 [VERIFY V2.6] Start: case={case_id}, doc={document_id}, "
            f"file={file_name}, doc_type={doc_type} ({doc_type_label}), "
            f"len={len(doc_text)} chars, user={user_id or '?'}, "
            f"parallel x{MAX_CONCURRENT_VERIFY_SECTIONS}, "
            f"hallucination_gate={HALLUCINATION_GATE_ENABLED}"
        )

        if progress_callback:
            try:
                progress_callback("step_started", {
                    "step_key": "extraction",
                    "step_title": "Duke nxjerrë citimet nga drafti...",
                })
            except Exception:
                pass

        t0 = time.time()
        try:
            citation_profile = build_citation_profile(doc_text)
        except Exception as e:
            logger.error(f"❌ [VERIFY] build_citation_profile failed: {e}")
            citation_profile = {"stats": {"total_articles": 0, "total_laws_by_number": 0}}
        _lap("build_citation_profile", t0)

        t0 = time.time()
        fact_profile: Dict[str, Any] = {}
        if HALLUCINATION_GATE_ENABLED:
            try:
                fact_profile = build_fact_profile(
                    doc_text, source_document=file_name
                )
                logger.info(
                    f"🔬 [VERIFY V2.6] Fact profile: "
                    f"dates={fact_profile.get('stats', {}).get('total_dates', 0)}, "
                    f"parties={fact_profile.get('stats', {}).get('total_parties', 0)}, "
                    f"deadlines={fact_profile.get('stats', {}).get('legal_deadlines', 0)}"
                )
            except Exception as e:
                logger.error(f"❌ [VERIFY] build_fact_profile failed: {e}")
                fact_profile = {}
        _lap("build_fact_profile", t0)

        # ═══════════════════════════════════════════════════════════════════
        # V2.2: CASE PROFILE
        # ═══════════════════════════════════════════════════════════════════
        t0 = time.time()
        case_profile: Dict[str, Any] = {}
        try:
            case_profile = build_case_profile(
                self.db, case_id, exclude_doc_id=document_id,
            )
            if case_profile.get("has_context"):
                logger.info(
                    f"📚 [VERIFY V2.6] Case profile aktiv: "
                    f"docs={case_profile['stats']['documents_scanned']}, "
                    f"subjects={case_profile['stats']['unique_subjects']}, "
                    f"block_chars={len(case_profile.get('block', ''))}"
                )
            else:
                logger.info(
                    f"ℹ️ [VERIFY V2.6] Case profile bosh — verifikimi "
                    f"kalon në mode 'vetëm draft'."
                )
        except Exception as e:
            logger.warning(f"⚠️ [VERIFY V2.6] build_case_profile dështoi: {e}")
            case_profile = {}
        _lap("build_case_profile", t0)

        t0 = time.time()
        try:
            verification_report = verify_all(self.db, citation_profile)
        except Exception as e:
            logger.error(f"❌ [VERIFY] verify_all failed: {e}")
            verification_report = {
                "articles": [],
                "laws_by_number": [],
                "case_numbers": [],
                "stats": {
                    "articles_total": 0, "articles_verified": 0,
                    "laws_total": 0, "laws_verified": 0,
                    "case_numbers_cited": 0, "precedents_verified": 0,
                },
            }
        _lap("verify_all (MongoDB)", t0)

        logger.info(
            f"📚 [VERIFY] Articles {verification_report['stats'].get('articles_verified', 0)}/"
            f"{verification_report['stats'].get('articles_total', 0)}"
        )

        cited_summary = summarize_cited_precedents(verification_report)
        if cited_summary["unverified_count"] > 0:
            logger.warning(
                f"⚠️ [VERIFY V2.6] CITED PRECEDENTS: "
                f"{cited_summary['unverified_count']}/{cited_summary['total_cited']} "
                f"të cituar NUK ekzistojnë në DB — "
                f"{cited_summary['unverified'][:5]}"
                + ("..." if cited_summary["unverified_count"] > 5 else "")
            )
        else:
            logger.info(
                f"✅ [VERIFY V2.6] CITED PRECEDENTS: "
                f"{cited_summary['verified_count']}/{cited_summary['total_cited']} "
                f"të verifikuar"
            )

        if progress_callback:
            try:
                progress_callback("step_started", {
                    "step_key": "precedents",
                    "step_title": "Duke kërkuar precedentë në Gjykatën Supreme...",
                })
            except Exception:
                pass

        t0 = time.time()
        precedents: List[Dict[str, Any]] = []
        try:
            query = build_precedent_query(
                document_type=doc_type_label,
                file_name=file_name,
                doc_text=doc_text,
                case_type=None,
            )
            precedents = search_relevant_precedents(
                self.db, query,
                top_k=PRECEDENT_TOP_K,
                threshold=PRECEDENT_SIMILARITY_THRESHOLD,
            ) or []
            logger.info(
                f"🏛️ [VERIFY] Precedent search: {len(precedents)} rezultate "
                f"(top_k={PRECEDENT_TOP_K}, threshold={PRECEDENT_SIMILARITY_THRESHOLD})"
            )
        except Exception as e:
            logger.error(f"❌ [VERIFY] Precedent search failed: {e}")
            precedents = []
        _lap("search_relevant_precedents", t0)

        found_precedent_cases: Set[str] = set()
        for p in precedents:
            cn = (p.get("case_number") or "").strip()
            if cn:
                found_precedent_cases.add(cn)

        sections: Dict[str, Dict[str, Any]] = {}
        section_stats: Dict[str, Any] = {}
        sections_start = time.time()

        logger.info(
            f"🚀 [VERIFY PARALLEL V2.6] {len(VERIFY_SECTION_KEYS)} seksione, "
            f"max_workers={MAX_CONCURRENT_VERIFY_SECTIONS}"
        )

        # V2.6: import në module-level (jo brenda funksionit)
        _callback_lock = threading.Lock()

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

        def _synthesize_prompt(
            log_key: str,
            prompt_cfg: Dict[str, Any],
            verified_context: str,
        ) -> str:
            return synthesize_section_streaming(
                section_key=log_key,
                section_cfg=prompt_cfg,
                verified_context=verified_context,
                file_name=file_name,
                document_type=doc_type_label,
                stream_callback=None,
            )

        def _run_section(
            section_key: str,
        ) -> Tuple[str, Dict[str, Any], Dict[str, Any]]:
            section_start = time.time()
            section_cfg = VERIFY_SECTION_PROMPTS[section_key]
            section_title = section_cfg["title"]
            section_max_tokens = section_cfg.get("max_tokens", 2500)

            sub_prompts: Optional[List[str]] = section_cfg.get("sub_prompts")

            t_ctx = time.time()
            try:
                verified_context = build_verify_context(
                    doc_type=doc_type,
                    doc_text=doc_text,
                    file_name=file_name,
                    section_key=section_key,
                    precedents=precedents if "precedents" in section_cfg.get("needs", []) else None,
                    verification_report=(
                        verification_report
                        if "articles" in section_cfg.get("needs", [])
                        else None
                    ),
                    case_profile=(
                        case_profile
                        if "case_context" in section_cfg.get("needs", [])
                        else None
                    ),
                )
            except Exception as e:
                logger.error(f"❌ [VERIFY {section_key}] Context build failed: {e}")
                return (
                    section_key,
                    {"title": section_title, "content": "", "error": f"context_build_failed: {e}"},
                    {"duration_sec": round(time.time() - section_start, 2), "error": str(e)},
                )
            ctx_build_time = time.time() - t_ctx

            # SPLIT MODE
            if sub_prompts:
                logger.info(
                    f"▶️ [VERIFY {section_key}] start (SPLIT into "
                    f"{len(sub_prompts)} sub-prompts, ctx={len(verified_context)} chars, "
                    f"ctx_build={ctx_build_time*1000:.0f}ms) — {section_title}"
                )

                _emit_progress("section_started", {
                    "section_key": section_key,
                    "section_title": section_title,
                })

                sub_results: Dict[str, str] = {}
                sub_timings: Dict[str, float] = {}

                def _run_sub(sub_key: str) -> Tuple[str, str, float]:
                    sub_start = time.time()
                    sub_cfg = VERIFY_SECTION_PROMPTS.get(sub_key)
                    if not sub_cfg:
                        logger.error(f"❌ [VERIFY {section_key}] Sub-prompt '{sub_key}' nuk ekziston")
                        return sub_key, "", 0.0
                    sub_max = sub_cfg.get("max_tokens", 1500)
                    logger.info(
                        f"▶️ [VERIFY {section_key}::{sub_key}] start "
                        f"(max_tokens={sub_max}) — {sub_cfg.get('title', sub_key)}"
                    )
                    try:
                        raw = _synthesize_prompt(
                            log_key=f"{section_key}::{sub_key}",
                            prompt_cfg=sub_cfg,
                            verified_context=verified_context,
                        )
                        elapsed = round(time.time() - sub_start, 2)
                        logger.info(
                            f"✅ [VERIFY {section_key}::{sub_key}] done: "
                            f"{elapsed}s, {len(raw)} chars"
                        )
                        return sub_key, raw, elapsed
                    except Exception as e:
                        elapsed = round(time.time() - sub_start, 2)
                        logger.error(
                            f"❌ [VERIFY {section_key}::{sub_key}] failed "
                            f"after {elapsed}s: {e}"
                        )
                        return sub_key, "", elapsed

                try:
                    with concurrent.futures.ThreadPoolExecutor(
                        max_workers=len(sub_prompts),
                        thread_name_prefix=f"verify_split_{section_key}",
                    ) as sub_ex:
                        sub_futures = {
                            sub_ex.submit(_run_sub, sk): sk
                            for sk in sub_prompts
                        }
                        for sfut in concurrent.futures.as_completed(sub_futures):
                            sk = sub_futures[sfut]
                            try:
                                sub_key, raw, sub_elapsed = sfut.result()
                                sub_results[sub_key] = raw
                                sub_timings[sub_key] = sub_elapsed
                            except Exception as e:
                                logger.error(
                                    f"❌ [VERIFY {section_key}] sub future "
                                    f"failed for {sk}: {e}"
                                )
                except Exception as e:
                    logger.error(
                        f"❌ [VERIFY {section_key}] split ThreadPoolExecutor "
                        f"failed: {e} — fallback në prompt-in e parent-it"
                    )
                    try:
                        raw = _synthesize_prompt(
                            log_key=section_key,
                            prompt_cfg=section_cfg,
                            verified_context=verified_context,
                        )
                        sub_results = {section_key: raw}
                        sub_timings = {section_key: round(time.time() - section_start, 2)}
                    except Exception as e2:
                        logger.error(f"❌ [VERIFY {section_key}] parent fallback failed: {e2}")

                ordered_parts: List[str] = []
                for sk in sub_prompts:
                    part = sub_results.get(sk, "")
                    if part and part.strip():
                        ordered_parts.append(part.strip())

                merged = "\n\n".join(ordered_parts)

                content = post_process_section(
                    section_key=section_key,
                    llm_content=merged,
                    verification_report=verification_report,
                    precedents=precedents,
                )

                elapsed = round(time.time() - section_start, 2)

                logger.info(
                    f"✅ [VERIFY {section_key}] done (SPLIT merged): "
                    f"{elapsed}s, {len(content)} chars "
                    f"(sub_timings: {sub_timings})"
                )

                return (
                    section_key,
                    {"title": section_title, "content": content},
                    {
                        "duration_sec": elapsed,
                        "content_length": len(content),
                        "split_mode": True,
                        "sub_prompts": sub_prompts,
                        "sub_timings": sub_timings,
                        "context_chars": len(verified_context),
                        "max_tokens": section_max_tokens,
                    },
                )

            # SJELLJA EKZISTUESE
            logger.info(
                f"▶️ [VERIFY {section_key}] start "
                f"(max_tokens={section_max_tokens}, ctx={len(verified_context)} chars, "
                f"ctx_build={ctx_build_time*1000:.0f}ms) — {section_title}"
            )

            _emit_progress("section_started", {
                "section_key": section_key,
                "section_title": section_title,
            })

            try:
                raw_llm_content = _synthesize_prompt(
                    log_key=section_key,
                    prompt_cfg=section_cfg,
                    verified_context=verified_context,
                )

                content = post_process_section(
                    section_key=section_key,
                    llm_content=raw_llm_content,
                    verification_report=verification_report,
                    precedents=precedents,
                )

                elapsed = round(time.time() - section_start, 2)

                logger.info(
                    f"✅ [VERIFY {section_key}] done: {elapsed}s, "
                    f"{len(content)} chars (llm_raw={len(raw_llm_content)}, "
                    f"python_prefix={len(content) - len(raw_llm_content)})"
                )

                return (
                    section_key,
                    {"title": section_title, "content": content},
                    {
                        "duration_sec": elapsed,
                        "content_length": len(content),
                        "llm_raw_length": len(raw_llm_content),
                        "python_prefix_length": len(content) - len(raw_llm_content),
                        "context_chars": len(verified_context),
                        "max_tokens": section_max_tokens,
                    },
                )

            except Exception as e:
                elapsed = round(time.time() - section_start, 2)
                logger.error(f"❌ [VERIFY {section_key}] failed after {elapsed}s: {e}")
                return (
                    section_key,
                    {"title": section_title, "content": "", "error": str(e)},
                    {"duration_sec": elapsed, "error": str(e)},
                )

        try:
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=MAX_CONCURRENT_VERIFY_SECTIONS,
                thread_name_prefix="draft_verify",
            ) as executor:
                futures = {
                    executor.submit(_run_section, k): k
                    for k in VERIFY_SECTION_KEYS
                }
                for fut in concurrent.futures.as_completed(futures):
                    key = futures[fut]
                    try:
                        k, sec_entry, stat_entry = fut.result()
                        sections[k] = sec_entry
                        section_stats[k] = stat_entry
                        if sec_entry.get("content"):
                            _emit_section(k, sec_entry["content"])
                        if not sec_entry.get("error"):
                            _emit_progress("section_completed", {
                                "section_key": k,
                                "section_title": sec_entry["title"],
                                "content_length": stat_entry.get("content_length", 0),
                            })
                    except Exception as e:
                        logger.error(f"❌ [VERIFY PARALLEL] Future failed for {key}: {e}")

        except Exception as e:
            logger.error(f"❌ [VERIFY PARALLEL] ThreadPoolExecutor failed: {e}")
            logger.info("🔄 [VERIFY] Fallback në sequential mode")
            for section_key in VERIFY_SECTION_KEYS:
                try:
                    k, sec_entry, stat_entry = _run_section(section_key)
                    sections[k] = sec_entry
                    section_stats[k] = stat_entry
                    if sec_entry.get("content"):
                        _emit_section(k, sec_entry["content"])
                except Exception as e2:
                    logger.error(f"❌ [VERIFY SEQUENTIAL] {section_key}: {e2}")

        sections = {k: sections[k] for k in VERIFY_SECTION_KEYS if k in sections}
        section_stats = {k: section_stats[k] for k in VERIFY_SECTION_KEYS if k in section_stats}

        sections_total_time = round(time.time() - sections_start, 2)
        logger.info(
            f"⏱️ [VERIFY TIMING] sections_total (parallel x{MAX_CONCURRENT_VERIFY_SECTIONS}): "
            f"{sections_total_time}s"
        )

        # ═══════════════════════════════════════════════════════════════════
        # V2.6: db_laws INIT — para if-block për të shmangur NameError
        # ═══════════════════════════════════════════════════════════════════
        db_laws: Set[str] = set()

        # ═══════════════════════════════════════════════════════════════════
        # ANTI-HALLUCINATION CHECK
        # ═══════════════════════════════════════════════════════════════════
        hallucination_report: Dict[str, Any] = {}
        if HALLUCINATION_GATE_ENABLED and fact_profile:
            if progress_callback:
                try:
                    progress_callback("step_started", {
                        "step_key": "hallucination_check",
                        "step_title": "Duke kontrolluar saktësinë e fakteve...",
                    })
                except Exception:
                    pass

            precedent_dates: Set[str] = set()
            for p in precedents:
                excerpt = (p.get("text_excerpt") or "").strip()
                if excerpt:
                    try:
                        precedent_dates.update(_extract_dates_iso(excerpt))
                    except Exception as _e:
                        logger.warning(
                            f"⚠️ [VERIFY V2.6] Date extract failed for "
                            f"precedent {p.get('case_number')}: {_e}"
                        )
            if precedent_dates:
                logger.info(
                    f"📅 [VERIFY V2.6] Precedent excerpt dates (allowed): "
                    f"{sorted(precedent_dates)}"
                )

            precedent_articles = extract_precedent_articles(precedents)
            if precedent_articles:
                logger.info(
                    f"📅 [VERIFY V2.6] Precedent excerpt articles (allowed): "
                    f"{sorted(precedent_articles)}"
                )

            precedent_cases = extract_precedent_cases(precedents)
            all_allowed_cases: Set[str] = set(found_precedent_cases)
            if precedent_cases:
                new_cases = precedent_cases - all_allowed_cases
                if new_cases:
                    logger.info(
                        f"📅 [VERIFY V2.6] Precedent excerpt cases (allowed): "
                        f"{sorted(new_cases)}"
                    )
                all_allowed_cases.update(precedent_cases)

            if case_profile and case_profile.get("has_context"):
                cp_dates = case_profile.get("dates_set") or set()
                cp_cases = case_profile.get("cases_set") or set()
                cp_articles = case_profile.get("articles_set") or set()

                new_dates = cp_dates - precedent_dates
                new_cases = cp_cases - all_allowed_cases
                new_articles = cp_articles - precedent_articles

                if new_dates:
                    logger.info(
                        f"📅 [VERIFY V2.6] Case profile dates added to allowed: "
                        f"{len(new_dates)} vlera"
                    )
                if new_cases:
                    logger.info(
                        f"📅 [VERIFY V2.6] Case profile cases added to allowed: "
                        f"{len(new_cases)} vlera"
                    )
                if new_articles:
                    logger.info(
                        f"📅 [VERIFY V2.6] Case profile articles added to allowed: "
                        f"{len(new_articles)} vlera"
                    )

                precedent_dates = set(precedent_dates) | cp_dates
                all_allowed_cases = all_allowed_cases | cp_cases
                precedent_articles = set(precedent_articles) | cp_articles

            # V2.5: DYNAMIC DB LAWS (V2.6: db_laws inicializuar më lart)
            t_db = time.time()
            try:
                db_laws = get_all_law_numbers_from_db(self.db)
            except Exception as e:
                logger.warning(f"⚠️ [V2.6] get_all_law_numbers_from_db dështoi: {e}")
                db_laws = set()
            logger.info(
                f"⏱️ [VERIFY TIMING] db_laws_fetch: {time.time() - t_db:.2f}s "
                f"({len(db_laws)} ligje nga DB)"
            )

            t0 = time.time()
            try:
                hallucination_report = check_all_sections(
                    sections=sections,
                    citation_profile=citation_profile,
                    fact_profile=fact_profile,
                    verification_report=verification_report,
                    extra_allowed_cases=all_allowed_cases,
                    extra_allowed_dates=precedent_dates,
                    extra_allowed_articles=precedent_articles,
                    extra_allowed_laws=db_laws,
                )
                logger.info(
                    f"🧪 [VERIFY V2.6] Hallucination: "
                    f"status={hallucination_report.get('status')}, "
                    f"issues={hallucination_report.get('total_issues', 0)} "
                    f"(high={hallucination_report.get('severity_totals', {}).get('high', 0)}, "
                    f"medium={hallucination_report.get('severity_totals', {}).get('medium', 0)}, "
                    f"low={hallucination_report.get('severity_totals', {}).get('low', 0)}), "
                    f"suspicious={hallucination_report.get('suspicious_sections', [])}"
                )
            except Exception as e:
                logger.error(f"❌ [VERIFY] check_all_sections failed: {e}")
                hallucination_report = {}
            _lap("hallucination_check", t0)
        elif not HALLUCINATION_GATE_ENABLED:
            logger.info("ℹ️ [VERIFY V2.6] Hallucination gate çaktivizuar (env)")
        elif not fact_profile:
            logger.warning("⚠️ [VERIFY V2.6] Fact profile bosh — halluzinacioni nuk u kontrollua")

        # ═══════════════════════════════════════════════════════════════════
        # READINESS OVERRIDE
        # ═══════════════════════════════════════════════════════════════════
        readiness = parse_readiness(sections)
        readiness_before_override = readiness

        if hallucination_report.get("status") == "suspect":
            readiness = maybe_override_readiness(
                readiness=readiness,
                hallucination_report=hallucination_report,
                sections=sections,
            )

        critical_count = count_critical_recommendations(sections)
        if critical_count > 0:
            logger.info(
                f"🔍 [VERIFY V2.6] U gjetën {critical_count} rekomandime "
                f"KRITIKE [#K] në Section 5 (concrete_recommendations)"
            )
        readiness = maybe_override_readiness_for_critical(
            readiness=readiness,
            sections=sections,
        )

        readiness_overridden = readiness != readiness_before_override

        score, score_breakdown = calculate_score(
            sections=sections,
            verification_report=verification_report,
            readiness=readiness,
        )

        full_report = build_full_report(
            sections=sections,
            doc_type_label=doc_type_label,
            file_name=file_name,
            readiness=readiness,
        )

        if hallucination_report.get("status") == "suspect":
            warning_banner = build_hallucination_warning(hallucination_report)
            if warning_banner:
                full_report = warning_banner + full_report

        if cited_summary["unverified_count"] > 0:
            cited_banner = build_cited_precedents_warning(cited_summary)
            if cited_banner:
                full_report = cited_banner + full_report

        duration = round(time.time() - start, 2)

        vstats = verification_report.get("stats", {}) or {}
        articles_total = int(vstats.get("articles_total", 0) or 0)
        articles_verified = int(vstats.get("articles_verified", 0) or 0)
        legal_pct = score_breakdown.get("legal", 0.0)
        formal_pct = score_breakdown.get("formal", 0.0)
        readiness_score = int(score_breakdown.get("readiness", 0))

        h_sev = (hallucination_report or {}).get("severity_totals", {}) or {}

        # ═══════════════════════════════════════════════════════════════════
        # V2.5: QUALITY METRICS
        # ═══════════════════════════════════════════════════════════════════
        t0 = time.time()
        quality_metrics = compute_quality_metrics(
            sections=sections,
            section_stats=section_stats,
            hallucination_report=hallucination_report,
        )
        _lap("quality_metrics", t0)
        log_quality_metrics(quality_metrics)

        result: Dict[str, Any] = {
            "case_id": case_id,
            "document_id": document_id,
            "doc_type": doc_type,
            "doc_type_label": doc_type_label,
            "file_name": file_name,
            "built_at": datetime.now(timezone.utc).isoformat(),
            "sections": sections,
            "stats": {
                "case_id": case_id,
                "document_id": document_id,
                "doc_type": doc_type,
                "doc_type_label": doc_type_label,
                "file_name": file_name,
                "text_length": len(doc_text),
                "sections_generated": len([s for s in sections.values() if s.get("content")]),
                "sections_total": len(VERIFY_SECTION_KEYS),
                "report_chars": len(full_report),
                "duration_sec": duration,
                "execution_mode": "verify_hybrid_v2.6",
                "precedents_found": len(precedents),
                "precedent_threshold": PRECEDENT_SIMILARITY_THRESHOLD,
                "precedent_top_k": PRECEDENT_TOP_K,
                "articles_total": articles_total,
                "articles_verified": articles_verified,
                "sections_total_sec": sections_total_time,
                "formal_pct": formal_pct,
                "legal_pct": legal_pct,
                "readiness_score": readiness_score,
                "readiness_overridden": readiness_overridden,
                "readiness_before_override": readiness_before_override,
                "critical_recommendations_count": critical_count,
                "hallucination_status": hallucination_report.get("status", "not_checked"),
                "hallucination_issues": hallucination_report.get("total_issues", 0),
                "hallucination_high": h_sev.get("high", 0),
                "hallucination_medium": h_sev.get("medium", 0),
                "hallucination_low": h_sev.get("low", 0),
                "hallucination_suspicious_sections": hallucination_report.get("suspicious_sections", []),
                "hallucination_enabled": HALLUCINATION_GATE_ENABLED,
                "cited_precedents_total": cited_summary["total_cited"],
                "cited_precedents_verified": cited_summary["verified_count"],
                "cited_precedents_unverified": cited_summary["unverified_count"],
                "cited_precedents_unverified_list": cited_summary["unverified"],
                "case_profile_active": bool(case_profile.get("has_context")),
                "case_profile_stats": case_profile.get("stats", {}),
                "db_laws_count": len(db_laws),
                "quality_metrics": quality_metrics,
            },
            "readiness": readiness,
            "score": score,
            "score_breakdown": score_breakdown,
            "full_report": full_report,
            "section_stats": section_stats,
            "status": "completed",
        }

        if hallucination_report:
            result["hallucination_report"] = hallucination_report

        t0 = time.time()
        persisted = persist_verification(
            self.db, case_id, document_id, result
        )
        _lap("persist_verification", t0)

        result["persisted"] = persisted

        logger.info(
            f"✅ [VERIFY V2.6] Complete: "
            f"sections={result['stats']['sections_generated']}/{result['stats']['sections_total']}, "
            f"readiness={readiness}"
            + (f" (override from {readiness_before_override})" if readiness_overridden else "")
            + f", score={score} "
            f"(formal={formal_pct}%, legal={legal_pct}%, readiness={readiness_score}), "
            f"quality={quality_metrics['quality_score']}/100, "
            f"cost=${quality_metrics['cost_estimate_usd']}, "
            f"db_laws={len(db_laws)}, "
            f"precedents={len(precedents)}, "
            f"articles={articles_verified}/{articles_total}, "
            f"cited_precedents={cited_summary['verified_count']}/{cited_summary['total_cited']}"
            + (f" (⚠️ {cited_summary['unverified_count']} unverified)"
               if cited_summary["unverified_count"] > 0 else "")
            + f", "
            f"critical_recommendations={critical_count}, "
            f"case_profile_active={result['stats']['case_profile_active']}, "
            f"hallucination={result['stats']['hallucination_status']} "
            f"({result['stats']['hallucination_issues']} issues), "
            f"report_chars={len(full_report)}, duration={duration}s, "
            f"persisted={persisted}"
        )

        return result


def get_draft_verifier(db) -> DraftVerifier:
    return DraftVerifier(db)