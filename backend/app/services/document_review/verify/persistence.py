# FILE: backend/app/services/document_review/verify/persistence.py
# PHOENIX PROTOCOL - VERIFY PERSISTENCE V1.0
# Ekstraktuar nga draft_verifier.py V1.17 (pa ndryshim logjike).

import logging
from typing import Any, Dict

from bson import ObjectId
from bson.errors import InvalidId

logger = logging.getLogger(__name__)


def persist_verification(
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