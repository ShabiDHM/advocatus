# FILE: backend/app/services/extraction_pipeline.py
# PHOENIX PROTOCOL - EXTRACTION PIPELINE V1.5
# V1.5: HASH-SKIP GJITHMONË — existing_by_docid ngarkohet edhe me force_reprocess=True.
#       Nëse teksti nuk ka ndryshuar (hash match), skip për çdo dokument pavarësisht
#       force flag. Kjo kursen 283s të NER-it kur teksti është i paprekur.
#       Re-extraction ndodh vetëm nëse hash-i ndryshon (dokument u modifikua).
# V1.4: ORG-AWARE FETCH.
# V1.3: PARALLEL DOCUMENTS.

import asyncio
import hashlib
import logging
import os
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, AsyncGenerator, Tuple

from bson import ObjectId

from app.services.albanian_ner_service import ALBANIAN_NER_SERVICE
from app.services.albanian_metadata_extractor import albanian_metadata_extractor
from app.services.categorization_service import CATEGORIZATION_SERVICE

logger = logging.getLogger(__name__)


EXTRACTION_COLLECTION = "case_extractions"
DOCUMENT_TIMEOUT_SEC = 600

MAX_CONCURRENT_DOCS = int(os.environ.get("EXTRACT_MAX_CONCURRENT_DOCS", "3"))


def _compute_text_hash(text: str) -> str:
    if not text:
        return ""
    return hashlib.md5(text.encode("utf-8")).hexdigest()


