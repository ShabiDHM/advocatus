# FILE: backend/app/services/chat_service.py

from __future__ import annotations
import os
from groq import AsyncGroq
from typing import Any
import logging
from fastapi import HTTPException
from bson import ObjectId

from app.services import vector_store_service
from app.models.case import ChatMessage, ChatMessageOut
from app.core.websocket_manager import ConnectionManager

logger = logging.getLogger(__name__)

def _get_rag_service_instance() -> Any:
    try:
        from .albanian_rag_service import AlbanianRAGService
        from .albanian_language_detector import AlbanianLanguageDetector
        
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

async def process_chat_message(
    # PHOENIX PROTOCOL CURE: Use 'Any' to definitively solve Pylance errors.
    db: Any,
    manager: ConnectionManager,
    case_id: str,
    user_query: str,
    user_id: str
):
    case_collection = db.cases
    
    user_message = ChatMessage(sender_id=user_id, sender_type="user", content=user_query)
    await case_collection.update_one(
        {"_id": ObjectId(case_id)},
        {"$push": {"chat_history": user_message.model_dump()}}
    )
    
    user_message_out = ChatMessageOut(**user_message.model_dump())
    await manager.broadcast_to_case(
        case_id, {"type": "chat_message", "payload": user_message_out.model_dump()}
    )
    
    try:
        rag_service = _get_rag_service_instance()
        
        full_response_text = ""
        stream = rag_service.chat_stream(query=user_query, case_id=case_id)
        async for chunk in stream:
            full_response_text += chunk

        if not full_response_text:
            full_response_text = "Më falni, nuk munda të gjej një përgjigje."

        ai_message = ChatMessage(sender_id="ai_assistant", sender_type="ai", content=full_response_text)
        await case_collection.update_one(
            {"_id": ObjectId(case_id)},
            {"$push": {"chat_history": ai_message.model_dump()}}
        )

        ai_message_out = ChatMessageOut(**ai_message.model_dump())
        await manager.broadcast_to_case(
            case_id, {"type": "chat_message", "payload": ai_message_out.model_dump()}
        )

    except (RuntimeError, HTTPException) as e:
        error_detail = e.detail if isinstance(e, HTTPException) else str(e)
        logger.error(f"Chat failed for case {case_id} due to service error: {error_detail}")
        error_message = ChatMessageOut(sender_id="system_error", sender_type="ai", content=f"An error occurred: {error_detail}")
        await manager.broadcast_to_case(case_id, {"type": "error", "payload": error_message.model_dump()})
    except Exception as e:
        logger.error(f"Unhandled error in process_chat_message for case {case_id}: {e}", exc_info=True)
        error_message = ChatMessageOut(sender_id="system_error", sender_type="ai", content="An unexpected internal error occurred.")
        await manager.broadcast_to_case(
            case_id, {"type": "error", "payload": error_message.model_dump()}
        )