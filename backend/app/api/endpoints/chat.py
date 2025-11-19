from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated, Any
from pydantic import BaseModel
import json
import logging
from app.services import chat_service
from app.models.user import UserInDB
from app.api.endpoints.dependencies import get_current_active_user
from app.core.db import get_async_db, redis_sync_client

router = APIRouter(prefix="/chat", tags=["Chat"])
logger = logging.getLogger(__name__)

class ChatMessageRequest(BaseModel):
    message: str
class ChatResponse(BaseModel):
    response: str

@router.post("/case/{case_id}", response_model=ChatResponse)
async def handle_chat_message(case_id: str, chat_request: ChatMessageRequest, current_user: Annotated[UserInDB, Depends(get_current_active_user)], db: Any = Depends(get_async_db)):
    if not chat_request.message: raise HTTPException(status_code=400, detail="Empty message")
    try:
        response_text = await chat_service.get_http_chat_response(db=db, case_id=case_id, user_query=chat_request.message, user_id=str(current_user.id))
        try:
            channel = f"user:{current_user.id}:updates"
            payload = {"type": "CHAT_MESSAGE", "case_id": case_id, "content": response_text}
            redis_sync_client.publish(channel, json.dumps(payload))
        except Exception as e:
            logger.error(f"SSE Publish failed: {e}")
        return ChatResponse(response=response_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))