# FILE: backend/app/api/endpoints/chat.py
# PHOENIX PROTOCOL - CHAT ROUTER V7.4 (INFRASTRUCTURE INTEGRITY)
# 1. FIX: Injected 'X-Accel-Buffering' and 'Cache-Control' headers to bypass Proxy buffering.
# 2. STATUS: Fully synchronized with chat_service.py and albanian_rag_service.py.

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from typing import Annotated, Optional
from pydantic import BaseModel
import logging
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
            mode=chat_request.mode
        )
        
        # PHOENIX FIX: Mandatory Anti-Buffering Headers for Caddy/Nginx
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