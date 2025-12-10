# FILE: backend/app/services/chat_service.py
# PHOENIX PROTOCOL - CHAT SERVICE V6.0 (TRIPLE-CONTEXT RAG)
# 1. UPGRADE: Now injects structured 'Findings' into the AI context for high-value answers.
# 2. RAG STRATEGY: Combines Graph Intelligence + Findings DB + Vector Search.
# 3. CONTEXT: Builds a "Case Dossier" to give the LLM a deep understanding of the case.

from __future__ import annotations
import os
import logging
from datetime import datetime, timezone
from typing import Any, Optional, List, Dict

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
    """
    try:
        from app.services.albanian_rag_service import AlbanianRAGService
        from app.services.albanian_language_detector import AlbanianLanguageDetector
    except ImportError as e:
        logger.error(f"❌ Critical Import Error in Chat Service: {e}")
        return None

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        logger.warning("⚠️ DEEPSEEK_API_KEY missing. AI features disabled.")
        return None

    try:
        detector = AlbanianLanguageDetector()
        dummy_client = AsyncOpenAI(api_key="dummy") 
        
        return AlbanianRAGService(
            vector_store=vector_store_service,
            llm_client=dummy_client,
            language_detector=detector
        )
    except Exception as e:
        logger.error(f"❌ RAG Init Failed: {e}", exc_info=True)
        return None

async def _build_context_dossier(db: Any, case_id: str) -> str:
    """
    Constructs a rich context summary by querying findings and graph data.
    """
    context_parts = []
    
    # 1. Fetch Key Findings
    try:
        # Find findings for this case, limit to the 7 most recent/relevant.
        findings_cursor = db.findings.find(
            {"case_id": {"$in": [ObjectId(case_id), case_id]}}
        ).sort("created_at", -1).limit(7)
        
        findings: List[Dict] = await findings_cursor.to_list(length=7)
        
        if findings:
            findings_text = "\n".join([
                f"- [{f.get('category', 'FAKT')}]: {f.get('finding_text', 'N/A')}"
                for f in findings
            ])
            context_parts.append(f"DOSJA E RASTIT (Gjetjet Kryesore):\n{findings_text}")
            
    except Exception as e:
        logger.warning(f"Findings lookup for chat failed: {e}")

    # 2. Fetch Graph Intelligence
    try:
        contradictions = graph_service.find_contradictions(case_id)
        if contradictions and "No direct contradictions" not in contradictions:
            context_parts.append(f"INTELIGJENCA E GRAFIT (Kontradiktat e Mundshme):\n{contradictions}")
    except Exception as e:
        logger.warning(f"Graph lookup for chat failed: {e}")

    if not context_parts:
        return ""
        
    # Combine into a single block
    header = "[SISTEMI R-A-G: Ky informacion i brendshëm i jep kontekst AI-së. Mos ia shfaq përdoruesit.]"
    return f"\n\n{header}\n" + "\n\n".join(context_parts) + "\n[FUNDI I KONTEKSTIT TË SISTEMIT]\n\n"

async def get_http_chat_response(
    db: Any, 
    case_id: str, 
    user_query: str, 
    user_id: str,
    document_id: Optional[str] = None,
    jurisdiction: Optional[str] = 'ks'
) -> str:
    """
    Orchestrates the Socratic Chat using the Triple-Context RAG model.
    """
    try:
        oid = ObjectId(case_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid Case ID")

    # 1. Save User Message
    try:
        await db.cases.update_one(
            {"_id": oid},
            {"$push": {"chat_history": ChatMessage(role="user", content=user_query, timestamp=datetime.now(timezone.utc)).model_dump()}}
        )
    except Exception as e:
        logger.error(f"DB Write Error (User Message): {e}")
    
    # 2. Build High-Value Context Dossier
    context_dossier = await _build_context_dossier(db, case_id)
    
    # 3. AI Processing (RAG with Enhanced Context)
    response_text = ""
    try:
        rag_service = _get_rag_service_instance()
        if rag_service:
            # Augment the user's query with our deep context dossier
            augmented_query = f"{context_dossier}{user_query}"
            
            response_text = await rag_service.chat(
                query=augmented_query, 
                case_id=case_id, 
                document_ids=[document_id] if document_id else None,
                jurisdiction=jurisdiction
            )
        else:
            response_text = "Shërbimi AI nuk është i konfiguruar (Mungojnë modulet ose API Key)."
    except Exception as e:
        logger.error(f"AI Processing Error: {e}", exc_info=True)
        response_text = "Më vjen keq, pata një problem teknik gjatë përpunimit të përgjigjes."

    # 4. Save AI Response
    try:
        await db.cases.update_one(
            {"_id": oid},
            {"$push": {"chat_history": ChatMessage(role="ai", content=response_text, timestamp=datetime.now(timezone.utc)).model_dump()}}
        )
    except Exception as e:
        logger.error(f"DB Write Error (AI Response): {e}")

    return response_text