# FILE: backend/app/services/chat_service.py
# PHOENIX PROTOCOL - STATIC ANALYSIS FIX
# 1. FIX: Removed global 'None' initializers to fix Pylance "Object cannot be called" error.
# 2. LOGIC: Scoped imports inside the factory function for type safety.
# 3. STATUS: Validated.

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
from app.services.graph_service import graph_service 
import app.services.vector_store_service as vector_store_service

logger = logging.getLogger(__name__)

def _get_rag_service_instance() -> Any:
    """
    Factory to get the RAG Service instance.
    Uses local imports to prevent circular dependency issues and static analysis errors.
    """
    # 1. Dynamic Imports (Scoped to this function to satisfy Pylance)
    try:
        from app.services.albanian_rag_service import AlbanianRAGService
        from app.services.albanian_language_detector import AlbanianLanguageDetector
    except ImportError as e:
        logger.error(f"❌ Critical Import Error in Chat Service: {e}")
        return None

    # 2. Config Check
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        logger.warning("⚠️ DEEPSEEK_API_KEY missing. AI features disabled.")
        return None

    # 3. Instantiation
    try:
        detector = AlbanianLanguageDetector()
        # Use a dummy client here, as RAG service will init its own OpenAI client based on config
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
    jurisdiction: Optional[str] = 'ks'
) -> str:
    """
    Orchestrates the Socratic Chat: Graph Check -> Vector Search -> LLM Answer.
    """
    try: oid = ObjectId(case_id)
    except InvalidId: raise HTTPException(status_code=400, detail="Invalid ID")

    # 1. Save User Message
    try:
        await db.cases.update_one(
            {"_id": oid},
            {"$push": {"chat_history": ChatMessage(role="user", content=user_query, timestamp=datetime.now(timezone.utc)).model_dump()}}
        )
    except Exception as e: logger.error(f"DB Write Error: {e}")
    
    # 2. Graph Intelligence Step (The "Detective")
    graph_context = ""
    try:
        # Check for contradictions or hidden flags in the graph
        contradictions = graph_service.find_contradictions(case_id)
        if contradictions and "No direct contradictions" not in contradictions:
            graph_context = f"\n\n[SISTEMI DETEKTIV - RAPORT NGA GRAPH DB]:\n{contradictions}\n(Përdore këtë informacion për të paralajmëruar përdoruesin nëse pyetja lidhet me besueshmërinë.)\n"
    except Exception as e:
        logger.warning(f"Graph Lookup Failed (Non-critical): {e}")

    # 3. AI Processing (RAG + Graph Context)
    response_text = ""
    try:
        rag_service = _get_rag_service_instance()
        if rag_service:
            # We transparently append Graph Intelligence to the user query context
            augmented_query = f"{user_query}{graph_context}"
            
            response_text = await rag_service.chat(
                query=augmented_query, 
                case_id=case_id, 
                document_ids=[document_id] if document_id else None,
                jurisdiction=jurisdiction
            )
        else:
            response_text = "Shërbimi AI nuk është i konfiguruar (Mungojnë modulet ose API Key)."
    except Exception as e:
        logger.error(f"AI Error: {e}")
        response_text = "Më vjen keq, pata një problem teknik gjatë përpunimit të përgjigjes."

    # 4. Save Response
    try:
        await db.cases.update_one(
            {"_id": oid},
            {"$push": {"chat_history": ChatMessage(role="ai", content=response_text, timestamp=datetime.now(timezone.utc)).model_dump()}}
        )
    except Exception: pass

    return response_text