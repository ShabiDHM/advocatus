# FILE: backend/app/services/case_analysis_orchestrator.py
# PHOENIX PROTOCOL - CASE ANALYSIS ORCHESTRATOR V1.7
# V1.7: CLIENT CONTEXT — fetch user's full_name nga DB, kalo te document_review.review()
#       per klasifikim te saktë te "Pozicioni i klientit".
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
from app.services.pillars.cross_reference_service import get_cross_reference_service
from app.services.synthesis_service import get_synthesis_service
from app.services.document_review_service import get_document_review_service

logger = logging.getLogger(__name__)


QUEUE_POLL_INTERVAL_SEC = 0.3
EXTRACTION_COLLECTION = "case_extractions"
CROSS_REF_COLLECTION = "case_cross_references"
SYNTHESIS_COLLECTION = "case_synthesis"

SECTION_ORDER = [
    "executive_summary",
    "chronology",
    "parties_and_roles",
    "legal_framework",
    "key_findings_contradictions",
    "recommendations",
]

DOCUMENT_REVIEW_SECTION_ORDER = [
    "document_summary",
    "article_verification",
    "supreme_court_precedents",
    "drafting_quality",
    "errors_corrections",
    "action_steps",
]


class CaseAnalysisOrchestrator:

    def __init__(self, db):
        self.db = db
        self.pipeline = get_extraction_pipeline(db)
        self.xref_service = get_cross_reference_service(db)
        self.synthesis = get_synthesis_service(db)
        self.document_review = get_document_review_service(db)

    # ────────────────────────────────────────────────────────────────────
    # V1.7: LOAD CLIENT NAME
    # ────────────────────────────────────────────────────────────────────

    def _load_client_name(self, user_id: str) -> Optional[str]:
        """
        V1.7: Lexon full_name/username te user-it (klientit te loguar)
        per ta kaluar te document_review si kontekst.
        """
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
            logger.warning(f"⚠️ [ORCH V1.7] Could not load client_name: {e}")
            return None

    # ────────────────────────────────────────────────────────────────────
    # V1.6: FINGERPRINT — cache invalidation
    # ────────────────────────────────────────────────────────────────────

    def _compute_docs_fingerprint(self, case_id: str) -> str:
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
            logger.warning(f"⚠️ [ORCH V1.7] fingerprint compute failed: {e}")
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
            logger.info(
                f"🔄 [ORCH V1.7] {label} pa docs_fingerprint → invalidate "
                f"(refresh i sigurt)"
            )
            return False

        if stored_fp != current_fp:
            logger.info(
                f"🔄 [ORCH V1.7] {label} INVALIDATED — docs changed "
                f"(stored={stored_fp[:8]}... current={current_fp[:8]}...)"
            )
            return False

        return True

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
        is_single_doc = bool(document_ids and len(document_ids) >= 1)

        if is_single_doc:
            scope = "document"
        else:
            scope = "case"

        # V1.7: Fetch client_name once per run
        client_name = self._load_client_name(user_id)
        if client_name:
            logger.info(f"👤 [ORCH V1.7] Client name: {client_name}")
        else:
            logger.warning(f"⚠️ [ORCH V1.7] Client name not available for user_id={user_id}")

        current_fp = self._compute_docs_fingerprint(case_id)

        yield {
            "event": "start",
            "case_id": str(case_id),
            "case_title": case_title,
            "scope": scope,
            "force_reprocess": force_reprocess,
            "document_ids": document_ids,
            "is_single_document": is_single_doc,
            "docs_fingerprint": current_fp[:8],
        }

        # ═══════════════════════════════════════════════════════════════
        # SINGLE-DOCUMENT MODE → Document Review
        # ═══════════════════════════════════════════════════════════════
        if is_single_doc:
            async for evt in self._run_single_document(
                case_id=case_id,
                user_id=user_id,
                client_name=client_name,   # V1.7
                document_ids=document_ids,
                force_reprocess=force_reprocess,
                case_title=case_title,
                start_time=start_time,
                loop=loop,
                current_fp=current_fp,
            ):
                yield evt
            return

        # ═══════════════════════════════════════════════════════════════
        # CASE MODE → Case Synthesis
        # ═══════════════════════════════════════════════════════════════

        # ═══ PHASE 1 — EXTRACTION ═══
        try:
            yield {"event": "phase_started", "phase": "extraction"}

            extraction_summary: Dict[str, Any] = {}

            async for evt in self.pipeline.run(
                user_id=user_id,
                case_id=str(case_id),
                document_ids=None,
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
                    yield self._final_error(
                        start_time, "extraction", evt.get("message", "Unknown")
                    )
                    return
                else:
                    yield {"phase": "extraction", **evt}

        except Exception as e:
            logger.exception(f"❌ [ORCH] Extraction phase failed: {e}")
            yield {"event": "error", "phase": "extraction", "message": str(e)}
            yield self._final_error(start_time, "extraction", str(e))
            return

        # ═══ PHASE 2 — CROSS-REFERENCE ═══
        xref_stats: Dict[str, Any] = {}
        existing_xref = self._get_existing_xref(case_id)
        xref_valid = self._is_cache_valid(existing_xref, current_fp, label="xref")

        if existing_xref and xref_valid and not force_reprocess:
            yield {
                "event": "phase_skipped",
                "phase": "cross_reference",
                "reason": "existing_cross_reference_valid",
            }
            xref_stats = existing_xref.get("stats", {})
        else:
            try:
                yield {"event": "phase_started", "phase": "cross_reference"}
                xref_result = await loop.run_in_executor(
                    None,
                    lambda: self.xref_service.build(str(case_id)),
                )
                xref_stats = xref_result.get("stats", {})

                try:
                    self.db[CROSS_REF_COLLECTION].update_one(
                        {"case_id": str(case_id), "status": "completed"},
                        {"$set": {"docs_fingerprint": current_fp}},
                    )
                except Exception as fp_err:
                    logger.warning(f"⚠️ [ORCH V1.7] xref fingerprint save failed: {fp_err}")

                yield {
                    "event": "phase_completed",
                    "phase": "cross_reference",
                    "stats": xref_stats,
                }
            except Exception as e:
                logger.exception(f"❌ [ORCH] Cross-reference phase failed: {e}")
                yield {"event": "error", "phase": "cross_reference", "message": str(e)}

        # ═══ PHASE 3 — SYNTHESIS (case-only) ═══
        synthesis_stats: Dict[str, Any] = {}
        synthesis_result_for_markdown: Optional[Dict[str, Any]] = None
        is_cache_hit = False

        existing_synth = self._get_existing_case_synthesis(case_id)
        synth_valid = self._is_cache_valid(existing_synth, current_fp, label="synthesis")

        if existing_synth and synth_valid and not force_reprocess:
            is_cache_hit = True
            yield {
                "event": "phase_skipped",
                "phase": "synthesis",
                "reason": "existing_synthesis_valid",
            }
            synthesis_stats = existing_synth.get("stats", {})
            synthesis_result_for_markdown = existing_synth
        else:
            if existing_synth and not synth_valid:
                logger.info(
                    f"🔄 [ORCH V1.7] Re-generating case synthesis (cache invalidated)"
                )

            try:
                yield {"event": "phase_started", "phase": "synthesis"}

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

                synth_future = loop.run_in_executor(
                    None,
                    lambda: self.synthesis.synthesize(
                        case_id=str(case_id),
                        user_id=user_id,
                        progress_callback=_sync_progress,
                        section_stream_callback=_sync_stream,
                    ),
                )

                while True:
                    done, _ = await asyncio.wait(
                        {synth_future}, timeout=QUEUE_POLL_INTERVAL_SEC
                    )
                    while not event_queue.empty():
                        try:
                            evt = event_queue.get_nowait()
                            yield {"phase": "synthesis", **evt}
                        except asyncio.QueueEmpty:
                            break

                    if synth_future in done:
                        while not event_queue.empty():
                            try:
                                evt = event_queue.get_nowait()
                                yield {"phase": "synthesis", **evt}
                            except asyncio.QueueEmpty:
                                break
                        break

                synthesis_result = synth_future.result()
                synthesis_stats = synthesis_result.get("stats", {})
                synthesis_result_for_markdown = synthesis_result

                try:
                    self.db[SYNTHESIS_COLLECTION].update_one(
                        {
                            "case_id": str(case_id),
                            "status": "completed",
                            "scope": "case",
                        },
                        {"$set": {"docs_fingerprint": current_fp}},
                    )
                    logger.info(
                        f"💾 [ORCH V1.7] Saved docs_fingerprint={current_fp[:8]}... "
                        f"to synthesis cache"
                    )
                except Exception as fp_err:
                    logger.warning(f"⚠️ [ORCH V1.7] synthesis fingerprint save failed: {fp_err}")

                yield {
                    "event": "phase_completed",
                    "phase": "synthesis",
                    "stats": synthesis_stats,
                }

            except Exception as e:
                logger.exception(f"❌ [ORCH] Synthesis phase failed: {e}")
                yield {"event": "error", "phase": "synthesis", "message": str(e)}

        # ═══ PHASE 4 — REPORT READY ═══
        if is_cache_hit:
            report_markdown = self._build_markdown_from_case_synthesis(
                synthesis_result_for_markdown
            )
            if report_markdown.strip():
                yield {
                    "event": "report_ready",
                    "content": report_markdown,
                    "content_length": len(report_markdown),
                    "from_cache": True,
                    "scope": "case",
                }
        else:
            yield {
                "event": "report_ready",
                "from_cache": False,
                "scope": "case",
            }

        # ═══ COMPLETE ═══
        total_duration = round(time.time() - start_time, 2)

        final_summary = {
            "case_id": str(case_id),
            "case_title": case_title,
            "scope": "case",
            "duration_sec": total_duration,
            "from_cache": is_cache_hit,
            "is_single_document": False,
            "document_ids": None,
            "docs_fingerprint": current_fp[:8],
            "extraction": extraction_summary,
            "cross_reference": xref_stats,
            "synthesis": synthesis_stats,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(
            f"✅ [ORCH V1.7] Complete: case={case_id}, scope=case, "
            f"duration={total_duration}s, from_cache={is_cache_hit}, "
            f"fp={current_fp[:8]}..."
        )

        yield {"event": "complete", "summary": final_summary}

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
        client_name: Optional[str] = None,   # V1.7
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Rruga për review të një dokumenti të vetëm.
        """
        document_id = document_ids[0]

        # ═══ FAZA 1 — Ekstraktimi i dokumentit ═══
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
                    yield self._final_error(
                        start_time, "extraction", evt.get("message", "Unknown")
                    )
                    return
                else:
                    yield {"phase": "extraction", **evt}

        except Exception as e:
            logger.exception(f"❌ [ORCH] Single-doc extraction failed: {e}")
            yield {"event": "error", "phase": "extraction", "message": str(e)}
            yield self._final_error(start_time, "extraction", str(e))
            return

        # ═══ FAZA 2 — Document Review ═══
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

                # V1.7: Kalo client_name te review
                review_future = loop.run_in_executor(
                    None,
                    lambda: self.document_review.review(
                        case_id=str(case_id),
                        user_id=user_id,
                        client_name=client_name,   # V1.7
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
                    logger.warning(f"⚠️ [ORCH V1.7] review fingerprint save failed: {fp_err}")

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

        # ═══ FAZA 3 — Report Ready ═══
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
            yield {
                "event": "report_ready",
                "from_cache": False,
                "scope": "document",
            }

        # ═══ COMPLETE ═══
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
            f"✅ [ORCH V1.7] Complete: case={case_id}, scope=document, "
            f"doc={document_id}, duration={total_duration}s, "
            f"from_cache={is_cache_hit}"
        )

        yield {"event": "complete", "summary": final_summary}

    # ────────────────────────────────────────────────────────────────────
    # MARKDOWN BUILDERS (të paprekura)
    # ────────────────────────────────────────────────────────────────────

    def _build_markdown_from_case_synthesis(
        self,
        synthesis_result: Optional[Dict[str, Any]],
    ) -> str:
        if not synthesis_result:
            return ""

        sections = synthesis_result.get("sections") or {}
        if not sections:
            return ""

        parts: List[str] = []
        for key in SECTION_ORDER:
            section = sections.get(key)
            if not section:
                continue
            title = section.get("title") or key
            content = section.get("content") or ""
            if not content.strip():
                continue
            parts.append(f"# {title}\n\n{content.strip()}\n\n---\n\n")

        for key, section in sections.items():
            if key in SECTION_ORDER:
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

    def _build_markdown_from_document_review(
        self,
        review_result: Optional[Dict[str, Any]],
    ) -> str:
        if not review_result:
            return ""

        sections = review_result.get("sections") or {}
        if not sections:
            return ""

        parts: List[str] = []
        for key in DOCUMENT_REVIEW_SECTION_ORDER:
            section = sections.get(key)
            if not section:
                continue
            title = section.get("title") or key
            content = section.get("content") or ""
            if not content.strip():
                continue
            parts.append(f"# {title}\n\n{content.strip()}\n\n---\n\n")

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
    # LOADERS (të paprekura)
    # ────────────────────────────────────────────────────────────────────

    def _load_case(self, case_id: str) -> Dict[str, Any]:
        try:
            c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
            return self.db.cases.find_one({"_id": c_oid}) or {}
        except Exception as e:
            logger.warning(f"⚠️ [ORCH] Could not load case: {e}")
            return {}

    def _get_existing_xref(self, case_id: str) -> Optional[Dict[str, Any]]:
        try:
            return self.db[CROSS_REF_COLLECTION].find_one(
                {"case_id": str(case_id), "status": "completed"}
            )
        except Exception as e:
            logger.warning(f"⚠️ [ORCH] xref lookup failed: {e}")
            return None

    def _get_existing_case_synthesis(self, case_id: str) -> Optional[Dict[str, Any]]:
        try:
            return self.db[SYNTHESIS_COLLECTION].find_one({
                "case_id": str(case_id),
                "status": "completed",
                "scope": "case",
            })
        except Exception as e:
            logger.warning(f"⚠️ [ORCH] case synthesis lookup failed: {e}")
            return None

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
        self,
        start_time: float,
        phase: str,
        message: str,
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


# ────────────────────────────────────────────────────────────────────────────
# FACTORY
# ────────────────────────────────────────────────────────────────────────────

def get_case_analysis_orchestrator(db) -> CaseAnalysisOrchestrator:
    return CaseAnalysisOrchestrator(db)