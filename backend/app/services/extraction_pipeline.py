# FILE: backend/app/services/extraction_pipeline.py
# PHOENIX PROTOCOL - EXTRACTION PIPELINE V1.1
# Integron CATEGORIZATION → kalon document_type hint në NER (V33.2).
# Orkestron NER + Metadata + Persistencë për një fashikull të plotë.
# Zero silent truncation. Idempotent. Progress SSE.

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, AsyncGenerator, Tuple

from bson import ObjectId

from app.services.albanian_ner_service import ALBANIAN_NER_SERVICE
from app.services.albanian_metadata_extractor import albanian_metadata_extractor
from app.services.categorization_service import CATEGORIZATION_SERVICE

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────────────
# CONFIG
# ────────────────────────────────────────────────────────────────────────────

EXTRACTION_COLLECTION = "case_extractions"
DOCUMENT_TIMEOUT_SEC = 600
MAX_CONCURRENT_DOCS = 1


# ────────────────────────────────────────────────────────────────────────────
# PIPELINE
# ────────────────────────────────────────────────────────────────────────────

class ExtractionPipeline:
    """
    Tubi i ekstraktimit për një fashikull të plotë.

    Rrjedha:
    1. Tërheq dokumentet nga MongoDB.
    2. Për çdo dokument:
       a. Kategorizo (CATEGORIZATION_SERVICE) → document_type
       b. NER (chunk-aware, me document_type hint) → entities
       c. Metadata (chunk-aware) → fushat strukturore
    3. Bashkon rezultatet.
    4. Persiston në `case_extractions` (idempotent — upsert).
    5. Raporton progres përmes async generator.
    """

    def __init__(self, db: Any):
        self.db = db
        self.ner = ALBANIAN_NER_SERVICE
        self.meta = albanian_metadata_extractor
        self.categorizer = CATEGORIZATION_SERVICE

    # ────────────────────────────────────────────────────────────────────
    # PUBLIC — run (async generator, SSE-friendly)
    # ────────────────────────────────────────────────────────────────────

    async def run(
        self,
        user_id: str,
        case_id: str,
        document_ids: Optional[List[str]] = None,
        force_reprocess: bool = False,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Async generator që yield events progresi.

        Events:
        - {"event": "start", "case_id", "total_documents"}
        - {"event": "document_started", "document_id", "file_name", "index", "total_documents"}
        - {"event": "document_skipped", "document_id", "index", "reason"}
        - {"event": "document_completed", "document_id", "file_name", "stats"}
        - {"event": "document_failed", "document_id", "file_name", "error"}
        - {"event": "complete", "summary"}
        - {"event": "error", "message"}
        """
        start_time = time.time()

        # 1. Tërheq dokumentet
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
        }

        # 2. Ekstraktimet ekzistuese (cache)
        existing: Dict[str, Any] = {}
        if not force_reprocess:
            existing = self._fetch_existing_extractions(
                case_id, [str(d["_id"]) for d in documents]
            )

        # 3. Procesimi (sequential për SSE dhe rate-limit safety)
        total_entities = 0
        total_metadata_fields = 0
        total_role_conflicts = 0
        successful = 0
        failed = 0
        skipped = 0
        per_doc_stats: List[Dict[str, Any]] = []

        for idx, doc in enumerate(documents):
            doc_id = str(doc["_id"])
            file_name = doc.get("file_name", f"doc_{idx}")

            # Skip nëse ekziston
            if doc_id in existing:
                skipped += 1
                yield {
                    "event": "document_skipped",
                    "document_id": doc_id,
                    "file_name": file_name,
                    "index": idx,
                    "reason": "existing_extraction",
                }
                continue

            yield {
                "event": "document_started",
                "document_id": doc_id,
                "file_name": file_name,
                "index": idx,
                "total_documents": total,
            }

            try:
                result = await asyncio.wait_for(
                    self._process_document(doc, case_id, user_id),
                    timeout=DOCUMENT_TIMEOUT_SEC,
                )

                # Persist
                self._persist_extraction(result)

                total_entities += result["stats"]["total_entities"]
                total_metadata_fields += result["stats"]["metadata_fields_found"]
                total_role_conflicts += result["stats"].get(
                    "role_conflicts_resolved", 0
                )
                successful += 1
                per_doc_stats.append(result["stats"])

                yield {
                    "event": "document_completed",
                    "document_id": doc_id,
                    "file_name": file_name,
                    "stats": result["stats"],
                }

            except asyncio.TimeoutError:
                failed += 1
                logger.warning(
                    f"⚠️ [EXTRACT] Document {doc_id} timed out after "
                    f"{DOCUMENT_TIMEOUT_SEC}s"
                )
                yield {
                    "event": "document_failed",
                    "document_id": doc_id,
                    "file_name": file_name,
                    "error": f"Timeout after {DOCUMENT_TIMEOUT_SEC}s",
                }

            except Exception as e:
                failed += 1
                logger.exception(f"❌ [EXTRACT] Document {doc_id} failed")
                yield {
                    "event": "document_failed",
                    "document_id": doc_id,
                    "file_name": file_name,
                    "error": str(e),
                }

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
        }

        logger.info(f"✅ [EXTRACT] Pipeline complete: {summary}")
        yield {"event": "complete", "summary": summary}

    # ────────────────────────────────────────────────────────────────────
    # INTERNAL — fetch
    # ────────────────────────────────────────────────────────────────────

    def _fetch_documents(
        self,
        user_id: str,
        case_id: str,
        document_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Tërheq dokumentet e lëndës nga MongoDB (me tenant isolation)."""
        case_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id

        filter_q: Dict[str, Any] = {
            "$or": [{"case_id": case_id}, {"case_id": case_oid}],
            "status": {"$ne": "DELETED"},
        }

        if user_id:
            user_oid = ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id
            filter_q["owner_id"] = {"$in": [user_id, user_oid]}

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
        """Tërheq ekstraktimet ekzistuese për skip (cache)."""
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

    # ────────────────────────────────────────────────────────────────────
    # INTERNAL — process one document
    # ────────────────────────────────────────────────────────────────────

    async def _process_document(
        self,
        doc: Dict[str, Any],
        case_id: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """
        Përpunon një dokument: Kategorizim → NER → Metadata.
        Ekzekuton në thread pool për të mos bllokuar event loop.
        """
        doc_id = str(doc["_id"])
        file_name = doc.get("file_name", "Document")
        text = (
            doc.get("content")
            or doc.get("extracted_text")
            or doc.get("text")
            or ""
        )

        doc_start = time.time()

        # Dokument bosh
        if not text.strip():
            return {
                "document_id": doc_id,
                "case_id": str(case_id),
                "user_id": str(user_id),
                "file_name": file_name,
                "text_length": 0,
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

        # ────────────────────────────────────────────────────────────────
        # 1. KATEGORIZIM (V1.1) — përcakto document_type
        # ────────────────────────────────────────────────────────────────
        categorization = await loop.run_in_executor(
            None,
            lambda: self.categorizer.categorize_document_detailed(text),
        )
        document_type = categorization.get("primary_category")
        logger.info(
            f"📋 [EXTRACT] doc={doc_id}: categorized as "
            f"'{document_type}' (conf={categorization.get('confidence')})"
        )

        # ────────────────────────────────────────────────────────────────
        # 2. NER — me document_type hint (V33.2)
        # ────────────────────────────────────────────────────────────────
        ner_result = await loop.run_in_executor(
            None,
            lambda: self.ner.extract_legal_entities(
                text=text,
                document_id=doc_id,
                document_type=document_type,   # ← hint i ri V1.1
            ),
        )

        # ────────────────────────────────────────────────────────────────
        # 3. METADATA
        # ────────────────────────────────────────────────────────────────
        meta_result = await loop.run_in_executor(
            None,
            lambda: self.meta.extract(
                text=text,
                document_id=doc_id,
            ),
        )

        # Pastrim metadata
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
            },
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

    # ────────────────────────────────────────────────────────────────────
    # INTERNAL — persist (idempotent upsert)
    # ────────────────────────────────────────────────────────────────────

    def _persist_extraction(self, result: Dict[str, Any]) -> None:
        """Ruajtja idempotente në MongoDB. Upsert sipas (case_id, document_id)."""
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

    # ────────────────────────────────────────────────────────────────────
    # PUBLIC — helpers
    # ────────────────────────────────────────────────────────────────────

    def load_extractions(
        self,
        case_id: str,
        only_completed: bool = True,
    ) -> List[Dict[str, Any]]:
        """Lexon të gjitha ekstraktimet e ruajtura për një lëndë."""
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
        """Statistika të shpejta për një lëndë."""
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


# ────────────────────────────────────────────────────────────────────────────
# FACTORY
# ────────────────────────────────────────────────────────────────────────────

def get_extraction_pipeline(db: Any) -> ExtractionPipeline:
    """Factory — injekton `db` në pipeline."""
    return ExtractionPipeline(db)