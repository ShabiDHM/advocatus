# FILE: backend/app/services/forensic/forensic_chain_of_custody.py
# PHOENIX PROTOCOL - CRYPTOGRAPHIC CHAIN OF CUSTODY V1.0 (SERVER-SIDE SEALING)

import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from app.core.config import settings

def _get_server_secret() -> bytes:
    key = getattr(settings, "SECRET_KEY", "juristi-forensic-secret") or "juristi-forensic-secret"
    return key.encode("utf-8")

def generate_evidence_hash(data_bytes: bytes) -> str:
    """Llogarit SHA-256 të një skedari apo përmbajtjeje binare."""
    return hashlib.sha256(data_bytes).hexdigest()

def generate_chain_of_custody_hash(
    user_id: str,
    case_id: str,
    action: str,
    timestamp: datetime,
    payload_data: Optional[Dict[str, Any]] = None
) -> str:
    """
    Gjeneron vulën kriptografike HMAC-SHA256 të pandryshueshme nga serveri.
    """
    canonical_payload = json.dumps(payload_data or {}, sort_keys=True)
    raw_signature_base = (
        f"CUSTODY|USER:{user_id}|CASE:{case_id}|ACTION:{action}|"
        f"TIME:{timestamp.isoformat()}|DATA:{canonical_payload}"
    )
    
    signature = hmac.new(
        _get_server_secret(),
        raw_signature_base.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    
    return signature

def create_custody_stamp(
    user_id: str,
    case_id: str,
    action: str,
    evidence_ids: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Krijon një bllok zyrtar të Chain of Custody të vulosur për databazë dhe dosje gjyqësore.
    """
    now_utc = datetime.now(timezone.utc)
    payload = {
        "evidence_ids": evidence_ids or [],
        "metadata": metadata or {}
    }
    
    custody_hash = generate_chain_of_custody_hash(
        user_id=user_id,
        case_id=case_id,
        action=action,
        timestamp=now_utc,
        payload_data=payload
    )
    
    return {
        "custody_hash": custody_hash,
        "sealed_at": now_utc,
        "sealed_by_user_id": user_id,
        "action": action,
        "algorithm": "HMAC-SHA256",
        "evidence_ids": evidence_ids or [],
        "is_verified": True,
        "metadata": metadata or {}
    }

def verify_custody_stamp(stamp_data: Dict[str, Any], user_id: str, case_id: str) -> bool:
    """Verifikon nëse vula është e pacënuar."""
    try:
        timestamp = stamp_data["sealed_at"]
        if isinstance(timestamp, str):
            clean_str = timestamp.replace("Z", "+00:00")
            timestamp = datetime.fromisoformat(clean_str)
            
        expected = generate_chain_of_custody_hash(
            user_id=user_id,
            case_id=case_id,
            action=stamp_data.get("action", ""),
            timestamp=timestamp,
            payload_data={
                "evidence_ids": stamp_data.get("evidence_ids", []),
                "metadata": stamp_data.get("metadata", {})
            }
        )
        return hmac.compare_digest(expected, stamp_data.get("custody_hash", ""))
    except Exception:
        return False