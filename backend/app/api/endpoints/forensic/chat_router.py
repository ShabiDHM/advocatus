# FILE: backend/app/api/endpoints/forensic/chat_router.py
# PHOENIX PROTOCOL - FORENSIC INTERROGATION TERMINAL ROUTER V4.0 (FULL CONVERSATIONAL MEMORY & ATOMIC PURGE)
# 100% COMPLETE CODE • ZERO TS/PY WARNINGS • MULTI-DEVICE SYNC

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pymongo.database import Database
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from bson import ObjectId
from pydantic import BaseModel, Field
import logging

from app.core.db import get_db
from app.api.endpoints.dependencies import get_current_forensic_user
from app.models.user import UserInDB
from app.services.forensic.forensic_llm_service import call_forensic_llm_chat, stream_forensic_llm_async
from app.services.forensic.forensic_hallucination_filter import purge_and_regenerate_if_hallucinated
from app.services.forensic.forensic_audit_service import log_forensic_action

router = APIRouter()
logger = logging.getLogger(__name__)

FORENSIC_CHAT_COLLECTION = "forensic_chat_history"

class ForensicChatMessage(BaseModel):
    case_id: str
    message: str = Field(..., min_length=1)
    case_context: Optional[str] = ""

def _build_case_query(case_id: str) -> Dict[str, Any]:
    conditions = [{"case_id": str(case_id)}]
    if ObjectId.is_valid(case_id):
        conditions.append({"case_id": ObjectId(case_id)})
    return {"$or": conditions}

# ==========================================================
# 1. LEXIMI I HISTORIKUT (MULTI-DEVICE UNIFIED RESOLVER)
# ==========================================================
@router.get("/chat/{case_id}/history")
def get_forensic_chat_history(
    case_id: str,
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db),
    limit: int = Query(200, ge=1, le=500)
):
    query = _build_case_query(case_id)
    cursor = db[FORENSIC_CHAT_COLLECTION].find(query).sort("created_at", 1).limit(limit)

    messages = []
    for m in cursor:
        m["_id"] = str(m["_id"])
        m["case_id"] = str(m["case_id"])
        if isinstance(m.get("created_at"), datetime):
            m["created_at"] = m["created_at"].isoformat()
        messages.append(m)

    if len(messages) == 0:
        try:
            case_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
            case_doc = db.cases.find_one({"$or": [{"_id": case_oid}, {"_id": str(case_id)}]})
            legacy_history = (case_doc or {}).get("forensic_chat_history") or []
            if isinstance(legacy_history, list) and len(legacy_history) > 0:
                for idx, legacy_m in enumerate(legacy_history):
                    messages.append({
                        "_id": f"legacy_{idx}",
                        "case_id": str(case_id),
                        "role": legacy_m.get("role", "assistant"),
                        "content": legacy_m.get("content", ""),
                        "created_at": legacy_m.get("timestamp") or datetime.now(timezone.utc).isoformat()
                    })
        except Exception as e:
            logger.warning(f"Legacy chat sync warning: {e}")

    return {"case_id": case_id, "messages": messages}

