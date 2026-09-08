# FILE: backend/app/api/endpoints/forensic/chat_router.py
# PHOENIX PROTOCOL - FORENSIC INTERROGATION TERMINAL ROUTER V1.0 (STREAMING & CITATION AUDIT)

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pymongo.database import Database
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from app.core.db import get_db
from app.api.endpoints.dependencies import get_current_forensic_user
from app.models.user import UserInDB
from app.services.forensic.forensic_llm_service import call_forensic_llm, stream_forensic_llm_async
from app.services.forensic.forensic_hallucination_filter import purge_and_regenerate_if_hallucinated
from app.services.forensic.forensic_audit_service import log_forensic_action

router = APIRouter()

FORENSIC_CHAT_COLLECTION = "forensic_chat_history"

class ForensicChatMessage(BaseModel):
    case_id: str
    message: str = Field(..., min_length=1)
    case_context: Optional[str] = ""

@router.get("/chat/{case_id}/history")
def get_forensic_chat_history(
    case_id: str,
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db),
    limit: int = Query(50, ge=1, le=100)
):
    """Merr historikun e bisedave hetimore për një lëndë të caktuar."""
    cursor = db[FORENSIC_CHAT_COLLECTION].find(
        {"case_id": str(case_id)}
    ).sort("created_at", 1).limit(limit)

    messages = []
    for m in cursor:
        m["_id"] = str(m["_id"])
        if isinstance(m.get("created_at"), datetime):
            m["created_at"] = m["created_at"].isoformat()
        messages.append(m)
    return {"case_id": case_id, "messages": messages}

@router.post("/chat")
def send_forensic_chat_message(
    payload: ForensicChatMessage,
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db)
):
    """
    Dërgon pyetje te Claude Sonnet 4.6, verifikon citimet në DB,
    dhe ruan historikun e plotë në MongoDB.
    """
    user_id = str(current_user.id)
    now_utc = datetime.now(timezone.utc)

    # 1. Ruaj mesazhin e përdoruesit
    user_msg_doc = {
        "case_id": str(payload.case_id),
        "user_id": user_id,
        "role": "user",
        "content": payload.message,
        "created_at": now_utc
    }
    db[FORENSIC_CHAT_COLLECTION].insert_one(user_msg_doc)

    # 2. Përgatit kontekstin e mëparshëm
    past_msgs = list(db[FORENSIC_CHAT_COLLECTION].find(
        {"case_id": str(payload.case_id)}
    ).sort("created_at", -1).limit(6))
    past_msgs.reverse()

    history_text = "\n".join([f"{m.get('role', 'user').upper()}: {m.get('content', '')}" for m in past_msgs])

    system_prompt = f"""TERMINALI FORENZIK HETIMOR I ANALIZËS LIGJORE (CLAUDE SONNET 4.6):
Ju jeni hetuesi suprem ligjor për Republikën e Kosovës.
Analizoni pyetjen e avokatit/hetuesit bazuar në legjislacionin e Kosovës.

KONTEKSTI I LËNDËS:
{payload.case_context or 'Çështje hetimore forenzike'}

HISTORIKU I HETIMIT:
{history_text}"""

    # 3. Thirrja te Claude Sonnet 4.6
    raw_response = call_forensic_llm(
        system_prompt=system_prompt,
        user_content=payload.message,
        temperature=0.0
    )

    # 4. Filtri i halucinacioneve dhe verifikimi i neneve/precedentëve
    verified_text, audit_result = purge_and_regenerate_if_hallucinated(
        response_text=raw_response,
        db=db,
        original_prompt=payload.message
    )

    # 5. Ruaj përgjigjen e verifikuar të asistentit
    assistant_msg_doc = {
        "case_id": str(payload.case_id),
        "user_id": user_id,
        "role": "assistant",
        "content": verified_text,
        "citation_audit": audit_result,
        "created_at": datetime.now(timezone.utc)
    }
    result = db[FORENSIC_CHAT_COLLECTION].insert_one(assistant_msg_doc)

    log_forensic_action(
        db=db,
        user_id=user_id,
        case_id=payload.case_id,
        action="FORENSIC_INTERROGATION_QUERY",
        details={"query_preview": payload.message[:100], "is_citation_safe": audit_result.get("is_safe", True)}
    )

    return {
        "_id": str(result.inserted_id),
        "role": "assistant",
        "content": verified_text,
        "citation_audit": audit_result,
        "created_at": assistant_msg_doc["created_at"].isoformat()
    }

@router.post("/chat/stream")
async def stream_forensic_chat_message(
    payload: ForensicChatMessage,
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db)
):
    """
    Transmeton përgjigjen në kohë reale nga Claude Sonnet 4.6 për Terminalin.
    """
    user_id = str(current_user.id)
    now_utc = datetime.now(timezone.utc)

    # Ruaj pyetjen e përdoruesit
    db[FORENSIC_CHAT_COLLECTION].insert_one({
        "case_id": str(payload.case_id),
        "user_id": user_id,
        "role": "user",
        "content": payload.message,
        "created_at": now_utc
    })

    system_prompt = f"""TERMINALI FORENZIK INTERAKTIV (CLAUDE SONNET 4.6):
KONTEKSTI I LËNDËS:
{payload.case_context or 'Nuk ka kontekst shtesë.'}"""

    async def event_generator():
        collected_chunks = []
        try:
            async for chunk in stream_forensic_llm_async(
                system_prompt=system_prompt,
                user_content=payload.message,
                temperature=0.0
            ):
                collected_chunks.append(chunk)
                yield chunk
        finally:
            full_response = "".join(collected_chunks).strip()
            if full_response:
                db[FORENSIC_CHAT_COLLECTION].insert_one({
                    "case_id": str(payload.case_id),
                    "user_id": user_id,
                    "role": "assistant",
                    "content": full_response,
                    "created_at": datetime.now(timezone.utc)
                })
                log_forensic_action(
                    db=db,
                    user_id=user_id,
                    case_id=payload.case_id,
                    action="FORENSIC_STREAM_COMPLETED"
                )

    return StreamingResponse(event_generator(), media_type="text/plain")