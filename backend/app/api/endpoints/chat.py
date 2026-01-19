# FILE: backend/app/api/endpoints/chat.py
# PHOENIX PROTOCOL - CHAT ROUTER V6.1 (SYNC DB ADAPTER)
# 1. FIX: Removed 'get_async_db' import. Uses 'get_db' (Sync).
# 2. STATUS: Resolves backend startup crash.

from fastapi import APIRouter, Depends, HTTPException, status, Response
from typing import Annotated, Any, Optional
from pydantic import BaseModel
import json
import logging
from bson import ObjectId
from pymongo.database import Database

from app.services import chat_service
from app.models.user import UserInDB
from app.api.endpoints.dependencies import get_current_active_user, get_db, get_redis_client
import redis

router = APIRouter(tags=["Chat"])
logger = logging.getLogger(__name__)

class ChatMessageRequest(BaseModel):
    message: str
    document_id: Optional[str] = None
    jurisdiction: Optional[str] = 'ks'
    mode: Optional[str] = "FAST"

class ChatResponse(BaseModel):
    response: str

@router.post("/case/{case_id}", response_model=ChatResponse)
async def handle_chat_message(
    case_id: str, 
    chat_request: ChatMessageRequest, 
    current_user: Annotated[UserInDB, Depends(get_current_active_user)], 
    db: Database = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    """
    Sends a message to the AI Case Chat.
    """
    if not chat_request.message: 
        raise HTTPException(status_code=400, detail="Empty message")
        
    try:
        # PHOENIX: Pass Sync DB. Service must handle it synchronously.
        response_text = await chat_service.get_http_chat_response(
            db=db, 
            case_id=case_id, 
            user_query=chat_request.message, 
            user_id=str(current_user.id),
            document_id=chat_request.document_id,
            jurisdiction=chat_request.jurisdiction,
            mode=chat_request.mode
        )
        
        # Publish to Redis (Sync client)
        try:
            channel = f"user:{current_user.id}:updates"
            payload = {
                "type": "CHAT_MESSAGE", 
                "case_id": case_id, 
                "content": response_text,
                "document_id": chat_request.document_id,
                "jurisdiction": chat_request.jurisdiction
            }
            redis_client.publish(channel, json.dumps(payload))
        except Exception as e:
            logger.warning(f"SSE Publish failed: {e}")
            
        return ChatResponse(response=response_text)
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Unhandled Chat API Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/case/{case_id}/history", status_code=status.HTTP_204_NO_CONTENT)
def clear_chat_history(
    case_id: str, 
    current_user: Annotated[UserInDB, Depends(get_current_active_user)], 
    db: Database = Depends(get_db)
):
    try:
        # Sync DB operation
        result = db.cases.update_one(
            {"_id": ObjectId(case_id), "owner_id": current_user.id},
            {"$set": {"chat_history": []}}
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Case not found or access denied.")
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        logger.error(f"Failed to clear chat history: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear chat history.")