class ExtractionPipeline:

    def __init__(self, db: Any):
        self.db = db
        self.ner = ALBANIAN_NER_SERVICE
        self.meta = albanian_metadata_extractor
        self.categorizer = CATEGORIZATION_SERVICE

    async def run(
        self,
        user_id: str,
        case_id: str,
        document_ids: Optional[List[str]] = None,
        force_reprocess: bool = False,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Async generator që yield events progresi (V1.5: hash-skip gjithmonë)."""
        start_time = time.time()

        try:
            documents = self._fetch_documents(user_id, case_id, document_ids)
        except Exception as e:
            logger.error(f"❌ [EXTRACT] Fetch failed: {e}")
            yield {"event": "error", "message": f"Fetch failed: {e}"}
            return

        total = len(documents)
        if total == 0:
            yield {"event": "error", "message": "No documents found for this case."}
            return

        yield {
            "event": "start",
            "case_id": str(case_id),
            "total_documents": total,
            "max_concurrent_docs": MAX_CONCURRENT_DOCS,
        }

        # V1.5: GJITHMONË ngarko existing_by_docid (edhe me force_reprocess=True)
        # Hash-based skip bëhet brenda _process_one_document
        existing_by_docid: Dict[str, Dict[str, Any]] = self._fetch_existing_extractions(
            case_id, [str(d["_id"]) for d in documents]
        )
        logger.info(
            f"📚 [EXTRACT V1.5] Ngarkuar {len(existing_by_docid)} ekstraktime ekzistuese "
            f"(force_reprocess={force_reprocess})"
        )

        event_queue: asyncio.Queue = asyncio.Queue()
        sem = asyncio.Semaphore(MAX_CONCURRENT_DOCS)

        async def _worker(doc: Dict[str, Any], idx: int) -> Dict[str, Any]:
            async with sem:
                return await self._process_one_document(
                    doc=doc,
                    idx=idx,
                    total=total,
                    case_id=str(case_id),
                    user_id=user_id,
                    existing_by_docid=existing_by_docid,
                    event_queue=event_queue,
                    force_reprocess=force_reprocess,  # V1.5: kalo më poshtë
                )

        tasks = [
            asyncio.create_task(_worker(d, i))
            for i, d in enumerate(documents)
        ]

        logger.info(
            f"🚀 [EXTRACT V1.5] Nisur {total} dokumente me "
            f"max_concurrent={MAX_CONCURRENT_DOCS} (user={user_id}, "
            f"force={force_reprocess})"
        )

        pending = set(tasks)
        try:
            while pending:
                done, pending = await asyncio.wait(pending, timeout=0.3)
                while not event_queue.empty():
                    try:
                        yield event_queue.get_nowait()
                    except asyncio.QueueEmpty:
                        break
        finally:
            for t in tasks:
                if not t.done():
                    t.cancel()

        while not event_queue.empty():
            try:
                yield event_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

        total_entities = 0
        total_metadata_fields = 0
        total_role_conflicts = 0
        successful = 0
        failed = 0
        skipped = 0
        per_doc_stats: List[Dict[str, Any]] = []

        for t in tasks:
            try:
                res = t.result()
            except (asyncio.CancelledError, Exception) as e:
                logger.error(f"❌ [EXTRACT V1.5] Worker task error: {e}")
                failed += 1
                continue

            status = res.get("status")
            if status == "success":
                successful += 1
                r = res["result"]
                total_entities += r["stats"]["total_entities"]
                total_metadata_fields += r["stats"]["metadata_fields_found"]
                total_role_conflicts += r["stats"].get("role_conflicts_resolved", 0)
                per_doc_stats.append(r["stats"])
            elif status == "skipped":
                skipped += 1
            else:
                failed += 1

        duration = round(time.time() - start_time, 2)

        summary = {
            "case_id": str(case_id),
            "documents_total": total,
            "documents_successful": successful,
            "documents_failed": failed,
            "documents_skipped": skipped,
            "total_entities": total_entities,
            "total_metadata_fields": total_metadata_fields,
            "total_role_conflicts_resolved": total_role_conflicts,
            "duration_sec": duration,
            "max_concurrent_docs": MAX_CONCURRENT_DOCS,
        }

        logger.info(f"✅ [EXTRACT V1.5] Pipeline complete: {summary}")
        yield {"event": "complete", "summary": summary}

    def _fetch_documents(
        self,
        user_id: str,
        case_id: str,
        document_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        V1.4: NUK filtrohet me owner_id — aksesi verifikohet nga router.
        """
        case_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id

        filter_q: Dict[str, Any] = {
            "$or": [
                {"case_id": case_id},
                {"case_id": case_oid},
                {"case_id": str(case_oid)},
            ],
            "status": {"$ne": "DELETED"},
        }

        if document_ids:
            doc_oids = [ObjectId(d) for d in document_ids if ObjectId.is_valid(d)]
            doc_strs = [str(d) for d in document_ids]
            filter_q["_id"] = {"$in": doc_oids + doc_strs}

        cursor = self.db.documents.find(filter_q).sort(
            [("created_at", 1), ("_id", 1)]
        )
        return list(cursor)

    def _fetch_existing_extractions(
        self,
        case_id: str,
        document_ids: List[str],
    ) -> Dict[str, Any]:
        try:
            cursor = self.db[EXTRACTION_COLLECTION].find({
                "case_id": str(case_id),
                "document_id": {"$in": document_ids},
                "status": "completed",
            })
            return {doc["document_id"]: doc for doc in cursor}
        except Exception as e:
            logger.warning(f"⚠️ [EXTRACT] Could not fetch existing: {e}")
            return {}

    async def _process_one_document(
        self,
        doc: Dict[str, Any],
        idx: int,
        total: int,
        case_id: str,
        user_id: str,
        existing_by_docid: Dict[str, Dict[str, Any]],
        event_queue: asyncio.Queue,
        force_reprocess: bool = False,
    ) -> Dict[str, Any]:
        """
        V1.5: Cache check GJITHMONË (pavarësisht force_reprocess).
        Skip vetëm nëse hash-i përputhet — re-extract vetëm nëse teksti ndryshoi.
        """
        doc_id = str(doc["_id"])
        file_name = doc.get("file_name", f"doc_{idx}")

        current_text = (
            doc.get("content")
            or doc.get("extracted_text")
            or doc.get("text")
            or ""
        )
        current_hash = _compute_text_hash(current_text)

        if doc_id in existing_by_docid:
            cached = existing_by_docid[doc_id]
            cached_hash = cached.get("text_hash", "")

            # V1.5: Skip VETËM nëse hash-i përputhet — edhe me force_reprocess=True
            if cached_hash and cached_hash == current_hash:
                logger.info(
                    f"⚡ [EXTRACT V1.5] Doc {doc_id}: hash match → SKIP "
                    f"(force_reprocess={force_reprocess} injorohet per tekst te paprekur)"
                )
                await event_queue.put({
                    "event": "document_skipped",
                    "document_id": doc_id,
                    "file_name": file_name,
                    "index": idx,
                    "reason": "text_hash_unchanged",
                })
                return {"status": "skipped"}

            # Hash ndryshoi ose bosh → re-extract
            if cached_hash and cached_hash != current_hash:
                logger.info(
                    f"🔄 [EXTRACT V1.5] Doc {doc_id}: text CHANGED "
                    f"(hash {cached_hash[:8]}... → {current_hash[:8]}...) → re-extracting"
                )

        await event_queue.put({
            "event": "document_started",
            "document_id": doc_id,
            "file_name": file_name,
            "index": idx,
            "total_documents": total,
        })

        try:
            result = await asyncio.wait_for(
                self._process_document(doc, case_id, user_id),
                timeout=DOCUMENT_TIMEOUT_SEC,
            )

            self._persist_extraction(result)

            await event_queue.put({
                "event": "document_completed",
                "document_id": doc_id,
                "file_name": file_name,
                "stats": result["stats"],
            })
            return {"status": "success", "result": result}

        except asyncio.TimeoutError:
            logger.warning(
                f"⚠️ [EXTRACT V1.5] Document {doc_id} timed out after "
                f"{DOCUMENT_TIMEOUT_SEC}s"
            )
            await event_queue.put({
                "event": "document_failed",
                "document_id": doc_id,
                "file_name": file_name,
                "error": f"Timeout after {DOCUMENT_TIMEOUT_SEC}s",
            })
            return {"status": "failed", "error": "timeout"}

        except Exception as e:
            logger.exception(f"❌ [EXTRACT V1.5] Document {doc_id} failed")
            await event_queue.put({
                "event": "document_failed",
                "document_id": doc_id,
                "file_name": file_name,
                "error": str(e),
            })
            return {"status": "failed", "error": str(e)}

    async def _process_document(
        self,
        doc: Dict[str, Any],
        case_id: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """V1.2: Kategorizim → NER + Metadata PARALEL."""
        doc_id = str(doc["_id"])
        file_name = doc.get("file_name", "Document")
        text = (
            doc.get("content")
            or doc.get("extracted_text")
            or doc.get("text")
            or ""
        )

        doc_start = time.time()
        text_hash = _compute_text_hash(text)

        if not text.strip():
            return {
                "document_id": doc_id,
                "case_id": str(case_id),
                "user_id": str(user_id),
                "file_name": file_name,
                "text_length": 0,
                "text_hash": text_hash,
                "document_type": None,
                "document_type_details": None,
                "entities_by_type": {},
                "entities_flat": [],
                "metadata": {},
                "ner_stats": {},
                "metadata_stats": {},
                "ner_warnings": ["Empty text"],
                "metadata_warnings": ["Empty text"],
                "stats": {
                    "text_length": 0,
                    "total_entities": 0,
                    "metadata_fields_found": 0,
                    "role_conflicts_resolved": 0,
                    "duration_sec": 0.0,
                    "warning": "Empty document text",
                },
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }

        loop = asyncio.get_event_loop()

        categorization = await loop.run_in_executor(
            None,
            lambda: self.categorizer.categorize_document_detailed(text),
        )
        document_type = categorization.get("primary_category")
        logger.info(
            f"📋 [EXTRACT V1.5] doc={doc_id}: categorized as "
            f"'{document_type}' (conf={categorization.get('confidence')})"
        )

        t_parallel = time.time()

        ner_task = loop.run_in_executor(
            None,
            lambda: self.ner.extract_legal_entities(
                text=text,
                document_id=doc_id,
                document_type=document_type,
            ),
        )

        meta_task = loop.run_in_executor(
            None,
            lambda: self.meta.extract(
                text=text,
                document_id=doc_id,
            ),
        )

        ner_result, meta_result = await asyncio.gather(ner_task, meta_task)

        parallel_duration = round(time.time() - t_parallel, 2)
        logger.info(
            f"⚡ [EXTRACT V1.5] doc={doc_id}: NER + Metadata paralel përfunduan "
            f"në {parallel_duration}s"
        )

        metadata_fields_found = 0
        metadata_clean: Dict[str, Any] = {}
        internal_meta_keys = {
            "document_id", "extraction_timestamp",
            "stats", "warnings", "confidence",
        }
        for k, v in meta_result.items():
            if k in internal_meta_keys:
                continue
            metadata_clean[k] = v
            if v not in (None, "", [], {}):
                metadata_fields_found += 1

        duration = round(time.time() - doc_start, 2)

        return {
            "document_id": doc_id,
            "case_id": str(case_id),
            "user_id": str(user_id),
            "file_name": file_name,
            "text_length": len(text),
            "text_hash": text_hash,
            "document_type": document_type,
            "document_type_details": categorization,
            "entities_by_type": ner_result.get("entities_by_type", {}),
            "entities_flat": ner_result.get("entities_flat", []),
            "metadata": metadata_clean,
            "ner_stats": ner_result.get("stats", {}),
            "metadata_stats": meta_result.get("stats", {}),
            "ner_warnings": ner_result.get("warnings", []),
            "metadata_warnings": meta_result.get("warnings", []),
            "stats": {
                "text_length": len(text),
                "total_entities": ner_result.get("stats", {}).get("total_entities", 0),
                "metadata_fields_found": metadata_fields_found,
                "role_conflicts_resolved": ner_result.get("stats", {}).get(
                    "role_conflicts_resolved", 0
                ),
                "duration_sec": duration,
                "parallel_duration_sec": parallel_duration,
            },
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

    def _persist_extraction(self, result: Dict[str, Any]) -> None:
        try:
            self.db[EXTRACTION_COLLECTION].update_one(
                {
                    "case_id": result["case_id"],
                    "document_id": result["document_id"],
                },
                {"$set": result},
                upsert=True,
            )
        except Exception as e:
            logger.error(
                f"❌ [EXTRACT] Persist failed for {result['document_id']}: {e}"
            )
            raise

    def load_extractions(
        self,
        case_id: str,
        only_completed: bool = True,
    ) -> List[Dict[str, Any]]:
        filter_q: Dict[str, Any] = {"case_id": str(case_id)}
        if only_completed:
            filter_q["status"] = "completed"

        try:
            cursor = self.db[EXTRACTION_COLLECTION].find(filter_q).sort(
                [("completed_at", 1)]
            )
            return list(cursor)
        except Exception as e:
            logger.error(f"❌ [EXTRACT] load_extractions failed: {e}")
            return []

    def get_extraction_stats(self, case_id: str) -> Dict[str, Any]:
        try:
            pipeline = [
                {"$match": {"case_id": str(case_id)}},
                {
                    "$group": {
                        "_id": None,
                        "documents_total": {"$sum": 1},
                        "documents_completed": {
                            "$sum": {"$cond": [{"$eq": ["$status", "completed"]}, 1, 0]}
                        },
                        "total_entities": {"$sum": "$stats.total_entities"},
                        "total_metadata_fields": {
                            "$sum": "$stats.metadata_fields_found"
                        },
                        "total_role_conflicts_resolved": {
                            "$sum": "$stats.role_conflicts_resolved"
                        },
                        "total_duration_sec": {"$sum": "$stats.duration_sec"},
                    }
                },
            ]
            result = list(self.db[EXTRACTION_COLLECTION].aggregate(pipeline))
            return result[0] if result else {}
        except Exception as e:
            logger.error(f"❌ [EXTRACT] get_extraction_stats failed: {e}")
            return {}


def get_extraction_pipeline(db: Any) -> ExtractionPipeline:
    return ExtractionPipeline(db)