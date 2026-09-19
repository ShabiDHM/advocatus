# FILE: backend/app/services/document_review/persistence.py
# PHOENIX PROTOCOL - PERSISTENCE V2.0
# Ngarkon dokumentin dhe ekstraktimin nga MongoDB; ruan rezultatin.

import logging
from typing import Any, Dict, Optional
from datetime import datetime, timezone
from bson import ObjectId

from .constants import SYNTHESIS_COLLECTION, EXTRACTION_COLLECTION
from .prompts import DOCUMENT_REVIEW_PROMPTS

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# LOADERS
# ═══════════════════════════════════════════════════════════════════════════

def load_document(db, case_id: str, document_id: str) -> Dict[str, Any]:
    """Ngarko dokumentin nga MongoDB."""
    try:
        case_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
        doc_oid = ObjectId(document_id) if ObjectId.is_valid(document_id) else document_id

        doc = db.documents.find_one({
            "_id": doc_oid,
            "$or": [
                {"case_id": case_id},
                {"case_id": case_oid},
                {"case_id": str(case_oid)},
            ],
        })
        return doc or {}
    except Exception as e:
        logger.warning(f"⚠️ load_document: {e}")
        return {}


def load_extraction(db, case_id: str, document_id: str) -> Optional[Dict[str, Any]]:
    """Ngarko ekstraktimin (NER + Metadata) nga MongoDB."""
    try:
        return db[EXTRACTION_COLLECTION].find_one({
            "case_id": str(case_id),
            "document_id": str(document_id),
            "status": "completed",
        })
    except Exception as e:
        logger.warning(f"⚠️ load_extraction: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════
# PERSIST
# ═══════════════════════════════════════════════════════════════════════════

def persist(db, result: Dict[str, Any]) -> None:
    """Ruan rezultatin në MongoDB."""
    try:
        db[SYNTHESIS_COLLECTION].update_one(
            {
                "case_id": result["case_id"],
                "scope": "document",
                "document_ids": result["document_ids"],
            },
            {"$set": result},
            upsert=True,
        )
    except Exception as e:
        logger.error(f"❌ Persist: {e}")
        raise


# ═══════════════════════════════════════════════════════════════════════════
# EMPTY RESULT
# ═══════════════════════════════════════════════════════════════════════════

def empty_result(case_id: str, document_id: str, reason: str) -> Dict[str, Any]:
    """Rezultat bosh për raste kur nuk ka tekst."""
    return {
        "case_id": case_id,
        "document_id": document_id,
        "scope": "document",
        "document_ids": [document_id],
        "built_at": datetime.now(timezone.utc).isoformat(),
        "sections": {},
        "stats": {
            "case_id": case_id,
            "document_id": document_id,
            "sections_generated": 0,
            "sections_total": len(DOCUMENT_REVIEW_PROMPTS),
            "duration_sec": 0.0,
        },
        "status": "empty",
        "warning": reason,
    }