# FILE: backend/app/services/document_review/persistence.py
# PHOENIX PROTOCOL - PERSISTENCE V2.1
# V2.1: LOAD_EXTRACTION DIAGNOSTICS — load_extraction() tani logon statusin
#       real kur extraction != completed: "processing"/"pending"/"queued"
#       → INFO me udhëzim; "failed" → WARNING me arsyen; mungon → INFO.
#       Përpara: None silent → user shihte "Drafti nuk ka tekst" pa e ditur pse.
# V2.0: Ngarkon dokumentin dhe ekstraktimin nga MongoDB; ruan rezultatin.

import logging
from typing import Any, Dict, Optional, Tuple
from datetime import datetime, timezone
from bson import ObjectId

from .constants import SYNTHESIS_COLLECTION, EXTRACTION_COLLECTION
from .prompts import DOCUMENT_REVIEW_PROMPTS

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# V2.1: EXTRACTION STATUS CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════

_EXTRACTION_STATUS_IN_PROGRESS = {"processing", "pending", "queued", "running"}


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


def _find_extraction_any_status(
    db, case_id: str, document_id: str,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    V2.1: Gjen ekstraktimin e çdo statusi (jo vetëm completed).

    Kthen (entry, status) ose (None, None) nëse mungon fare.
    """
    try:
        entry = db[EXTRACTION_COLLECTION].find_one({
            "case_id": str(case_id),
            "document_id": str(document_id),
        })
        if not entry:
            return None, None
        return entry, str(entry.get("status", "")).lower()
    except Exception as e:
        logger.warning(f"⚠️ _find_extraction_any_status: {e}")
        return None, None


def load_extraction(db, case_id: str, document_id: str) -> Optional[Dict[str, Any]]:
    """
    V2.1: Ngarko ekstraktimin (NER + Metadata) nga MongoDB.

    Diagnostikon statusin kur ekstraktimi nuk është "completed":
      - processing/pending/queued/running → INFO ("prit")
      - failed/error → WARNING me arsyen
      - mungon → INFO
    """
    try:
        # 1. Provo completed direkt
        completed = db[EXTRACTION_COLLECTION].find_one({
            "case_id": str(case_id),
            "document_id": str(document_id),
            "status": "completed",
        })
        if completed:
            return completed

        # 2. Nuk ka "completed" — diagnostiko pse
        entry, status = _find_extraction_any_status(db, case_id, document_id)

        if entry is None:
            logger.info(
                f"ℹ️ [load_extraction] Pa ekstraktim: case={case_id}, "
                f"doc={document_id} — verifiko draftin me fallback (document.content)."
            )
            return None

        if status in _EXTRACTION_STATUS_IN_PROGRESS:
            logger.info(
                f"⏳ [load_extraction] Ekstraktimi në progres: case={case_id}, "
                f"doc={document_id}, status='{status}'. "
                f"Verifiko draftin përpara se ekstraktimi të mbarojë — "
                f"përdoret fallback i document.content."
            )
            return None

        if status in ("failed", "error"):
            reason = entry.get("error_message") or entry.get("error") or "(pa arsye)"
            logger.warning(
                f"⚠️ [load_extraction] Ekstraktimi dështoi: case={case_id}, "
                f"doc={document_id}, status='{status}', reason='{reason}'. "
                f"Verifiko draftin me fallback (document.content)."
            )
            return None

        # Status tjetër i panjohur
        logger.warning(
            f"⚠️ [load_extraction] Status i panjohur '{status}' për "
            f"case={case_id}, doc={document_id}. Fallback në document.content."
        )
        return None

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