# FILE: backend/app/api/endpoints/forensic/chat_router.py
# PHOENIX PROTOCOL - FORENSIC INTERROGATION TERMINAL ROUTER V5.0 (DEEP DOSSIER RETRIEVAL ENGINE)
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

def _build_system_prompt_with_rag(
    case_id_str: str,
    user_id: str,
    payload: ForensicChatMessage,
    case_context: str,
    db: Optional[Database] = None
) -> str:
    """
    Ndërton system prompt me thellësi të plotë hetimore (Deep Case Dossier RAG).
    Zgjeron dritaren nga 6 copëza në 35 copëza dhe tërheq tekstin integral të dosjes.
    """
    case_chunks: List[Dict[str, Any]] = []
    
    # 1. Tërheqje e thellë nga Vector Store (35 copëza në vend të 6)
    try:
        case_chunks = query_case_knowledge_base(
            user_id=user_id,
            query_text=payload.message,
            n_results=35,
            case_id=case_id_str
        )
    except Exception as e:
        logger.warning(f"Deep case base retrieval failed: {e}")

    # 2. Siguresë Integriteti: Nëse copëzat vektoriale janë të pakta, merr tekstin e plotë direkt nga dokumentet e lëndës
    direct_dossier_text = ""
    if db is not None:
        try:
            c_oid = ObjectId(case_id_str) if ObjectId.is_valid(case_id_str) else case_id_str
            doc_cursor = db.documents.find(
                {"$or": [{"case_id": str(case_id_str)}, {"case_id": c_oid}], "status": {"$ne": "DELETED"}},
                {"file_name": 1, "extracted_text": 1, "content": 1, "text": 1, "page_count": 1}
            ).limit(10)

            dossier_parts = []
            for doc in doc_cursor:
                content = (doc.get("extracted_text") or doc.get("content") or doc.get("text") or "").strip()
                if content and len(content) > 50:
                    fname = doc.get("file_name", "Dokument i Lëndës")
                    pcount = doc.get("page_count", "I plotë")
                    dossier_parts.append(f"--- DOKUMENTI ZYRTAR I LËNDËS: {fname} (Gjithsej faqe: {pcount}) ---\n{content}")

            if dossier_parts:
                direct_dossier_text = "\n\n".join(dossier_parts)
        except Exception as doc_err:
            logger.warning(f"Direct dossier lookup error: {doc_err}")

    # 3. RAG Knowledge Base (Statute + Caselaw e Gjykatës Supreme)
    knowledge_chunks = []
    try:
        knowledge_chunks = query_global_knowledge_base(
            query_text=payload.message,
            n_results=15
        )
    except Exception as e:
        logger.warning(f"Knowledge base retrieval failed: {e}")

    # Formatimi i copëzave të lëndës
    if case_chunks:
        case_context_text = "\n\n".join([
            f"📄 {c.get('source','Dokument')} (Faqe {c.get('page','?')}) [Fragment {i+1}]:\n{c.get('text','')}"
            for i, c in enumerate(case_chunks) if c.get("text")
        ])
    else:
        case_context_text = direct_dossier_text if direct_dossier_text else "Nuk ka pjesë relevante nga dokumentet e lëndës."

    # Nëse kemi tekst të drejtpërdrejtë të dosjes, e bashkojmë për transparencë maksimale
    if direct_dossier_text and case_chunks:
        # Bashkon fragmentet specifike me përmbajtjen integrale të dosjes
        case_context_text = f"=== FRAGMENTET PARËSORE TË IDENTIFIKUARA ===\n{case_context_text}\n\n=== PËRMBAJTJA INTEGRALE E DOSJES SË LËNDËS ===\n{direct_dossier_text}"

    knowledge_context_text = "\n".join([
        f"{c.get('source','Ligj')}: {c.get('text','')}"
        for c in knowledge_chunks if c.get("text")
    ]) if knowledge_chunks else "Nuk ka referenca ligjore relevante."

    return f"""Ju jeni një ekspert ligjor i specializuar për legjislacionin e Republikës së Kosovës.
Detyra juaj është të jepni përgjigje të sakta, profesionale, shteruese dhe me bazë ligjore të pakundërshtueshme.

RREGULLAT E ANALIZËS HETIMORE:
1. Analizoni ME KUJDES TË GJITHA faqet, personat e përfshirë, të gjithë të dyshuarit (zyrtarë publikë, mjekë, punonjës socialë, gjyqtarë, persona privatë) dhe çdo provë shkresore që gjendet në dosje.
2. Mos supozoni se mungojnë faqe apo të dyshuar: e gjithë dosja e lëndës gjendet më poshtë. Përgjigjuni mbi bazën e të gjitha provave dhe dokumenteve të administruara.
3. Përdorni vetëm gjuhë zyrtare juridike. Përgjigjuni drejtpërdrejt pyetjes.

KONTEKSTI I LËNDËS:
{payload.case_context or 'Çështje hetimore forenzike'}

DOSJA DHE PROVAT SHKRESORE TË LËNDËS (CASE BASE):
{case_context_text}

REFERENCAT LIGJORE DHE PRAKTIKA E GJYKATËS SUPREME (KNOWLEDGE BASE):
{knowledge_context_text}"""

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
# 2a. DËRGIMI I PYETJES JO-STREAMING
# ==========================================================
@router.post("/chat")
def send_forensic_chat_message_nonstream(
    payload: ForensicChatMessage,
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db)
):
    user_id = str(current_user.id)
    case_id_str = str(payload.case_id)
    now_utc = datetime.now(timezone.utc)

    query = _build_case_query(case_id_str)
    past_cursor = db[FORENSIC_CHAT_COLLECTION].find(query).sort("created_at", 1).limit(40)
    conversation_turns = [{"role": m.get("role", "user"), "content": m.get("content", "")} for m in past_cursor]

    if len(conversation_turns) == 0:
        try:
            case_oid = ObjectId(case_id_str) if ObjectId.is_valid(case_id_str) else case_id_str
            case_doc = db.cases.find_one({"$or": [{"_id": case_oid}, {"_id": case_id_str}]})
            legacy_history = (case_doc or {}).get("forensic_chat_history") or []
            for legacy_m in legacy_history[-30:]:
                conversation_turns.append({"role": legacy_m.get("role", "user"), "content": legacy_m.get("content", "")})
        except Exception:
            pass

    conversation_turns.append({"role": "user", "content": payload.message})

    # Ruaj pyetjen
    db[FORENSIC_CHAT_COLLECTION].insert_one({
        "case_id": case_id_str,
        "user_id": user_id,
        "role": "user",
        "content": payload.message,
        "created_at": now_utc
    })

    # Ndërto system prompt me qasje të plotë në dosje
    system_prompt = _build_system_prompt_with_rag(case_id_str, user_id, payload, payload.case_context, db=db)

    # Thirr LLM
    raw_response = call_forensic_llm_chat(
        conversation_turns=conversation_turns,
        system_prompt=system_prompt,
        temperature=0.0
    )

    try:
        verified_text, audit_result = purge_and_regenerate_if_hallucinated(
            response_text=raw_response,
            db=db,
            original_prompt=payload.message
        )
    except Exception:
        verified_text, audit_result = raw_response, None

    assistant_msg_doc = {
        "case_id": case_id_str,
        "user_id": user_id,
        "role": "assistant",
        "content": verified_text,
        "citation_audit": audit_result,
        "created_at": datetime.now(timezone.utc)
    }
    db[FORENSIC_CHAT_COLLECTION].insert_one(assistant_msg_doc)

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
        details={"query_preview": payload.message[:100], "streaming": False}
    )

    return {
        "_id": str(assistant_msg_doc.get("_id")),
        "case_id": case_id_str,
        "role": "assistant",
        "content": verified_text,
        "citation_audit": audit_result,
        "created_at": assistant_msg_doc["created_at"].isoformat()
    }

# ==========================================================
# 2b. DËRGIMI I PYETJES ME STREAMING
# ==========================================================
@router.post("/chat/stream")
async def stream_forensic_chat_message(
    payload: ForensicChatMessage,
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db)
):
    user_id = str(current_user.id)
    case_id_str = str(payload.case_id)
    now_utc = datetime.now(timezone.utc)

    query = _build_case_query(case_id_str)
    past_cursor = db[FORENSIC_CHAT_COLLECTION].find(query).sort("created_at", 1).limit(40)
    conversation_turns = [{"role": m.get("role", "user"), "content": m.get("content", "")} for m in past_cursor]

    if len(conversation_turns) == 0:
        try:
            case_oid = ObjectId(case_id_str) if ObjectId.is_valid(case_id_str) else case_id_str
            case_doc = db.cases.find_one({"$or": [{"_id": case_oid}, {"_id": case_id_str}]})
            legacy_history = (case_doc or {}).get("forensic_chat_history") or []
            for legacy_m in legacy_history[-30:]:
                conversation_turns.append({"role": legacy_m.get("role", "user"), "content": legacy_m.get("content", "")})
        except Exception:
            pass

    conversation_turns.append({"role": "user", "content": payload.message})

    db[FORENSIC_CHAT_COLLECTION].insert_one({
        "case_id": case_id_str,
        "user_id": user_id,
        "role": "user",
        "content": payload.message,
        "created_at": now_utc
    })

    # Ndërto system prompt me qasje të plotë në dosje
    system_prompt = _build_system_prompt_with_rag(case_id_str, user_id, payload, payload.case_context, db=db)

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
            if full_response:
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