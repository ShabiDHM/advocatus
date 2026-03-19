# FILE: backend/app/api/endpoints/chat.py
# PHOENIX PROTOCOL - CHAT ROUTER V7.6 (ADDED DOMAIN PARAMETER)
# 1. ADDED: domain field to ChatMessageRequest for deep mode customisation.
# 2. RETAINED: All previous functionality.

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from typing import Annotated, Optional, Literal
from pydantic import BaseModel
import logging
from datetime import datetime
from pymongo.database import Database

from app.services import chat_service
from app.models.user import UserInDB
from app.api.endpoints.dependencies import get_current_active_user, get_db

router = APIRouter(tags=["Chat"])
logger = logging.getLogger(__name__)

class ChatMessageRequest(BaseModel):
    message: str
    document_id: Optional[str] = None
    jurisdiction: Optional[str] = 'ks'
    mode: Optional[str] = "FAST"
    domain: Optional[str] = 'automatic'  # NEW: legal domain for deep mode

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
    """
    Sends a message to the AI Case Chat and returns a real-time stream.
    """
    if not chat_request.message: 
        raise HTTPException(status_code=400, detail="Mesazhi është i zbrazët.")
        
    try:
        # Generate the stream via the Chat Service
        generator = chat_service.stream_chat_response(
            db=db, 
            case_id=case_id, 
            user_query=chat_request.message, 
            user_id=str(current_user.id),
            document_id=chat_request.document_id,
            jurisdiction=chat_request.jurisdiction,
            mode=chat_request.mode,
            domain=chat_request.domain  # NEW: pass domain to service
        )
        
        headers = {
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/plain; charset=utf-8"
        }
        
        return StreamingResponse(
            generator,
            media_type="text/plain",
            headers=headers
        )
        
    except Exception as e:
        logger.error(f"Chat Router Failure: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ndodhi një gabim në shërbimin e bisedës.")

@router.delete("/case/{case_id}/history", status_code=status.HTTP_204_NO_CONTENT)
def clear_chat_history(
    case_id: str, 
    current_user: Annotated[UserInDB, Depends(get_current_active_user)], 
    db: Database = Depends(get_db)
):
    from bson import ObjectId
    try:
        result = db.cases.update_one(
            {"_id": ObjectId(case_id), "owner_id": current_user.id},
            {"$set": {"chat_history": []}}
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Rasti nuk u gjet.")
    except Exception as e:
        logger.error(f"Failed to clear history: {e}")
        raise HTTPException(status_code=500, detail="Dështoi fshirja e historisë.")

@router.post("/case/{case_id}/feedback")
async def submit_chat_feedback(
    case_id: str,
    feedback_request: ChatFeedbackRequest,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    db: Database = Depends(get_db)
):
    """Submit feedback for a specific chat message."""
    from bson import ObjectId
    try:
        # Verify case exists and belongs to user
        case = db.cases.find_one({"_id": ObjectId(case_id), "owner_id": current_user.id})
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        
        # Ensure the message index is within range
        chat_history = case.get("chat_history", [])
        if feedback_request.message_index < 0 or feedback_request.message_index >= len(chat_history):
            raise HTTPException(status_code=400, detail="Invalid message index")
        
        # Store feedback in a separate collection
        message = chat_history[feedback_request.message_index]
        feedback_doc = {
            "case_id": case_id,
            "user_id": str(current_user.id),
            "message_index": feedback_request.message_index,
            "feedback": feedback_request.feedback,
            "message_preview": message.get("content", "")[:200],
            "created_at": datetime.utcnow()
        }
        db.chat_feedback.insert_one(feedback_doc)
        
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Feedback submission failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit feedback")