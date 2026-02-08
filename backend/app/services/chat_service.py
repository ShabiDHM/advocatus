# FILE: backend/app/services/chat_service.py
# PHOENIX PROTOCOL - CHAT SERVICE V25.3 (PARAMETER ALIGNMENT)
# 1. FIX: Added 'jurisdiction' pass-through to Deep Mode streaming call.
# 2. FIX: Hardened FAST mode prompt to ensure law citations are preserved.
# 3. STATUS: Full synchronization with RAG Service V46.6.

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

        # Record user message
        db.cases.update_one({"_id": oid}, {"$push": {"chat_history": ChatMessage(role="user", content=user_query, timestamp=datetime.now(timezone.utc)).model_dump()}})
        
        full_response = ""
        yield " " # Keep-alive token

        if not mode or mode.upper() == 'FAST':
            snippets = vector_store_service.query_case_knowledge_base(user_id=user_id, query_text=user_query, n_results=10, case_context_id=case_id)
            context = "\n".join([f"- {s['text']} (Burimi: {s['source']})" for s in snippets])
            
            # PHOENIX FIX: Professional Instruction for Fast Mode
            system_prompt = f"Ti je 'Juristi AI'. Përdor formatin [Ligji](doc://ligji) për çdo citim.\nKONTEKSTI I RASTIT:\n{context}"
            
            async for token in llm_service.stream_text_async(system_prompt, user_query, temp=0.1):
                full_response += token
                yield token
        else:
            agent_service = AlbanianRAGService(db=db)
            
            # PHOENIX FIX: Pass jurisdiction to the deep chat generator
            async for token in agent_service.chat(
                query=user_query, 
                user_id=user_id, 
                case_id=case_id, 
                document_ids=[document_id] if document_id else None,
                jurisdiction=jurisdiction or 'ks'
            ):
                full_response += token
                yield token

        # Persistence
        if full_response.strip():
            db.cases.update_one({"_id": oid}, {"$push": {"chat_history": ChatMessage(role="ai", content=full_response.strip(), timestamp=datetime.now(timezone.utc)).model_dump()}})
            
    except Exception as e:
        logger.error(f"Streaming Error: {e}")
        yield "\n\n[Gabim Teknik: Shërbimi AI dështoi. Kontrolloni çelësat API.]"