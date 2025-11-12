# FILE: backend/app/api/endpoints/chat.py

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated, Any
from pydantic import BaseModel
import asyncio

# PHOENIX PROTOCOL CURE: Switched to absolute imports to resolve all linter path errors.
from app.services import chat_service
from app.models.user import UserInDB
from app.api.endpoints.dependencies import get_current_active_user
from app.core.db import get_async_db

router = APIRouter(prefix="/chat", tags=["Chat"])

class ChatRequest(BaseModel):
    case_id: str
    message: str

class ChatResponse(BaseModel):
    response: str

@router.post("", response_model=ChatResponse, include_in_schema=False)
@router.post("/", response_model=ChatResponse)
async def handle_http_chat(
    chat_request: ChatRequest,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    # PHOENIX PROTOCOL CURE: Use 'Any' to definitively solve the final Pylance error.
    db: Any = Depends(get_async_db)
):
    """
    Handles a single, non-streaming chat interaction over HTTP.
    """
    if not chat_request.message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message cannot be empty."
        )

    try:
        response_text = await chat_service.get_http_chat_response(
            db=db,
            case_id=chat_request.case_id,
            user_query=chat_request.message,
            user_id=str(current_user.id)
        )
        return ChatResponse(response=response_text)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )