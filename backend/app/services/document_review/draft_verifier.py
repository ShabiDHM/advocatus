# FILE: backend/app/services/document_review/draft_verifier.py
# PHOENIX PROTOCOL - DRAFT VERIFIER V1.3
# V1.3: SCORE + ENHANCED STATS — _calculate_score() + _extract_formal_pct()
#       + score_breakdown. Statistikat e plota për frontend:
#       - score (0-100), score_breakdown {formal, legal, readiness}
#       - formal_pct, legal_pct, readiness_score
#       - articles_verified/total, precedents_found, duration, chars
# V1.2: _parse_readiness njeh shqip + anglisht.
# V1.1: READINESS SHQIP.
# V1.0: "Verifiko Draftin" — 6 seksione.

import os
import re
import time
import logging
import concurrent.futures
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Callable, Tuple

from bson import ObjectId
from bson.errors import InvalidId

from .citation_extractor import build_citation_profile
from .mongo_verifier import verify_all
from .streaming import synthesize_section_streaming
from .persistence import load_document, load_extraction
from .precedent_search import (
    build_precedent_query,
    search_relevant_precedents,
    PRECEDENT_SIMILARITY_THRESHOLD,
    PRECEDENT_TOP_K,
)
from .verify_prompts import (
    VERIFY_SECTION_PROMPTS,
    VERIFY_SECTION_KEYS,
    VERIFY_DOC_TYPES,
    build_verify_context,
)

logger = logging.getLogger(__name__)

MAX_CONCURRENT_VERIFY_SECTIONS = int(
    os.getenv("VERIFY_MAX_WORKERS", os.getenv("DOC_REVIEW_MAX_WORKERS", "3"))
)

# V1.1: Map readiness → shqip
READINESS_LABELS_SQ: Dict[str, str] = {
    "READY":       "GATI",
    "NEEDS WORK":  "KËRKON PUNË",
    "INCOMPLETE":  "I PËRPLOTË",
    "UNKNOWN":     "I PANJOHUR",
}

# V1.3: Readiness → score (0-100)
READINESS_SCORES: Dict[str, int] = {
    "READY":       100,
    "NEEDS WORK":  65,
    "INCOMPLETE":  30,
    "UNKNOWN":     0,
}


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _empty_verify_result(
    case_id: str,
    document_id: str,
    message: str,
    doc_type: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "case_id": case_id,
        "document_id": document_id,
        "doc_type": doc_type,
        "doc_type_label": VERIFY_DOC_TYPES.get(doc_type, "—") if doc_type else "—",
        "file_name": None,
        "built_at": datetime.now(timezone.utc).isoformat(),
        "sections": {},
        "stats": {
            "sections_generated": 0,
            "sections_total": len(VERIFY_SECTION_KEYS),
            "duration_sec": 0.0,
            "precedents_found": 0,
            "articles_total": 0,
            "articles_verified": 0,
            "execution_mode": "none",
            "formal_pct": 0.0,
            "legal_pct": 0.0,
            "readiness_score": 0,
        },
        "readiness": "UNKNOWN",
        "score": 0,
        "score_breakdown": {"formal": 0.0, "legal": 0.0, "readiness": 0},
        "full_report": f"# Raport Verifikimi\n\n⚠️ {message}\n",
        "status": "error",
        "error_message": message,
    }


def _parse_readiness(sections: Dict[str, Dict[str, Any]]) -> str:
    """
    V1.2: Njeh edhe terma shqip edhe anglezë.
    """
    sec = sections.get("readiness")
    if not sec or not sec.get("content"):
        return "UNKNOWN"

    content_upper = sec["content"].upper()

    if (
        re.search(r'\bINCOMPLETE\b', content_upper)
        or re.search(r'\bI PËRPLOTË\b', content_upper)
        or re.search(r'\bI PERPLOTE\b', content_upper)
    ):
        return "INCOMPLETE"

    if (
        re.search(r'\bNEEDS WORK\b', content_upper)
        or re.search(r'\bNEEDS_WORK\b', content_upper)
        or re.search(r'\bKËRKON PUNË\b', content_upper)
        or re.search(r'\bKERKON PUNE\b', content_upper)
    ):
        return "NEEDS WORK"

    if (
        re.search(r'\bREADY\b', content_upper)
        or re.search(r'\bGATI\b', content_upper)
    ):
        return "READY"

    return "UNKNOWN"


