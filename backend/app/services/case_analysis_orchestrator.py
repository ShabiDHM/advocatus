# FILE: backend/app/services/case_analysis_orchestrator.py
# PHOENIX PROTOCOL - CASE ANALYSIS ORCHESTRATOR V1.9
# V1.9: SYNTHESIS REMOVED — Hequr dega CASE MODE dhe varësitë nga synthesis:
#       - Importi get_synthesis_service dhe atributi self.synthesis
#       - Importi get_cross_reference_service dhe self.xref_service
#       - Konstantet SECTION_ORDER, CROSS_REF_COLLECTION
#       - Metodat _get_existing_xref, _get_existing_case_synthesis
#       - Metoda _build_markdown_from_case_synthesis
#       - Dega CASE MODE në run() — tani vetëm single-document mode.
#       Router V1.12 e bllokon analizën pa document_ids me 400; orchestratori
#       ka mbrojtje të brendshme në rast thirrjeje direkte.
# V1.8.2: RIGOROUS ANALYSIS — shtuar "analiza_e_thelluar" ne
#         DOCUMENT_REVIEW_SECTION_ORDER per ta shfaqur ne raport.
# V1.8.1: NO HARDCODE — _normalize_client_position kthen raw value.
# V1.8: CLIENT POSITION — lexon case.client_position.
# V1.7: CLIENT CONTEXT — client_name.
# V1.6: CACHE INVALIDATION DINAMIK.
# V1.5: Removed document_ids param from synthesis call.

import asyncio
import hashlib
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, AsyncGenerator

from bson import ObjectId

from app.services.extraction_pipeline import get_extraction_pipeline
from app.services.document_review_service import get_document_review_service

logger = logging.getLogger(__name__)


QUEUE_POLL_INTERVAL_SEC = 0.3
EXTRACTION_COLLECTION = "case_extractions"
SYNTHESIS_COLLECTION = "case_synthesis"

# V1.8.2: Renditja e seksioneve për raportin e document review
DOCUMENT_REVIEW_SECTION_ORDER = [
    "document_summary",
    "article_verification",
    "supreme_court_precedents",
    "drafting_quality",
    "errors_corrections",
    "action_steps",
    "analiza_e_thelluar",
]


