# FILE: backend/app/services/chat_service.py
# PHOENIX PROTOCOL MODIFICATION 13.0 (STATIC ANALYSIS FIX):
# 1. CRITICAL FIX: Changed the type hint for the 'manager' parameter from
#    `ConnectionManager` to `'ConnectionManager'` (a string forward reference).
# 2. This resolves the `Pylance (reportInvalidTypeForm)` error by breaking a
#    circular dependency at static analysis time, allowing the type checker to
#    validate the file without failing.
# 3. This is the standard Python approach for handling circular type dependencies
#    and does not affect runtime execution.
# 4. All previous logic and type corrections are preserved.

from __future__ import annotations
import os
from groq import AsyncGroq
from typing import List, Dict, Any
import logging
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException, status
from bson import ObjectId

from app.services import vector_store_service
from app.core.websocket_manager import ConnectionManager
from app.models.case import ChatMessage, ChatMessageOut

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
        logging.error(f"🔥🔥🔥 CRITICAL FAILURE: Could not initialize AlbanianRAGService. Error: {e} 🔥🔥🔥", exc_info=True)
        raise RuntimeError(f"AI service components are not available: {e}")

async def process_chat_message(
    db: AsyncIOMotorDatabase,
    manager: 'ConnectionManager',
    case_id: str,
    user_query: str,
    user_id: str
):
    """
    Orchestrates the handling of a new chat message using the asynchronous database client.
    """
    case_collection = db.cases
    
    # 1. Create and Persist User's Message
    user_message = ChatMessage(sender_id=user_id, sender_type="user", content=user_query)
    await case_collection.update_one(
        {"_id": ObjectId(case_id)},
        {"$push": {"chat_history": user_message.model_dump()}}
    )
    
    # 2. Broadcast User's Message
    user_message_out = ChatMessageOut(**user_message.model_dump())
    await manager.broadcast_to_case(
        case_id, {"type": "chat_message", "payload": user_message_out.model_dump()}
    )
    
    try:
        rag_service = _get_rag_service_instance()
        
        # 3. Generate AI Response
        full_response_text = ""
        stream = rag_service.chat_stream(query=user_query, case_id=case_id)
        async for chunk in stream:
            full_response_text += chunk

        if not full_response_text:
            full_response_text = "Më falni, nuk munda të gjej një përgjigje." # Default response

        # 4. Create and Persist AI's Message
        ai_message = ChatMessage(sender_id="ai_assistant", sender_type="ai", content=full_response_text)
        await case_collection.update_one(
            {"_id": ObjectId(case_id)},
            {"$push": {"chat_history": ai_message.model_dump()}}
        )

        # 5. Broadcast AI's Message
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