def _extract_formal_pct(sections: Dict[str, Dict[str, Any]]) -> float:
    """
    V1.3: Nxjerr përqindjen formale nga seksioni 1.
    Provo modele:
      - "11/14 pjesë të pranishme (78.57%)"
      - "13/14 pjesë të pranishme (92.86%)"
      - "(78.57%)" kudo në content
    """
    sec = sections.get("formal_completeness")
    if not sec:
        return 0.0

    content = sec.get("content") or ""

    # Model 1: me pjesë/pranishme
    m = re.search(
        r'(\d+)\s*/\s*(\d+)\s*pjes[ëe]?\s*(?:t[ëe]\s*)?pranishme\s*\(\s*(\d+(?:[.,]\d+)?)\s*%\s*\)',
        content,
        re.IGNORECASE,
    )
    if m:
        try:
            return float(m.group(3).replace(",", "."))
        except ValueError:
            pass

    # Model 2: vetëm përqindja në kllapa
    m2 = re.search(r'\(\s*(\d+(?:[.,]\d+)?)\s*%\s*\)', content)
    if m2:
        try:
            return float(m2.group(1).replace(",", "."))
        except ValueError:
            pass

    return 0.0


def _calculate_score(
    sections: Dict[str, Dict[str, Any]],
    verification_report: Dict[str, Any],
    readiness: str,
) -> Tuple[int, Dict[str, float]]:
    """
    V1.3: Llogarit score 0-100 për verifikimin.

    Formula:
      formal_pct * 0.35    → plotësia formale
      legal_pct  * 0.35    → cilësia ligjore (nene të verifikuar)
      readiness_score * 0.30 → gatishmëria

    Kthen (score, breakdown)
    """
    formal_pct = _extract_formal_pct(sections)

    # Legal pct: articles verified / total
    stats = verification_report.get("stats", {}) or {}
    articles_total = int(stats.get("articles_total", 0) or 0)
    articles_verified = int(stats.get("articles_verified", 0) or 0)

    if articles_total > 0:
        legal_pct = (articles_verified / articles_total) * 100.0
    else:
        legal_pct = 70.0  # neutral kur nuk citohen nene

    readiness_pct = float(READINESS_SCORES.get(readiness, 0))

    score = formal_pct * 0.35 + legal_pct * 0.35 + readiness_pct * 0.30
    score_int = int(round(min(100.0, max(0.0, score))))

    breakdown = {
        "formal": round(formal_pct, 1),
        "legal": round(legal_pct, 1),
        "readiness": readiness_pct,
    }

    return score_int, breakdown


def _build_full_report(
    sections: Dict[str, Dict[str, Any]],
    doc_type_label: str,
    file_name: str,
    readiness: str,
) -> str:
    """
    V1.1: Monton raportin në shqip.
    """
    built_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    readiness_sq = READINESS_LABELS_SQ.get(readiness, readiness)

    lines: List[str] = []
    lines.append(f"# RAPORT VERIFIKIMI — {doc_type_label}")
    lines.append("")
    lines.append(f"**Dokumenti:** `{file_name}`  ")
    lines.append(f"**Data:** {built_at}  ")
    lines.append(f"**Gatishmëria:** **{readiness_sq}**")
    lines.append("")
    lines.append("---")
    lines.append("")

    for key in VERIFY_SECTION_KEYS:
        sec = sections.get(key)
        if not sec:
            continue
        title = sec.get("title") or VERIFY_SECTION_PROMPTS[key]["title"]
        content = sec.get("content") or "_(pa përmbajtje)_"
        lines.append(f"## {title}")
        lines.append("")
        lines.append(content)
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines).strip()