class CaseAnalysisOrchestrator:

    def __init__(self, db):
        self.db = db
        self.pipeline = get_extraction_pipeline(db)
        self.document_review = get_document_review_service(db)

    # ────────────────────────────────────────────────────────────────────
    # V1.7: LOAD CLIENT NAME
    # ────────────────────────────────────────────────────────────────────

    def _load_client_name(self, user_id: str) -> Optional[str]:
        """Lexon full_name/username te user-it (klientit te loguar)."""
        if not user_id:
            return None
        try:
            u_oid = ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id
            user = self.db.users.find_one(
                {"_id": u_oid},
                {"full_name": 1, "username": 1},
            )
            if not user:
                return None
            name = (user.get("full_name") or "").strip()
            if not name:
                name = (user.get("username") or "").strip()
            return name or None
        except Exception as e:
            logger.warning(f"⚠️ [ORCH V1.9] Could not load client_name: {e}")
            return None

    # ────────────────────────────────────────────────────────────────────
    # V1.8.1: NO HARDCODE — raw value
    # ────────────────────────────────────────────────────────────────────

    def _normalize_client_position(self, raw: Optional[str]) -> Optional[str]:
        """
        V1.8.1: Kthen raw value (case.client_position) pa interpretim.
        Nuk hardcode-ojmë mapping sepse rastet mund të kenë vlera të tjera.
        LLM-i do ta interpretojë vlerën raw në kontekstin e dokumentit.
        """
        if not raw:
            return None
        return str(raw).strip()

    # ────────────────────────────────────────────────────────────────────
    # V1.6: FINGERPRINT
    # ────────────────────────────────────────────────────────────────────

    def _compute_docs_fingerprint(self, case_id: str) -> str:
        """Hash i dokumenteve aktive (id + updated_at + status)."""
        try:
            case_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
            query = {
                "$or": [
                    {"case_id": case_id},
                    {"case_id": case_oid},
                    {"case_id": str(case_oid)},
                ],
                "status": {"$ne": "DELETED"},
            }
            cursor = self.db.documents.find(
                query,
                {"_id": 1, "updated_at": 1, "created_at": 1, "status": 1},
            ).sort([("_id", 1)])

            parts: List[str] = []
            for d in cursor:
                doc_id = str(d["_id"])
                ts = d.get("updated_at") or d.get("created_at")
                ts_str = ts.isoformat() if hasattr(ts, "isoformat") else str(ts or "")
                status = d.get("status", "")
                parts.append(f"{doc_id}:{ts_str}:{status}")

            raw = "|".join(parts)
            return hashlib.md5(raw.encode("utf-8")).hexdigest()
        except Exception as e:
            logger.warning(f"⚠️ [ORCH V1.9] fingerprint compute failed: {e}")
            return ""

    def _is_cache_valid(
        self,
        cached: Optional[Dict[str, Any]],
        current_fp: str,
        label: str = "cache",
    ) -> bool:
        if not cached:
            return False
        if not current_fp:
            return True
        stored_fp = (
            cached.get("docs_fingerprint")
            or cached.get("stats", {}).get("docs_fingerprint")
        )
        if not stored_fp:
            logger.info(f"🔄 [ORCH V1.9] {label} pa docs_fingerprint → invalidate")
            return False
        if stored_fp != current_fp:
            logger.info(
                f"🔄 [ORCH V1.9] {label} INVALIDATED — docs changed "
                f"(stored={stored_fp[:8]}... current={current_fp[:8]}...)"
            )
            return False
        return True

    # ────────────────────────────────────────────────────────────────────
    # V1.9: RUN — vetëm single-document mode
    # ────────────────────────────────────────────────────────────────────

    async def run(
        self,
        case_id: str,
        user_id: str,
        force_reprocess: bool = False,
        document_ids: Optional[List[str]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        start_time = time.time()
        loop = asyncio.get_event_loop()

        case = self._load_case(case_id)
        case_title = case.get("title") or case.get("case_name") or "Lënda"

        # V1.9: document_ids i detyrueshëm. Router V1.12 e bllokon me 400,
        # por mbrohemi edhe këtu për thirrje direkte.
        if not document_ids:
            logger.error(
                f"❌ [ORCH V1.9] run() called without document_ids: case={case_id}"
            )
            yield {
                "event": "start",
                "case_id": str(case_id),
                "case_title": case_title,
                "scope": "invalid",
                "force_reprocess": force_reprocess,
                "document_ids": None,
                "is_single_document": False,
                "docs_fingerprint": "",
            }
            yield {
                "event": "error",
                "phase": "start",
                "message": "document_ids required (orchestrator V1.9).",
            }
            yield self._final_error(start_time, "start", "document_ids required")
            return

        client_name = self._load_client_name(user_id)
        client_position = self._normalize_client_position(
            case.get("client_position")
        )

        if client_name:
            logger.info(
                f"👤 [ORCH V1.9] Client: name={client_name}, "
                f"case_position={client_position or '?'}"
            )
        else:
            logger.warning(f"⚠️ [ORCH V1.9] Client name unavailable (user_id={user_id})")

        current_fp = self._compute_docs_fingerprint(case_id)

        yield {
            "event": "start",
            "case_id": str(case_id),
            "case_title": case_title,
            "scope": "document",
            "force_reprocess": force_reprocess,
            "document_ids": document_ids,
            "is_single_document": True,
            "docs_fingerprint": current_fp[:8],
        }

        async for evt in self._run_single_document(
            case_id=case_id,
            user_id=user_id,
            client_name=client_name,
            client_position=client_position,
            document_ids=document_ids,
            force_reprocess=force_reprocess,
            case_title=case_title,
            start_time=start_time,
            loop=loop,
            current_fp=current_fp,
        ):
            yield evt

    # ────────────────────────────────────────────────────────────────────
    # SINGLE DOCUMENT RUN (Document Review)
    # ────────────────────────────────────────────────────────────────────

    async def _run_single_document(
        self,
        case_id: str,
        user_id: str,
        document_ids: List[str],
        force_reprocess: bool,
        case_title: str,
        start_time: float,
        loop,
        current_fp: str = "",
        client_name: Optional[str] = None,
        client_position: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        document_id = document_ids[0]

        # FAZA 1 — Ekstraktimi
        try:
            yield {"event": "phase_started", "phase": "extraction"}
            extraction_summary: Dict[str, Any] = {}

            async for evt in self.pipeline.run(
                user_id=user_id,
                case_id=str(case_id),
                document_ids=[document_id],
                force_reprocess=force_reprocess,
            ):
                evt_type = evt.get("event", "")
                if evt_type == "complete":
                    extraction_summary = evt.get("summary", {})
                    yield {
                        "event": "phase_completed",
                        "phase": "extraction",
                        "summary": extraction_summary,
                    }
                elif evt_type == "error":
                    yield {
                        "event": "error",
                        "phase": "extraction",
                        "message": evt.get("message", "Unknown error"),
                    }
                    yield self._final_error(start_time, "extraction", evt.get("message", "Unknown"))
                    return
                else:
                    yield {"phase": "extraction", **evt}

        except Exception as e:
            logger.exception(f"❌ [ORCH] Single-doc extraction failed: {e}")
            yield {"event": "error", "phase": "extraction", "message": str(e)}
            yield self._final_error(start_time, "extraction", str(e))
            return

        # FAZA 2 — Document Review
        review_stats: Dict[str, Any] = {}
        review_result_for_markdown: Optional[Dict[str, Any]] = None
        is_cache_hit = False

        existing_review = self._get_existing_document_review(case_id, document_id)
        doc_fp = self._compute_docs_fingerprint(case_id)
        review_valid = self._is_cache_valid(
            existing_review, doc_fp, label="document_review"
        )

        if existing_review and review_valid and not force_reprocess:
            is_cache_hit = True
            yield {
                "event": "phase_skipped",
                "phase": "document_review",
                "reason": "existing_document_review_valid",
            }
            review_stats = existing_review.get("stats", {})
            review_result_for_markdown = existing_review
        else:
            try:
                yield {"event": "phase_started", "phase": "document_review"}
                event_queue: asyncio.Queue = asyncio.Queue()

                def _sync_progress(event_type: str, data: Dict[str, Any]) -> None:
                    try:
                        evt = {"event": event_type, **data}
                        loop.call_soon_threadsafe(event_queue.put_nowait, evt)
                    except Exception as e:
                        logger.warning(f"⚠️ [ORCH] progress bridge failed: {e}")

                def _sync_stream(section_key: str, chunk: str) -> None:
                    try:
                        evt = {
                            "event": "section_chunk",
                            "section_key": section_key,
                            "chunk": chunk,
                        }
                        loop.call_soon_threadsafe(event_queue.put_nowait, evt)
                    except Exception as e:
                        logger.warning(f"⚠️ [ORCH] stream bridge failed: {e}")

                review_future = loop.run_in_executor(
                    None,
                    lambda: self.document_review.review(
                        case_id=str(case_id),
                        user_id=user_id,
                        client_name=client_name,
                        client_position=client_position,
                        document_id=document_id,
                        progress_callback=_sync_progress,
                        section_stream_callback=_sync_stream,
                    ),
                )

                while True:
                    done, _ = await asyncio.wait(
                        {review_future}, timeout=QUEUE_POLL_INTERVAL_SEC
                    )
                    while not event_queue.empty():
                        try:
                            evt = event_queue.get_nowait()
                            yield {"phase": "document_review", **evt}
                        except asyncio.QueueEmpty:
                            break
                    if review_future in done:
                        while not event_queue.empty():
                            try:
                                evt = event_queue.get_nowait()
                                yield {"phase": "document_review", **evt}
                            except asyncio.QueueEmpty:
                                break
                        break

                review_result = review_future.result()
                review_stats = review_result.get("stats", {})
                review_result_for_markdown = review_result

                try:
                    self.db[SYNTHESIS_COLLECTION].update_one(
                        {
                            "case_id": str(case_id),
                            "status": "completed",
                            "scope": "document",
                            "document_ids": [document_id],
                        },
                        {"$set": {"docs_fingerprint": doc_fp}},
                    )
                except Exception as fp_err:
                    logger.warning(f"⚠️ [ORCH V1.9] review fp save failed: {fp_err}")

                yield {
                    "event": "phase_completed",
                    "phase": "document_review",
                    "stats": review_stats,
                }

            except Exception as e:
                logger.exception(f"❌ [ORCH] Document review failed: {e}")
                yield {
                    "event": "error",
                    "phase": "document_review",
                    "message": str(e),
                }

        # FAZA 3 — Report Ready
        if is_cache_hit:
            report_markdown = self._build_markdown_from_document_review(
                review_result_for_markdown
            )
            if report_markdown.strip():
                yield {
                    "event": "report_ready",
                    "content": report_markdown,
                    "content_length": len(report_markdown),
                    "from_cache": True,
                    "scope": "document",
                }
        else:
            yield {"event": "report_ready", "from_cache": False, "scope": "document"}

        total_duration = round(time.time() - start_time, 2)
        final_summary = {
            "case_id": str(case_id),
            "case_title": case_title,
            "scope": "document",
            "duration_sec": total_duration,
            "from_cache": is_cache_hit,
            "is_single_document": True,
            "document_ids": document_ids,
            "extraction": extraction_summary,
            "document_review": review_stats,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(
            f"✅ [ORCH V1.9] Complete: case={case_id}, scope=document, "
            f"doc={document_id}, duration={total_duration}s, from_cache={is_cache_hit}"
        )
        yield {"event": "complete", "summary": final_summary}

    # ────────────────────────────────────────────────────────────────────
    # MARKDOWN BUILDER (vetëm document review)
    # ────────────────────────────────────────────────────────────────────

    def _build_markdown_from_document_review(
        self, review_result: Optional[Dict[str, Any]],
    ) -> str:
        if not review_result:
            return ""
        sections = review_result.get("sections") or {}
        if not sections:
            return ""

        parts: List[str] = []

        # V1.8.2: Rendit sipas DOCUMENT_REVIEW_SECTION_ORDER (7 seksione)
        for key in DOCUMENT_REVIEW_SECTION_ORDER:
            section = sections.get(key)
            if not section:
                continue
            title = section.get("title") or key
            content = section.get("content") or ""
            if not content.strip():
                continue
            parts.append(f"# {title}\n\n{content.strip()}\n\n---\n\n")

        # Seksione shtesë që nuk janë në order (nëse ka)
        for key, section in sections.items():
            if key in DOCUMENT_REVIEW_SECTION_ORDER:
                continue
            if not isinstance(section, dict):
                continue
            title = section.get("title") or key
            content = section.get("content") or ""
            if not content.strip():
                continue
            parts.append(f"# {title}\n\n{content.strip()}\n\n---\n\n")

        markdown = "".join(parts).rstrip()
        if markdown.endswith("---"):
            markdown = markdown[:-3].rstrip()
        return markdown

    # ────────────────────────────────────────────────────────────────────
    # LOADERS
    # ────────────────────────────────────────────────────────────────────

    def _load_case(self, case_id: str) -> Dict[str, Any]:
        try:
            c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
            return self.db.cases.find_one({"_id": c_oid}) or {}
        except Exception as e:
            logger.warning(f"⚠️ [ORCH] Could not load case: {e}")
            return {}

    def _get_existing_document_review(
        self, case_id: str, document_id: str
    ) -> Optional[Dict[str, Any]]:
        try:
            return self.db[SYNTHESIS_COLLECTION].find_one({
                "case_id": str(case_id),
                "status": "completed",
                "scope": "document",
                "document_ids": [document_id],
            })
        except Exception as e:
            logger.warning(f"⚠️ [ORCH] document review lookup failed: {e}")
            return None

    def _final_error(
        self, start_time: float, phase: str, message: str,
    ) -> Dict[str, Any]:
        return {
            "event": "complete",
            "summary": {
                "status": "failed",
                "failed_at_phase": phase,
                "error_message": message,
                "duration_sec": round(time.time() - start_time, 2),
                "completed_at": datetime.now(timezone.utc).isoformat(),
            },
        }


def get_case_analysis_orchestrator(db) -> CaseAnalysisOrchestrator:
    return CaseAnalysisOrchestrator(db)