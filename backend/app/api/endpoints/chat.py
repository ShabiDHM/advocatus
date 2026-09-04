# FILE: backend/app/api/endpoints/chat.py
# PHOENIX PROTOCOL - CHAT ROUTER V55.0 (TOTAL CERTIFIED CASCADE WIPEOUT • MONGO & REDIS FLUSH)

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from typing import Annotated, Optional, List, Literal, Dict, Any
from pydantic import BaseModel
import logging
from datetime import datetime, timezone
from pymongo.database import Database
from bson import ObjectId
import redis

from app.services import chat_service
from app.models.user import UserInDB
from app.api.endpoints.dependencies import get_current_active_user, get_db, get_sync_redis

router = APIRouter(tags=["Chat"])
logger = logging.getLogger(__name__)

class ChatMessageRequest(BaseModel):
    message: str
    document_ids: Optional[List[str]] = None
    jurisdiction: Optional[str] = 'ks'
    domain: Optional[str] = 'automatic'

class ChatFeedbackRequest(BaseModel):
    message_index: int
    feedback: Literal["up", "down"]

@router.post("/case/{case_id}")
async def handle_chat_message(
    case_id: str, 
    chat_request: ChatMessageRequest, 
    current_user: Annotated[UserInDB, Depends(get_current_active_user)], 
    db: Database = Depends(get_db)
):
    if not chat_request.message: 
        raise HTTPException(status_code=400, detail="Mesazhi është i zbrazët.")
        
    try:
        generator = chat_service.stream_chat_response(
            db=db, 
            case_id=case_id, 
            user_query=chat_request.message, 
            user_id=str(current_user.id),
            document_ids=chat_request.document_ids,
            jurisdiction=chat_request.jurisdiction,
            domain=chat_request.domain
        )
        
        headers = {
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream; charset=utf-8"
        }
        
        return StreamingResponse(
            generator,
            media_type="text/event-stream",
            headers=headers
        )
        
    except Exception as e:
        logger.error(f"Chat Router Failure: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ndodhi një gabim në shërbimin e bisedës.")


# =========================================================================
# 🧹 TOTAL CERTIFIED CASCADE WIPEOUT (MONGO ATLAS, REDIS & DOCUMENT CACHE)
# =========================================================================
@router.delete("/case/{case_id}/history", status_code=status.HTTP_200_OK)
def clear_chat_history(
    case_id: str, 
    current_user: Annotated[UserInDB, Depends(get_current_active_user)], 
    db: Database = Depends(get_db),
    redis_client: redis.Redis = Depends(get_sync_redis)
):
    """
    TOTAL CERTIFIED CASCADE WIPEOUT:
    1. Pastron historikun e bisedës në MongoDB.
    2. Fshin $unset të gjitha analizat (latest_deep_analysis, latest_comprehensive_analysis, latest_analysis).
    3. Fshin analizat e ruajtura nga të gjithë dokumentet e asaj lënde.
    4. Vendos analysis_dirty = True (detyrim i rreptë për analizë nga e para).
    5. Fshin të gjithë çelësat e memories së shpejtë në REDIS CLOUD.
    """
    try:
        c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
        
        # 1. Pastrim Total në MongoDB (Case Record)
        db.cases.update_one(
            {"_id": c_oid, "owner_id": current_user.id},
            {
                "$set": {
                    "chat_history": [],
                    "analysis_dirty": True,
                    "updated_at": datetime.now(timezone.utc)
                },
                "$unset": {
                    "latest_deep_analysis": "",
                    "latest_comprehensive_analysis": "",
                    "latest_analysis": "",
                    "latest_forensic_audit": "",
                    "summary": "",
                    "case_summary": ""
                }
            }
        )

        # 2. Pastrim Total në të gjitha Dokumentet e kësaj Lënde
        db.documents.update_many(
            {"$or": [{"case_id": case_id}, {"case_id": c_oid}]},
            {
                "$unset": {
                    "latest_analysis": "",
                    "latest_forensic_audit": "",
                    "last_audited_at": ""
                }
            }
        )

        # 3. Pastrim Total në REDIS CLOUD
        if redis_client:
            try:
                redis_keys = [
                    f"case:{case_id}:analysis",
                    f"case:{case_id}:summary",
                    f"case:{case_id}:chat",
                    f"rag:{case_id}:context"
                ]
                for rk in redis_keys:
                    redis_client.delete(rk)
                logger.info(f"✅ [Redis Flush] U fshinë çelësat e memories për lëndën {case_id}.")
            except Exception as r_err:
                logger.warning(f"Redis cache delete warning: {r_err}")

        logger.info(f"🧹 [TOTAL CERTIFIED CASCADE WIPEOUT] Çdo gjurmë e vjetër u asgjësua për lëndën {case_id}.")
        return {"status": "success", "message": "Fshirja me kaskadë u ekzekutua 100% në të gjitha nivelet e sistemit."}
        
    except Exception as e:
        logger.error(f"Failed to clear history with cascade wipeout: {e}")
        raise HTTPException(status_code=500, detail="Dështoi pastrimi me kaskadë.")


@router.post("/case/{case_id}/feedback")
async def submit_chat_feedback(
    case_id: str,
    feedback_request: ChatFeedbackRequest,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    db: Database = Depends(get_db)
):
    try:
        case = db.cases.find_one({"_id": ObjectId(case_id), "owner_id": current_user.id})
        if not case:
            raise HTTPException(status_code=404, detail="Lënda nuk u gjet.")
        
        chat_history = case.get("chat_history", [])
        if feedback_request.message_index < 0 or feedback_request.message_index >= len(chat_history):
            raise HTTPException(status_code=400, detail="Indeksi i mesazhit është i pasaktë.")
        
        message = chat_history[feedback_request.message_index]
        feedback_doc = {
            "case_id": case_id,
            "user_id": str(current_user.id),
            "message_index": feedback_request.message_index,
            "feedback": feedback_request.feedback,
            "message_preview": message.get("content", "")[:200],
            "created_at": datetime.now(timezone.utc)
        }
        db.chat_feedback.insert_one(feedback_doc)
        
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Feedback submission failed: {e}")
        raise HTTPException(status_code=500, detail="Dështoi dërgimi i vlerësimit.")