def _persist_verification(
    db,
    case_id: str,
    document_id: str,
    verification_entry: Dict[str, Any],
) -> bool:
    try:
        try:
            c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
        except InvalidId:
            c_oid = case_id

        minimal = {
            "doc_type": verification_entry.get("doc_type"),
            "doc_type_label": verification_entry.get("doc_type_label"),
            "file_name": verification_entry.get("file_name"),
            "built_at": verification_entry.get("built_at"),
            "readiness": verification_entry.get("readiness"),
            "score": verification_entry.get("score"),
            "score_breakdown": verification_entry.get("score_breakdown"),
            "full_report": verification_entry.get("full_report"),
            "stats": verification_entry.get("stats"),
            "status": verification_entry.get("status"),
        }

        result = db.cases.update_one(
            {"_id": c_oid},
            {"$set": {
                f"case_document_verifications.{document_id}": minimal,
            }},
            upsert=False,
        )

        if result.matched_count == 0:
            logger.warning(
                f"⚠️ [VERIFY PERSIST] Case nuk u gjet: case={case_id}, doc={document_id}"
            )
            return False

        logger.info(
            f"💾 [VERIFY PERSIST] Ruajtur: case={case_id}, doc={document_id}, "
            f"readiness={minimal['readiness']}, score={minimal['score']}, "
            f"report_chars={len(minimal['full_report'] or '')}"
        )
        return True

    except Exception as e:
        logger.error(f"❌ [VERIFY PERSIST] Dështoi: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════════════
# SERVICE
# ═══════════════════════════════════════════════════════════════════════════

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
            logger.warning(f"⏱️ [VERIFY TIMING] {label}: {elapsed:.2f}s")
            return elapsed

        # ═══ 0. VALIDIM ═══
        if doc_type not in VERIFY_DOC_TYPES:
            msg = (
                f"Lloj dokumenti i panjohur: '{doc_type}'. "
                f"Të lejuara: {sorted(VERIFY_DOC_TYPES.keys())}"
            )
            logger.error(f"❌ [VERIFY] {msg}")
            return _empty_verify_result(case_id, document_id, msg, doc_type)

        doc_type_label = VERIFY_DOC_TYPES[doc_type]

        # ═══ 1. LOAD ═══
        t0 = time.time()
        try:
            document = load_document(self.db, case_id, document_id)
            extraction = load_extraction(self.db, case_id, document_id)
        except Exception as e:
            logger.error(f"❌ [VERIFY] Load failed: {e}")
            return _empty_verify_result(
                case_id, document_id, f"Gabim gjatë leximit: {e}", doc_type
            )
        _lap("load_document+extraction", t0)

        if not document and not extraction:
            return _empty_verify_result(
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
            return _empty_verify_result(
                case_id, document_id, "Drafti nuk ka tekst për verifikim.", doc_type
            )

        file_name = (document or {}).get("file_name", "draft")

        logger.info(
            f"🔎 [VERIFY V1.3] Start: case={case_id}, doc={document_id}, "
            f"file={file_name}, doc_type={doc_type} ({doc_type_label}), "
            f"len={len(doc_text)} chars, user={user_id or '?'}, "
            f"parallel x{MAX_CONCURRENT_VERIFY_SECTIONS}"
        )

        # ═══ 2. CITATION + VERIFY_ALL ═══
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

        # ═══ 3. PRECEDENT SEARCH ═══
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

        # ═══ 4. 6 SEKSIONE — PARALLEL ═══
        sections: Dict[str, Dict[str, Any]] = {}
        section_stats: Dict[str, Any] = {}
        sections_start = time.time()

        logger.warning(
            f"🚀 [VERIFY PARALLEL] {len(VERIFY_SECTION_KEYS)} seksione, "
            f"max_workers={MAX_CONCURRENT_VERIFY_SECTIONS}"
        )

        import threading
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

        def _run_section(
            section_key: str,
        ) -> Tuple[str, Dict[str, Any], Dict[str, Any]]:
            section_start = time.time()
            section_cfg = VERIFY_SECTION_PROMPTS[section_key]
            section_title = section_cfg["title"]
            section_max_tokens = section_cfg.get("max_tokens", 2500)

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
                )
            except Exception as e:
                logger.error(f"❌ [VERIFY {section_key}] Context build failed: {e}")
                return (
                    section_key,
                    {"title": section_title, "content": "", "error": f"context_build_failed: {e}"},
                    {"duration_sec": round(time.time() - section_start, 2), "error": str(e)},
                )
            ctx_build_time = time.time() - t_ctx

            logger.warning(
                f"▶️ [VERIFY {section_key}] start "
                f"(max_tokens={section_max_tokens}, ctx={len(verified_context)} chars, "
                f"ctx_build={ctx_build_time*1000:.0f}ms) — {section_title}"
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
                    document_type=doc_type_label,
                    stream_callback=None,
                )
                elapsed = round(time.time() - section_start, 2)

                logger.warning(
                    f"✅ [VERIFY {section_key}] done: {elapsed}s, {len(content)} chars"
                )

                return (
                    section_key,
                    {"title": section_title, "content": content},
                    {
                        "duration_sec": elapsed,
                        "content_length": len(content),
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
            logger.warning("🔄 [VERIFY] Fallback në sequential mode")
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
        logger.warning(
            f"⏱️ [VERIFY TIMING] sections_total (parallel x{MAX_CONCURRENT_VERIFY_SECTIONS}): "
            f"{sections_total_time}s"
        )

        # ═══ 5. MONTIM RAPORTI + SCORE ═══
        readiness = _parse_readiness(sections)

        # V1.3: Llogarit score
        score, score_breakdown = _calculate_score(
            sections=sections,
            verification_report=verification_report,
            readiness=readiness,
        )

        full_report = _build_full_report(
            sections=sections,
            doc_type_label=doc_type_label,
            file_name=file_name,
            readiness=readiness,
        )

        duration = round(time.time() - start, 2)

        # V1.3: Statistikat e plota për frontend
        vstats = verification_report.get("stats", {}) or {}
        articles_total = int(vstats.get("articles_total", 0) or 0)
        articles_verified = int(vstats.get("articles_verified", 0) or 0)
        legal_pct = score_breakdown.get("legal", 0.0)
        formal_pct = score_breakdown.get("formal", 0.0)
        readiness_score = int(score_breakdown.get("readiness", 0))

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
                "execution_mode": f"verify_parallel_x{MAX_CONCURRENT_VERIFY_SECTIONS}_v1.3",
                "precedents_found": len(precedents),
                "precedent_threshold": PRECEDENT_SIMILARITY_THRESHOLD,
                "precedent_top_k": PRECEDENT_TOP_K,
                "articles_total": articles_total,
                "articles_verified": articles_verified,
                "sections_total_sec": sections_total_time,
                # V1.3: fusha të reja
                "formal_pct": formal_pct,
                "legal_pct": legal_pct,
                "readiness_score": readiness_score,
            },
            "readiness": readiness,
            "score": score,
            "score_breakdown": score_breakdown,
            "full_report": full_report,
            "section_stats": section_stats,
            "status": "completed",
        }

        # ═══ 6. PERSIST ═══
        t0 = time.time()
        persisted = _persist_verification(
            self.db, case_id, document_id, result
        )
        _lap("persist_verification", t0)

        result["persisted"] = persisted

        logger.info(
            f"✅ [VERIFY V1.3] Complete: "
            f"sections={result['stats']['sections_generated']}/{result['stats']['sections_total']}, "
            f"readiness={readiness}, score={score} "
            f"(formal={formal_pct}%, legal={legal_pct}%, readiness={readiness_score}), "
            f"precedents={len(precedents)}, "
            f"articles={articles_verified}/{articles_total}, "
            f"report_chars={len(full_report)}, duration={duration}s, "
            f"persisted={persisted}"
        )

        return result


# ═══════════════════════════════════════════════════════════════════════════
# FACTORY
# ═══════════════════════════════════════════════════════════════════════════

def get_draft_verifier(db) -> DraftVerifier:
    return DraftVerifier(db)