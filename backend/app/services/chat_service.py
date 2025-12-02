# FILE: backend/app/services/chat_service.py
# PHOENIX PROTOCOL - JURISDICTION SUPPORT (SERVICE LAYER)
# 1. SCOPE: 'get_http_chat_response' now accepts and passes 'jurisdiction'.
# 2. RAG INTEGRATION: The RAG engine will now receive the jurisdictional context.

from __future__ import annotations
import os
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import HTTPException
from bson import ObjectId
from bson.errors import InvalidId
from openai import AsyncOpenAI

from app.models.case import ChatMessage
import app.services.vector_store_service as vector_store_service

logger = logging.getLogger(__name__)

# --- DYNAMIC IMPORTS ---
AlbanianRAGService = None
AlbanianLanguageDetector = None

def _load_rag_dependencies():
    global AlbanianRAGService, AlbanianLanguageDetector
    if AlbanianRAGService is None:
        try:
            from app.services.albanian_rag_service import AlbanianRAGService
            from app.services.albanian_language_detector import AlbanianLanguageDetector
        except ImportError as e:
            logger.error(f"❌ Critical Import Error in Chat Service: {e}")

def _get_rag_service_instance() -> Any:
    _load_rag_dependencies()
    
    if AlbanianRAGService is None or AlbanianLanguageDetector is None:
        logger.error("❌ RAG Service or Language Detector Class is missing.")
        return None

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        logger.warning("⚠️ DEEPSEEK_API_KEY missing. AI features disabled.")
        return None

    try:
        detector = AlbanianLanguageDetector()
        # Use a dummy client here, as RAG service will init its own OpenAI client
        dummy_client = AsyncOpenAI(api_key="dummy") 
        
        return AlbanianRAGService(
            vector_store=vector_store_service,
            llm_client=dummy_client,
            language_detector=detector
        )
    except Exception as e:
        logger.error(f"❌ RAG Init Failed: {e}", exc_info=True)
        return None

async def get_http_chat_response(
    db: Any, 
    case_id: str, 
    user_query: str, 
    user_id: str,
    document_id: Optional[str] = None,
    jurisdiction: Optional[str] = 'ks' # PHOENIX FIX: Added param
) -> str:
    """
    Orchestrates the chat flow with scope and jurisdiction.
    """
    logger.info(f"💬 Chat Request: Case[{case_id}] Doc[{document_id or 'ALL'}] Jur[{jurisdiction}]")

    # 1. Validation
    try:
        oid = ObjectId(case_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid Case ID format.")

    # 2. Check Case Existence
    case = await db.cases.find_one({"_id": oid})
    if not case:
        logger.warning(f"⚠️ Chat attempted on missing case: {case_id}")
        raise HTTPException(status_code=404, detail="Case not found.")
    
    # 3. Save User Message
    try:
        user_message = ChatMessage(
            role="user",
            content=user_query,
            timestamp=datetime.now(timezone.utc)
        )
        await db.cases.update_one(
            {"_id": oid},
            {"$push": {"chat_history": user_message.model_dump()}}
        )
    except Exception as e:
        logger.error(f"❌ Database Write Error (User Message): {e}")
    
    # 4. AI Processing
    response_text = ""
    try:
        rag_service = _get_rag_service_instance()
        
        if rag_service:
            target_docs = [document_id] if document_id else None
            
            # PHOENIX FIX: Pass jurisdiction to RAG
            response_text = await rag_service.chat(
                query=user_query, 
                case_id=case_id, 
                document_ids=target_docs,
                jurisdiction=jurisdiction
            )
        else:
            response_text = "Shërbimi AI aktualisht nuk është i qasshëm (Missing Configuration)."

    except Exception as e:
        logger.error(f"❌ AI Generation Error: {e}", exc_info=True)
        response_text = "Ndodhi një gabim teknik gjatë përpunimit. Ju lutemi provoni përsëri."

    # 5. Save AI Response
    try:
        ai_message = ChatMessage(
            role="ai", 
            content=response_text,
            timestamp=datetime.now(timezone.utc)
        )
        await db.cases.update_one(
            {"_id": oid},
            {"$push": {"chat_history": ai_message.model_dump()}}
        )
    except Exception as e:
         logger.error(f"❌ Database Write Error (AI Message): {e}")

    return response_text