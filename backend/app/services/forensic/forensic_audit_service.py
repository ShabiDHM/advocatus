# FILE: backend/app/services/forensic/forensic_audit_service.py
# PHOENIX PROTOCOL - TAMPER-EVIDENT FORENSIC AUDIT TRAIL V1.0

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pymongo.database import Database
from bson import ObjectId

from .forensic_chain_of_custody import create_custody_stamp

logger = logging.getLogger(__name__)

FORENSIC_AUDIT_COLLECTION = "forensic_audit"

def log_forensic_action(
    db: Database,
    user_id: str,
    case_id: str,
    action: str,
    details: Optional[Dict[str, Any]] = None,
    evidence_ids: Optional[List[str]] = None,
    ip_address: Optional[str] = None
) -> str:
    """
    Regjistron veprimin hetimor me vulë të plotë Chain of Custody në MongoDB.
    Kthen ID-në e regjistrit të auditimit.
    """
    try:
        stamp = create_custody_stamp(
            user_id=user_id,
            case_id=case_id,
            action=action,
            evidence_ids=evidence_ids,
            metadata={"ip_address": ip_address}
        )

        audit_doc = {
            "user_id": str(user_id),
            "case_id": str(case_id),
            "action": action,
            "details": details or {},
            "evidence_ids": evidence_ids or [],
            "ip_address": ip_address,
            "custody_hash": stamp["custody_hash"],
            "sealed_at": stamp["sealed_at"],
            "created_at": datetime.now(timezone.utc)
        }

        result = db[FORENSIC_AUDIT_COLLECTION].insert_one(audit_doc)
        logger.info(f"🛡️ [Forensic Audit] Veprimi '{action}' për lëndën {case_id} u vulos me hash: {stamp['custody_hash'][:12]}...")
        return str(result.inserted_id)
    except Exception as e:
        logger.error(f"❌ [Forensic Audit Failure] Dështoi regjistrimi i auditimit: {e}")
        return ""

def get_case_audit_trail(
    db: Database,
    case_id: str,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """Nxjerr të gjitha veprimet e vulosura për një dosje forenzike."""
    try:
        cursor = db[FORENSIC_AUDIT_COLLECTION].find(
            {"case_id": str(case_id)}
        ).sort("sealed_at", -1).limit(limit)

        records = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            if isinstance(doc.get("sealed_at"), datetime):
                doc["sealed_at"] = doc["sealed_at"].isoformat()
            if isinstance(doc.get("created_at"), datetime):
                doc["created_at"] = doc["created_at"].isoformat()
            records.append(doc)
        return records
    except Exception as e:
        logger.error(f"❌ [Forensic Audit Query] Gabim gjatë leximit të audit trail: {e}")
        return []