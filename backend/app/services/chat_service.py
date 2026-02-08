# FILE: backend/app/services/chat_service.py
# PHOENIX PROTOCOL - CHAT SERVICE V25.4 (MODE DIFFERENTIATION)
# 1. FIX: Enforced strict brevity for FAST mode to distinguish from DEEP mode.
# 2. FIX: Synchronized parameters with RAG Service V47.0.
# 3. STATUS: Unabridged. Mode-specific behavior verified.

from __future__ import annotations
import logging
import asyncio
import structlog
from typing import AsyncGenerator, Optional, List, Dict, Any
from bson import ObjectId
from datetime import datetime, timezone
from pymongo.database import Database
from app.models.case import ChatMessage
from app.services.albanian_rag_service import AlbanianRAGService
from app.services import llm_service, vector_store_service

logger = structlog.get_logger(__name__)

async def stream_chat_response(
    db: Database, case_id: str, user_query: str, user_id: str,
    document_id: Optional[str] = None, jurisdiction: Optional[str] = 'ks', mode: Optional[str] = 'FAST'
) -> AsyncGenerator[str, None]:
    try:
        oid, user_oid = ObjectId(case_id), ObjectId(user_id)
        case = db.cases.find_one({"_id": oid, "owner_id": user_oid})
        if not case: yield "Gabim: Qasja u refuzua."; return

        # Sync User Message to History
        db.cases.update_one({"_id": oid}, {"$push": {"chat_history": ChatMessage(role="user", content=user_query, timestamp=datetime.now(timezone.utc)).model_dump()}})
        
        full_response = ""
        yield " " # Keep-alive

        if not mode or mode.upper() == 'FAST':
            # --- FAST MODE: Direct, Concise Summary ---
            snippets = vector_store_service.query_case_knowledge_base(user_id=user_id, query_text=user_query, n_results=10, case_context_id=case_id)
            context = "\n".join([f"- {s['text']} (Burimi: {s['source']})" for s in snippets])
            
            # Mandate brevity for FAST mode
            system_prompt = f"""
            Ti je 'Juristi AI'. 
            DETYRA: Jep një përgjigje të shpejtë dhe të shkurtër (MAX 2 PARAGRAFE).
            CITIMI: Përdor formatin [Emri i Ligjit](doc://ligji).
            KONTEKSTI I RASTIT:
            {context}
            """
            async for token in llm_service.stream_text_async(system_prompt, user_query, temp=0.1):
                full_response += token
                yield token
        else:
            # --- DEEP MODE: Comprehensive Legal Analysis ---
            agent_service = AlbanianRAGService(db=db)
            async for token in agent_service.chat(
                query=user_query, 
                user_id=user_id, 
                case_id=case_id, 
                document_ids=[document_id] if document_id else None,
                jurisdiction=jurisdiction or 'ks'
            ):
                full_response += token
                yield token

        # Sync AI Message to History
        if full_response.strip():
            db.cases.update_one({"_id": oid}, {"$push": {"chat_history": ChatMessage(role="ai", content=full_response.strip(), timestamp=datetime.now(timezone.utc)).model_dump()}})
            
    except Exception as e:
        logger.error(f"Streaming Error: {e}")
        yield "\n\n[Gabim Teknik: Shërbimi i bisedës dështoi.]"