# FILE: backend/app/services/chat_service.py

from __future__ import annotations
import os
from groq import AsyncGroq
# PHOENIX PROTOCOL CURE: Import 'Any' to permanently resolve linter errors.
from typing import Any
import logging
from fastapi import HTTPException
from bson import ObjectId

from app.services import vector_store_service
from app.models.case import ChatMessage, ChatMessageOut
from app.core.websocket_manager import ConnectionManager
from app.models.user import UserInDB

logger = logging.getLogger(__name__)

def _get_rag_service_instance() -> Any:
    try:
        from app.services.albanian_rag_service import AlbanianRAGService
        from app.services.albanian_language_detector import AlbanianLanguageDetector
        
        language_detector_instance = AlbanianLanguageDetector()
        groq_api_key = os.environ.get("GROQ_API_KEY")
        if not groq_api_key: raise ValueError("GROQ_API_KEY is not set in environment.")
        albanian_groq_client = AsyncGroq(api_key=groq_api_key)

        instance = AlbanianRAGService(
            vector_store=vector_store_service,
            llm_client=albanian_groq_client,
            language_detector=language_detector_instance
        )
        logging.info("✅ On-demand Albanian RAG Service initialized successfully.")
        return instance
    except (ImportError, Exception, ValueError) as e:
        log_message = f"🔥🔥🔥 CRITICAL FAILURE: Could not initialize AlbanianRAGService. Error: {e} 🔥🔥🔥"
        logging.error(log_message, exc_info=True)
        raise RuntimeError(f"AI service components are not available: {e}")

async def get_http_chat_response(
    # PHOENIX PROTOCOL CURE: Use Any for the db type to satisfy Pylance.
    db: Any, 
    case_id: str, 
    user_query: str, 
    user_id: str
) -> str:
    """
    Handles a chat query from a standard HTTP request. Returns a single, complete string response.
    """
    case_collection = db.cases
    
    user_message = ChatMessage(sender_id=user_id, sender_type="user", content=user_query)
    await case_collection.update_one(
        {"_id": ObjectId(case_id)},
        {"$push": {"chat_history": user_message.model_dump()}}
    )

    try:
        rag_service = _get_rag_service_instance()
        
        if not hasattr(rag_service, 'chat'):
            raise NotImplementedError("The configured RAG service does not support non-streaming chat.")
        
        full_response_text = await rag_service.chat(query=user_query, case_id=case_id)

        if not full_response_text:
            full_response_text = "Më falni, nuk munda të gjej një përgjigje."

        ai_message = ChatMessage(sender_id="ai_assistant", sender_type="ai", content=full_response_text)
        await case_collection.update_one(
            {"_id": ObjectId(case_id)},
            {"$push": {"chat_history": ai_message.model_dump()}}
        )
        return full_response_text
    except Exception as e:
        logger.error(f"Unhandled error in get_http_chat_response for case {case_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while processing the chat response.")

async def process_chat_message(
    # PHOENIX PROTOCOL CURE: Use Any for the db type to satisfy Pylance.
    db: Any,
    manager: ConnectionManager,
    case_id: str,
    user_query: str,
    user_id: str
):
    """Handles a chat query from a WebSocket connection, streaming the response."""
    case_collection = db.cases
    
    user_message = ChatMessage(sender_id=user_id, sender_type="user", content=user_query)
    await case_collection.update_one(
        {"_id": ObjectId(case_id)},
        {"$push": {"chat_history": user_message.model_dump()}}
    )
    
    user_message_out = ChatMessageOut(**user_message.model_dump())
    await manager.broadcast_to_case(
        case_id, {"type": "chat_message_out", "payload": user_message_out.model_dump()}
    )
    
    try:
        rag_service = _get_rag_service_instance()
        
        full_response_text = ""
        stream = rag_service.chat_stream(query=user_query, case_id=case_id)
        async for chunk in stream:
            full_response_text += chunk
            await manager.broadcast_to_case(case_id, {"type": "chat_response_chunk", "text": chunk})

        if not full_response_text:
            full_response_text = "Më falni, nuk munda të gjej një përgjigje."

        ai_message = ChatMessage(sender_id="ai_assistant", sender_type="ai", content=full_response_text)
        await case_collection.update_one(
            {"_id": ObjectId(case_id)},
            {"$push": {"chat_history": ai_message.model_dump()}}
        )

    except (RuntimeError, HTTPException) as e:
        error_detail = e.detail if isinstance(e, HTTPException) else str(e)
        error_message = ChatMessageOut(sender_id="system_error", sender_type="ai", content=f"An error occurred: {error_detail}")
        await manager.broadcast_to_case(case_id, {"type": "error", "payload": error_message.model_dump()})
    except Exception as e:
        logger.error(f"Unhandled error in process_chat_message for case {case_id}: {e}", exc_info=True)
        error_message = ChatMessageOut(sender_id="system_error", sender_type="ai", content="An unexpected internal error occurred.")
        await manager.broadcast_to_case(
            case_id, {"type": "error", "payload": error_message.model_dump()}
        )