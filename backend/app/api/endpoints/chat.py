# FILE: backend/app/api/endpoints/chat.py
# DEFINITIVE VERSION 8.2 (CRITICAL FIX: TYPE CONVERSION)
# 1. CRITICAL FIX: Explicitly cast 'current_user.id' from PyObjectId to str when passing it to the chat_service function,
#    resolving the Pylance/TypeScript type mismatch error.
# 2. All previous functional and architectural fixes are preserved.

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated, Optional
from pydantic import BaseModel
from pymongo.database import Database
from bson import ObjectId
from bson.errors import InvalidId
import logging

from ...services import chat_service, case_service
from ...models.user import UserInDB
from .dependencies import get_current_active_user, get_db

router = APIRouter(prefix="/chat", tags=["Chat"])

class ChatRequest(BaseModel):
    message: str
    document_id: Optional[str] = None # Retained for future filtering/RAG context

@router.post("/case/{case_id}", status_code=status.HTTP_200_OK)
async def handle_chat_message(
    case_id: str,
    chat_request: ChatRequest,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    db: Database = Depends(get_db)
):
    """
    Handles all chat messages for a given case.
    The response generation is now fully asynchronous.
    """
    try:
        validated_case_id = ObjectId(case_id)
        
        # Simplified to a direct synchronous call for the MongoDB lookup.
        case = case_service.get_case_by_id(db, validated_case_id, current_user)
        
        if not case:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found or access denied.")

        # FIX: Aligned service function name and arguments to match chat_service.get_chat_response
        response = await chat_service.get_chat_response(
            db=db,
            user_query=chat_request.message,
            case_id=case_id,
            # NOTE: Assuming an empty history for the first query in this implementation
            chat_history=[],
            # CRITICAL FIX: Explicitly cast current_user.id to str to match function signature
            user_id=str(current_user.id) 
        )
        
        # The response structure from get_chat_response is {"response": str, "citation": str | None}
        return {"message": response["response"], "citation": response["citation"]}
        
    except InvalidId:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Case or Document ID format.")
    except HTTPException:
        # Re-raise explicit HTTP exceptions (e.g., 404, 503)
        raise
    except Exception as e:
        logging.error(f"Unhandled error in chat endpoint for case {case_id}: {e}", exc_info=True)
        
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An internal error occurred in the chat service.")