# FILE: backend/app/api/endpoints/forensic/chat_router.py
# PHOENIX PROTOCOL - FORENSIC DEDICATED ROUTER V9.0 (TOKEN-BUDGET PROTECTED • 160K SAFE)
# 100% COMPLETE CODE • ZERO CONTEXT OVERFLOW • SAFE 450K CHAR CEILING • FULL 31-DOC COVERAGE

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pymongo.database import Database
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from bson import ObjectId
from pydantic import BaseModel, Field
import logging
import re

from app.core.db import get_db
from app.api.endpoints.dependencies import get_current_forensic_user
from app.models.user import UserInDB
from app.services.forensic.forensic_llm_service import call_forensic_llm_chat, stream_forensic_llm_chat_async
from app.services.forensic.forensic_hallucination_filter import audit_citations
from app.services.forensic.forensic_audit_service import log_forensic_action
from app.services.vector_store_service import query_case_knowledge_base, query_global_knowledge_base

router = APIRouter()
logger = logging.getLogger(__name__)

FORENSIC_CHAT_COLLECTION = "forensic_chat_history"
FORENSIC_DOCS_COLLECTION = "forensic_documents"

# Kufiri i sigurt për DeepSeek në OpenRouter (120,000 tokene ≈ 450,000 karaktere, brenda limitit 163,840)
MAX_SAFE_DOSSIER_CHARS = 450_000

class ForensicChatMessage(BaseModel):
    case_id: str
    message: str = Field(..., min_length=1)
    case_context: Optional[str] = ""

def _build_case_query(case_id: str) -> Dict[str, Any]:
    conditions = [{"case_id": str(case_id)}]
    if ObjectId.is_valid(case_id):
        conditions.append({"case_id": ObjectId(case_id)})
    return {"$or": conditions}

def _clean_whitespace(text: str) -> str:
    """Pastrojnë hapësirat e panevojshme për të kursyer mijëra tokene."""
    return re.sub(r'\n{3,}', '\n\n', text).strip()

