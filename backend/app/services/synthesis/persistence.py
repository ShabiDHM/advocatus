# FILE: backend/app/services/synthesis/persistence.py
# PHOENIX PROTOCOL - PERSISTENCE V1.0
# Ekstraktuar nga synthesis_service.py V3.8 — ZERO ndryshim funksional.

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from bson import ObjectId

from .constants import (
    SYNTHESIS_COLLECTION,
    EXTRACTION_COLLECTION,
    CROSS_REF_COLLECTION,
)
from .prompts import SECTION_PROMPTS

logger = logging.getLogger(__name__)


def load_case(db, case_id: str) -> Dict[str, Any]:
    try:
        c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
        doc = db.cases.find_one({"_id": c_oid})
        return doc or {}
    except Exception:
        return {}


def load_extractions(db, case_id: str) -> List[Dict[str, Any]]:
    try:
        query = {"case_id": str(case_id), "status": "completed"}
        cursor = db[EXTRACTION_COLLECTION].find(query).sort([("completed_at", 1)])
        return list(cursor)
    except Exception:
        return []


def load_cross_refs(db, case_id: str) -> Dict[str, Any]:
    try:
        doc = db[CROSS_REF_COLLECTION].find_one({"case_id": str(case_id)})
        return doc or {}
    except Exception:
        return {}


def persist(db, result: Dict[str, Any]) -> None:
    try:
        db[SYNTHESIS_COLLECTION].update_one(
            {"case_id": result["case_id"], "scope": "case"},
            {"$set": result},
            upsert=True,
        )
    except Exception as e:
        logger.error(f"❌ [SYNTHESIS] Persist failed: {e}")
        raise


def empty_result(case_id: str, reason: str) -> Dict[str, Any]:
    return {
        "case_id": case_id,
        "scope": "case",
        "built_at": datetime.now(timezone.utc).isoformat(),
        "sections": {},
        "stats": {
            "case_id": case_id,
            "scope": "case",
            "documents_analyzed": 0,
            "sections_generated": 0,
            "sections_total": len(SECTION_PROMPTS),
            "duration_sec": 0.0,
        },
        "status": "empty",
        "warning": reason,
    }


def load(db, case_id: str) -> Optional[Dict[str, Any]]:
    try:
        return db[SYNTHESIS_COLLECTION].find_one({
            "case_id": str(case_id),
            "scope": "case",
        })
    except Exception:
        return None