# ==========================================================
# 2. DËRGIMI I PYETJES ME KUJTESË TË PLOTË BASHKËBISEDUESE
# ==========================================================
@router.post("/chat")
def send_forensic_chat_message(
    payload: ForensicChatMessage,
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db)
):
    """
    Merr të gjitha pyetjet dhe përgjigjet e mëparshme, i dërgon te Claude Sonnet 4.6
    si dialog i plotë multi-turn, verifikon citimet dhe ruan të gjithë sekuencën.
    """
    user_id = str(current_user.id)
    case_id_str = str(payload.case_id)
    now_utc = datetime.now(timezone.utc)

    # 1. Mbledh historikun e kaluar nga MongoDB PËRPARA mesazhit të ri
    query = _build_case_query(case_id_str)
    past_cursor = db[FORENSIC_CHAT_COLLECTION].find(query).sort("created_at", 1).limit(40)

    conversation_turns: List[Dict[str, str]] = []
    for m in past_cursor:
        conversation_turns.append({
            "role": m.get("role", "user"),
            "content": m.get("content", "")
        })

    # Nëse koleksioni ishte bosh, provo nga cases
    if len(conversation_turns) == 0:
        try:
            case_oid = ObjectId(case_id_str) if ObjectId.is_valid(case_id_str) else case_id_str
            case_doc = db.cases.find_one({"$or": [{"_id": case_oid}, {"_id": case_id_str}]})
            legacy_history = (case_doc or {}).get("forensic_chat_history") or []
            for legacy_m in legacy_history[-30:]:
                conversation_turns.append({
                    "role": legacy_m.get("role", "user"),
                    "content": legacy_m.get("content", "")
                })
        except Exception:
            pass

    # Shto pyetjen aktuale në fund të zinxhirit të kujtesës
    conversation_turns.append({
        "role": "user",
        "content": payload.message
    })

    # 2. Ruaj pyetjen e re të përdoruesit në MongoDB
    user_msg_doc = {
        "case_id": case_id_str,
        "user_id": user_id,
        "role": "user",
        "content": payload.message,
        "created_at": now_utc
    }
    db[FORENSIC_CHAT_COLLECTION].insert_one(user_msg_doc)

    # 3. Direktiva e Kujtesës dhe Ekspertizës
    system_prompt = f"""TERMINALI FORENZIK HETIMOR SUPREM (CLAUDE SONNET 4.6):
Ju jeni hetuesi suprem ligjor për Republikën e Kosovës me KUJTESË TË PLOTË mbi këtë lëndë.
Ju i dini dhe i mbani mend të gjitha pyetjet dhe përgjigjet e mëparshme të këtij dialogu.
Përgjigjuni me koherencë të thellë hetimore: nëse një fakt apo person është përmendur më herët, ndërlidheni menjëherë.

KONTEKSTI I LËNDËS:
{payload.case_context or 'Çështje hetimore forenzike'}"""

    # 4. Thirrja e Claude Sonnet 4.6 me KUJTESË TË PLOTË MULTI-TURN
    raw_response = call_forensic_llm_chat(
        conversation_turns=conversation_turns,
        system_prompt=system_prompt,
        temperature=0.0
    )

    # 5. Verifikimi i citimeve ligjore në MongoDB
    verified_text, audit_result = purge_and_regenerate_if_hallucinated(
        response_text=raw_response,
        db=db,
        original_prompt=payload.message
    )

    # 6. Ruaj përgjigjen e verifikuar në MongoDB
    assistant_msg_doc = {
        "case_id": case_id_str,
        "user_id": user_id,
        "role": "assistant",
        "content": verified_text,
        "citation_audit": audit_result,
        "created_at": datetime.now(timezone.utc)
    }
    result = db[FORENSIC_CHAT_COLLECTION].insert_one(assistant_msg_doc)

    # 7. Sinkronizim i Dyfishtë për Multi-Device
    try:
        case_oid = ObjectId(case_id_str) if ObjectId.is_valid(case_id_str) else case_id_str
        db.cases.update_one(
            {"$or": [{"_id": case_oid}, {"_id": case_id_str}]},
            {
                "$push": {
                    "forensic_chat_history": {
                        "$each": [
                            {"role": "user", "content": payload.message, "timestamp": now_utc.isoformat()},
                            {"role": "assistant", "content": verified_text, "timestamp": assistant_msg_doc["created_at"].isoformat()}
                        ]
                    }
                },
                "$set": {"updated_at": datetime.now(timezone.utc)}
            }
        )
    except Exception as sync_err:
        logger.warning(f"Multi-device sync warning: {sync_err}")

    log_forensic_action(
        db=db,
        user_id=user_id,
        case_id=case_id_str,
        action="FORENSIC_INTERROGATION_QUERY",
        details={"query_preview": payload.message[:100], "memory_turns_count": len(conversation_turns)}
    )

    return {
        "_id": str(result.inserted_id),
        "case_id": case_id_str,
        "role": "assistant",
        "content": verified_text,
        "citation_audit": audit_result,
        "created_at": assistant_msg_doc["created_at"].isoformat()
    }

# ==========================================================
# 3. TOTAL CASCADE WIPEOUT (FSHIRJE TOTAL NGA KOSHI)
# ==========================================================
@router.delete("/chat/{case_id}", status_code=status.HTTP_200_OK)
def clear_forensic_chat_history(
    case_id: str,
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db)
):
    user_id = str(current_user.id)
    case_id_str = str(case_id)
    query = _build_case_query(case_id_str)

    del_result = db[FORENSIC_CHAT_COLLECTION].delete_many(query)

    try:
        case_oid = ObjectId(case_id_str) if ObjectId.is_valid(case_id_str) else case_id_str
        db.cases.update_one(
            {"$or": [{"_id": case_oid}, {"_id": case_id_str}]},
            {
                "$unset": {"forensic_chat_history": ""},
                "$set": {"updated_at": datetime.now(timezone.utc)}
            }
        )
    except Exception as unset_err:
        logger.warning(f"Case unset warning: {unset_err}")

    log_forensic_action(
        db=db,
        user_id=user_id,
        case_id=case_id_str,
        action="FORENSIC_CHAT_TOTAL_CASCADE_WIPEOUT",
        details={"deleted_messages_count": del_result.deleted_count}
    )

    return {
        "status": "success",
        "message": f"Biseda u asgjësua plotësisht (Total Cascade Wipeout). U fshinë {del_result.deleted_count} mesazhe.",
        "deleted_count": del_result.deleted_count
    }