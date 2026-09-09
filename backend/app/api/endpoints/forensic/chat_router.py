# FILE: backend/app/api/endpoints/forensic/chat_router.py
# PHOENIX PROTOCOL - FORENSIC INTERROGATION TERMINAL ROUTER V4.4 (CLEAN PROFESSIONAL STREAMING)
# 100% COMPLETE CODE • ZERO TS/PY WARNINGS • MULTI-DEVICE SYNC

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pymongo.database import Database
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from bson import ObjectId
from pydantic import BaseModel, Field
import logging

from app.core.db import get_db
from app.api.endpoints.dependencies import get_current_forensic_user
from app.models.user import UserInDB
from app.services.forensic.forensic_llm_service import call_forensic_llm_chat, stream_forensic_llm_chat_async
from app.services.forensic.forensic_hallucination_filter import purge_and_regenerate_if_hallucinated
from app.services.forensic.forensic_audit_service import log_forensic_action
from app.services.vector_store_service import query_case_knowledge_base, query_global_knowledge_base

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
            if isinstance(legacy_history, list):
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
# 2. DËRGIMI I PYETJES ME STREAMING (RAG + KUJTESË)
# ==========================================================
@router.post("/chat/stream")
async def stream_forensic_chat_message(
    payload: ForensicChatMessage,
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db)
):
    """
    Streaming endpoint për terminalin forenzik.
    Përdor RAG (Case Base + Knowledge Base) dhe transmeton token-at në kohë reale.
    """
    user_id = str(current_user.id)
    case_id_str = str(payload.case_id)
    now_utc = datetime.now(timezone.utc)

    # 1. Mbledh historikun e kaluar
    query = _build_case_query(case_id_str)
    past_cursor = db[FORENSIC_CHAT_COLLECTION].find(query).sort("created_at", 1).limit(40)

    conversation_turns: List[Dict[str, str]] = []
    for m in past_cursor:
        conversation_turns.append({
            "role": m.get("role", "user"),
            "content": m.get("content", "")
        })

    # Legacy fallback
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

    # Shto pyetjen aktuale
    conversation_turns.append({
        "role": "user",
        "content": payload.message
    })

    # 2. RAG CASE BASE
    case_chunks = []
    try:
        case_chunks = query_case_knowledge_base(
            user_id=user_id,
            query_text=payload.message,
            n_results=6,
            case_id=case_id_str
        )
    except Exception as e:
        logger.warning(f"Case base retrieval failed: {e}")

    # 3. RAG KNOWLEDGE BASE
    knowledge_chunks = []
    try:
        knowledge_chunks = query_global_knowledge_base(
            query_text=payload.message,
            n_results=8
        )
    except Exception as e:
        logger.warning(f"Knowledge base retrieval failed: {e}")

    # 4. Ruaj pyetjen e përdoruesit
    db[FORENSIC_CHAT_COLLECTION].insert_one({
        "case_id": case_id_str,
        "user_id": user_id,
        "role": "user",
        "content": payload.message,
        "created_at": now_utc
    })

    # 5. Ndërto system prompt TË PASTËR PROFESIONAL
    case_context_text = "\n".join([
        f"📄 {c.get('source','Dokument')} (Faqe {c.get('page','?')}): {c.get('text','')}"
        for c in case_chunks if c.get("text")
    ]) if case_chunks else "Nuk ka pjesë relevante nga dokumentet e lëndës."

    knowledge_context_text = "\n".join([
        f"{c.get('source','Ligj')}: {c.get('text','')}"
        for c in knowledge_chunks if c.get("text")
    ]) if knowledge_chunks else "Nuk ka referenca ligjore relevante."

    system_prompt = f"""Ju jeni një ekspert ligjor i specializuar për legjislacionin e Republikës së Kosovës.
Detyra juaj është të jepni përgjigje të sakta, profesionale dhe koncize, pa zhargon të panevojshëm, pa fraza marketingu, pa emoji dhe pa formatim të tepruar.

Përdorni vetëm gjuhë zyrtare juridike. Mos përfshini emra të tillë si "Terminali Forenzik Hetimor Suprem", "VULA FORENZIKE", etj. Përgjigjuni drejtpërdrejt pyetjes.

KONTEKSTI I LËNDËS:
{payload.case_context or 'Çështje hetimore forenzike'}

PJESËT RELEVANTE NGA DOKUMENTET E LËNDËS (CASE BASE):
{case_context_text}

REFERENCAT LIGJORE DHE PRAKTIKA E GJYKATËS SUPREME (KNOWLEDGE BASE):
{knowledge_context_text}"""

    # 6. Funksioni gjenerator për StreamingResponse
    async def generate():
        full_response = ""
        try:
            async for token in stream_forensic_llm_chat_async(
                conversation_turns=conversation_turns,
                system_prompt=system_prompt,
                temperature=0.0
            ):
                full_response += token
                yield token
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"\n\n[GABIM: {str(e)}]"
        finally:
            # Pas përfundimit, ruaj përgjigjen
            if full_response:
                # Verifikimi i citimeve
                try:
                    verified_text, audit_result = purge_and_regenerate_if_hallucinated(
                        response_text=full_response,
                        db=db,
                        original_prompt=payload.message
                    )
                    content_to_save = verified_text
                except Exception:
                    content_to_save = full_response
                    audit_result = None

                assistant_msg_doc = {
                    "case_id": case_id_str,
                    "user_id": user_id,
                    "role": "assistant",
                    "content": content_to_save,
                    "citation_audit": audit_result,
                    "created_at": datetime.now(timezone.utc)
                }
                db[FORENSIC_CHAT_COLLECTION].insert_one(assistant_msg_doc)

                # Sinkronizim për multi-device
                try:
                    case_oid = ObjectId(case_id_str) if ObjectId.is_valid(case_id_str) else case_id_str
                    db.cases.update_one(
                        {"$or": [{"_id": case_oid}, {"_id": case_id_str}]},
                        {
                            "$push": {
                                "forensic_chat_history": {
                                    "$each": [
                                        {"role": "user", "content": payload.message, "timestamp": now_utc.isoformat()},
                                        {"role": "assistant", "content": content_to_save, "timestamp": assistant_msg_doc["created_at"].isoformat()}
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
                    details={"query_preview": payload.message[:100], "streaming": True}
                )

    return StreamingResponse(
        generate(),
        media_type="text/plain; charset=utf-8",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )

# ==========================================================
# 3. TOTAL CASCADE WIPEOUT
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
        "message": f"Biseda u asgjësua plotësisht. U fshinë {del_result.deleted_count} mesazhe.",
        "deleted_count": del_result.deleted_count
    }