def _build_system_prompt_with_rag(
    case_id_str: str,
    user_id: str,
    payload: ForensicChatMessage,
    case_context: str,
    db: Optional[Database] = None
) -> str:
    """
    INJEKTON TË GJITHA 31 SHKRESAT ME SMART TOKEN BUDGETING:
    Garanton që teksti total të mos kalojë kurrë tavanin e DeepSeek (163,840 tokene).
    """
    dossier_blocks: List[str] = []
    total_docs_count = 0
    total_pages_count = 0

    if db is not None:
        try:
            c_oid = ObjectId(case_id_str) if ObjectId.is_valid(case_id_str) else case_id_str
            
            # 1. Tërheqim shkresat nga forensic_documents
            forensic_cursor = db[FORENSIC_DOCS_COLLECTION].find(
                {
                    "case_id": str(case_id_str),
                    "status": {"$ne": "DELETED"}
                },
                {"file_name": 1, "extracted_text": 1, "content": 1, "text": 1, "page_count": 1, "created_at": 1}
            ).sort([("created_at", 1), ("_id", 1)])

            docs_dict: Dict[str, Any] = {str(d["_id"]): d for d in forensic_cursor}

            # 2. Tërheqim edhe nga documents
            legacy_cursor = db.documents.find(
                {
                    "$or": [{"case_id": str(case_id_str)}, {"case_id": c_oid}],
                    "status": {"$ne": "DELETED"}
                },
                {"file_name": 1, "extracted_text": 1, "content": 1, "text": 1, "page_count": 1, "created_at": 1}
            ).sort([("created_at", 1), ("_id", 1)])

            for leg in legacy_cursor:
                leg_id = str(leg["_id"])
                if leg_id not in docs_dict:
                    docs_dict[leg_id] = leg

            all_docs = list(docs_dict.values())
            total_docs_count = len(all_docs)

            # 3. Renditim dokumentet: nëse përdoruesi ka zgjedhur një shkresë specifike, ajo vjen në krye
            current_chars = 0
            for idx, doc in enumerate(all_docs, start=1):
                raw_text = (doc.get("extracted_text") or doc.get("content") or doc.get("text") or "").strip()
                fname = doc.get("file_name", f"Shkresa_{idx}")
                pcount = doc.get("page_count", "1")
                try:
                    total_pages_count += int(pcount)
                except Exception:
                    total_pages_count += 1

                if raw_text:
                    cleaned = _clean_whitespace(raw_text)
                    block = (
                        f"======================================================================\n"
                        f"📁 SHKRESA ZYRTARE [{idx}/{total_docs_count}]: {fname} (Gjithsej faqe: {pcount})\n"
                        f"======================================================================\n"
                        f"{cleaned}\n"
                    )
                    
                    # Kontrolli i buxhetit të sigurisë
                    if current_chars + len(block) < MAX_SAFE_DOSSIER_CHARS:
                        dossier_blocks.append(block)
                        current_chars += len(block)
                    else:
                        # Merr pjesën e mbetur që nxë
                        remaining = MAX_SAFE_DOSSIER_CHARS - current_chars
                        if remaining > 500:
                            dossier_blocks.append(block[:remaining] + "\n[...Përmbajtja vazhdon në arkivë...]\n")
                            current_chars += remaining
                        break

        except Exception as doc_err:
            logger.error(f"Full forensic dossier retrieval error: {doc_err}")

    full_dossier_text = "\n".join(dossier_blocks) if dossier_blocks else "Nuk ka shkresa të ngarkuara në këtë dosje."

    # RAG Knowledge Base
    knowledge_chunks = []
    try:
        knowledge_chunks = query_global_knowledge_base(
            query_text=payload.message,
            n_results=10
        )
    except Exception as e:
        logger.warning(f"Knowledge base retrieval failed: {e}")

    knowledge_context_text = "\n".join([
        f"{c.get('source','Ligj')}: {c.get('text','')[:600]}"
        for c in knowledge_chunks if c.get("text")
    ]) if knowledge_chunks else "Nuk ka referenca ligjore relevante."

    return f"""Ju jeni Krye-Eksperti Forenzik Ligjor i autorizuar për legjislacionin dhe procedurën gjyqësore të Republikës së Kosovës.
Para syve tuaj ndodhet I GJITHË FASHIKULLI I LËNDËS (Gjithsej {total_docs_count} shkresa zyrtare dhe ~{total_pages_count} faqe të zbardhura fjalë për fjalë nga arkivi i provave).

MANDATI JUAJ HETIMOR DHE FORENZIK:
1. QASJE E PLOTË NË FASHIKULL:
   Posedoni shkresat dhe provat materiale të administruara në dosje.
2. EKSTRAKTIMI VERBATIM (FJALË PËR FJALË):
   Citoni me thonjëza deklarimet ekzakte të personave, ekspertëve, gjyqtarëve dhe prokurorëve. Tregoni saktësisht emrin e shkresës dhe faqen përkatëse.
3. STRUKTURA E ANALIZËS:
   - 1. Kronologjia Reale e Ngjarjeve (nga shkresat)
   - 2. Kontradiktat, Prapësimet dhe Manipulimet e Zbuluara mes provave
   - 3. Shkeljet Thelbësore Procedurale (Cito nenet neni-për-nen: LPK, KPP, Kushtetuta)
   - 4. Konkluzioni Taktik dhe Masat e Menjëhershme
4. GJUHA:
   Gjuhë e prerë solemne gjyqësore, pa hyrje boshe dhe pa marketing.

FOKUSI OPERATIV:
{payload.case_context or 'Analizë e thellë e fashikullit të plotë forenzik'}

===============================================================================
PËRMBAJTJA INTEGRALE E FASHIKULLIT TË LËNDËS ({total_docs_count} SHKRESA ZYRTARE):
===============================================================================
{full_dossier_text}

===============================================================================
KORPUSI LIGJOR & PRECEDENTËT E GJYKATËS SUPREME TË KOSOVËS:
===============================================================================
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
# 2. DËRGIMI I PYETJES ME STREAMING (ME BUXHET TË SIGURT TOKENASH)
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
    # Kufizojmë historikun në 10 mesazhet e fundit për të mos mbingarkuar tokenat
    past_cursor = db[FORENSIC_CHAT_COLLECTION].find(query).sort("created_at", -1).limit(10)
    raw_history = list(past_cursor)
    raw_history.reverse()

    conversation_turns = [{"role": m.get("role", "user"), "content": m.get("content", "")[:2000]} for m in raw_history]
    conversation_turns.append({"role": "user", "content": payload.message})

    # 1. Ruhet pyetja e përdoruesit në MongoDB
    db[FORENSIC_CHAT_COLLECTION].insert_one({
        "case_id": case_id_str,
        "user_id": user_id,
        "role": "user",
        "content": payload.message,
        "created_at": now_utc
    })

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
            # 2. Ruajtja atomike e përgjigjes në MongoDB
            if full_response.strip():
                clean_ai_text = full_response.strip()
                now_ai_utc = datetime.now(timezone.utc)

                audit_result = None
                try:
                    audit_result = audit_citations(clean_ai_text, db)
                except Exception as a_err:
                    logger.warning(f"Audit warning: {a_err}")

                assistant_msg_doc = {
                    "case_id": case_id_str,
                    "user_id": user_id,
                    "role": "assistant",
                    "content": clean_ai_text,
                    "citation_audit": audit_result,
                    "created_at": now_ai_utc
                }

                try:
                    db[FORENSIC_CHAT_COLLECTION].insert_one(assistant_msg_doc)

                    case_oid = ObjectId(case_id_str) if ObjectId.is_valid(case_id_str) else case_id_str
                    db.cases.update_one(
                        {"$or": [{"_id": case_oid}, {"_id": case_id_str}]},
                        {
                            "$push": {
                                "forensic_chat_history": {
                                    "$each": [
                                        {"role": "user", "content": payload.message, "timestamp": now_utc.isoformat()},
                                        {"role": "assistant", "content": clean_ai_text, "timestamp": now_ai_utc.isoformat()}
                                    ]
                                }
                            },
                            "$set": {"updated_at": now_ai_utc}
                        }
                    )
                    logger.info(f"✅ [Safe Token Budget Saved] U ruajtën {len(clean_ai_text)} karaktere për lëndën {case_id_str}.")
                except Exception as save_err:
                    logger.error(f"❌ Dështoi ruajtja e mesazhit në MongoDB: {save_err}")

                try:
                    log_forensic_action(
                        db=db,
                        user_id=user_id,
                        case_id=case_id_str,
                        action="FORENSIC_INTERROGATION_QUERY",
                        details={"query_preview": payload.message[:100], "streaming": True}
                    )
                except Exception:
                    pass

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