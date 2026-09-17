# FILE: backend/app/services/case_analysis_orchestrator.py
# PHOENIX PROTOCOL - CASE ANALYSIS ORCHESTRATOR V1.3
# FIX: document_ids param — scope analysis to specific documents.

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, AsyncGenerator

from bson import ObjectId

from app.services.extraction_pipeline import get_extraction_pipeline
from app.services.pillars.cross_reference_service import get_cross_reference_service
from app.services.synthesis_service import get_synthesis_service

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


class CaseAnalysisOrchestrator:
    """
    V1.3 — document_ids support.
    """

    def __init__(self, db):
        self.db = db
        self.pipeline = get_extraction_pipeline(db)
        self.xref_service = get_cross_reference_service(db)
        self.synthesis = get_synthesis_service(db)

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

        yield {
            "event": "start",
            "case_id": str(case_id),
            "case_title": case_title,
            "force_reprocess": force_reprocess,
            "document_ids": document_ids,
            "is_single_document": is_single_doc,
        }

        # ═══ PHASE 1 — EXTRACTION ═══
        try:
            yield {"event": "phase_started", "phase": "extraction"}

            extraction_summary: Dict[str, Any] = {}

            async for evt in self.pipeline.run(
                user_id=user_id,
                case_id=str(case_id),
                document_ids=document_ids,
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

        if is_single_doc:
            # Single document → no cross-references possible
            yield {
                "event": "phase_skipped",
                "phase": "cross_reference",
                "reason": "single_document_mode",
            }
            xref_stats = {
                "skipped": True,
                "reason": "single_document_mode",
            }
        else:
            existing_xref = self._get_existing_xref(case_id)

            if existing_xref and not force_reprocess:
                yield {
                    "event": "phase_skipped",
                    "phase": "cross_reference",
                    "reason": "existing_cross_reference",
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
                    yield {
                        "event": "phase_completed",
                        "phase": "cross_reference",
                        "stats": xref_stats,
                    }
                except Exception as e:
                    logger.exception(f"❌ [ORCH] Cross-reference phase failed: {e}")
                    yield {"event": "error", "phase": "cross_reference", "message": str(e)}

        # ═══ PHASE 3 — SYNTHESIS ═══
        synthesis_stats: Dict[str, Any] = {}
        synthesis_result_for_markdown: Optional[Dict[str, Any]] = None
        is_cache_hit = False

        existing_synth = None
        if not is_single_doc:
            existing_synth = self._get_existing_synthesis(case_id)
        elif not force_reprocess:
            existing_synth = self._get_existing_synthesis_for_single_doc(
                case_id, document_ids[0]
            )

        if existing_synth and not force_reprocess:
            is_cache_hit = True
            yield {
                "event": "phase_skipped",
                "phase": "synthesis",
                "reason": "existing_synthesis",
            }
            synthesis_stats = existing_synth.get("stats", {})
            synthesis_result_for_markdown = existing_synth
        else:
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
                        document_ids=document_ids,
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
            report_markdown = self._build_markdown_from_synthesis(
                synthesis_result_for_markdown
            )
            if report_markdown.strip():
                yield {
                    "event": "report_ready",
                    "content": report_markdown,
                    "content_length": len(report_markdown),
                    "from_cache": True,
                }
        else:
            yield {
                "event": "report_ready",
                "from_cache": False,
            }

        # ═══ COMPLETE ═══
        total_duration = round(time.time() - start_time, 2)

        final_summary = {
            "case_id": str(case_id),
            "case_title": case_title,
            "duration_sec": total_duration,
            "from_cache": is_cache_hit,
            "is_single_document": is_single_doc,
            "document_ids": document_ids,
            "extraction": extraction_summary,
            "cross_reference": xref_stats,
            "synthesis": synthesis_stats,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(
            f"✅ [ORCH] Complete: case={case_id}, "
            f"single_doc={is_single_doc}, duration={total_duration}s, "
            f"from_cache={is_cache_hit}"
        )

        yield {"event": "complete", "summary": final_summary}

    # ────────────────────────────────────────────────────────────────────
    # INTERNAL HELPERS
    # ────────────────────────────────────────────────────────────────────

    def _build_markdown_from_synthesis(
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

    def _get_existing_synthesis(self, case_id: str) -> Optional[Dict[str, Any]]:
        try:
            return self.db[SYNTHESIS_COLLECTION].find_one(
                {"case_id": str(case_id), "status": "completed", "scope": "case"}
            )
        except Exception as e:
            logger.warning(f"⚠️ [ORCH] synthesis lookup failed: {e}")
            return None

    def _get_existing_synthesis_for_single_doc(
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
            logger.warning(f"⚠️ [ORCH] single-doc synthesis lookup failed: {e}")
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

def get_case_analysis_orchestrator(db: Any) -> CaseAnalysisOrchestrator:
    return CaseAnalysisOrchestrator(db)