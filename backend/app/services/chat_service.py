# FILE: backend/app/services/chat_service.py
# PHOENIX PROTOCOL - SYSTEM INTEGRITY RESTORATION
# 1. Added robust error handling for AI service initialization.
# 2. Added fallback response if AI is unavailable (prevents 500 crashes).
# 3. Validated ObjectId conversion.

from __future__ import annotations
import os
import logging
from datetime import datetime
# PHOENIX PROTOCOL CURE: Import 'Any' to permanently resolve linter errors.
from typing import Any, Optional

from fastapi import HTTPException
from bson import ObjectId
from bson.errors import InvalidId
from groq import AsyncGroq

from app.models.case import ChatMessage
# We keep the lazy import of vector_store_service to avoid circular dependencies
import app.services.vector_store_service as vector_store_service

logger = logging.getLogger(__name__)

def _get_rag_service_instance() -> Any:
    """
    Lazy loads the RAG service to prevent startup crashes if dependencies are missing.
    Returns None if initialization fails.
    """
    try:
        # Check API Key first
        groq_api_key = os.environ.get("GROQ_API_KEY")
        if not groq_api_key:
            logger.warning("⚠️ GROQ_API_KEY is missing. Chat functionality will be limited.")
            return None

        from app.services.albanian_rag_service import AlbanianRAGService
        from app.services.albanian_language_detector import AlbanianLanguageDetector
        
        language_detector_instance = AlbanianLanguageDetector()
        albanian_groq_client = AsyncGroq(api_key=groq_api_key)

        instance = AlbanianRAGService(
            vector_store=vector_store_service,
            llm_client=albanian_groq_client,
            language_detector=language_detector_instance
        )
        logging.info("✅ On-demand Albanian RAG Service initialized successfully.")
        return instance

    except ImportError as e:
        logger.error(f"❌ RAG Service Import Error (Missing Files?): {e}")
        return None
    except Exception as e:
        logger.error(f"❌ RAG Service Initialization Error: {e}", exc_info=True)
        return None

async def get_http_chat_response(
    db: Any, 
    case_id: str, 
    user_query: str, 
    user_id: str
) -> str:
    """
    Handles a chat query from a standard HTTP request. 
    Saves the user message, attempts to get an AI response, and saves the AI response.
    """
    # 1. Validate Case ID
    try:
        oid = ObjectId(case_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid Case ID format.")

    case_collection = db.cases
    
    # 2. Save User Message (Commit to DB first so we don't lose the user's input)
    try:
        user_message = ChatMessage(
            sender_id=user_id, 
            sender_type="user", 
            content=user_query,
            timestamp=datetime.utcnow()
        )
        await case_collection.update_one(
            {"_id": oid},
            {"$push": {"chat_history": user_message.model_dump()}}
        )
    except Exception as e:
        logger.error(f"Failed to save user message to DB: {e}")
        raise HTTPException(status_code=500, detail="Database write failed.")

    # 3. Attempt AI Generation
    full_response_text = ""
    try:
        rag_service = _get_rag_service_instance()
        
        if rag_service and hasattr(rag_service, 'chat'):
            full_response_text = await rag_service.chat(query=user_query, case_id=case_id)
        else:
            # Fallback if service is down/misconfigured
            logger.warning("RAG Service unavailable, returning fallback message.")
            full_response_text = (
                "Sistemi AI aktualisht nuk është i disponueshëm (API Key ose shërbimi mungon). "
                "Ju lutemi provoni përsëri më vonë."
            )

        if not full_response_text:
            full_response_text = "Më falni, nuk munda të gjej një përgjigje."

    except Exception as e:
        logger.error(f"AI Generation failed for case {case_id}: {e}", exc_info=True)
        full_response_text = "Ndodhi një gabim gjatë gjenerimit të përgjigjes. Ju lutemi provoni përsëri."

    # 4. Save AI Response
    try:
        ai_message = ChatMessage(
            sender_id="ai_assistant", 
            sender_type="ai", 
            content=full_response_text,
            timestamp=datetime.utcnow()
        )
        await case_collection.update_one(
            {"_id": oid},
            {"$push": {"chat_history": ai_message.model_dump()}}
        )
    except Exception as e:
        logger.error(f"Failed to save AI response to DB: {e}")
        # We don't raise here because we successfully got a response, even if saving failed logic-wise.
        # But to be safe for the UI, we return the text.

    return full_response_text