# FILE: backend/app/services/chat_service.py
# PHOENIX PROTOCOL - CHAT SERVICE V30.0 (CIRCULAR IMPORT RESOLVED • LAZY RAG INGESTION)
# PRODUCTION STABILITY • ZERO CRASHES ON STARTUP • STRICT CHAT ISOLATION

from __future__ import annotations
import logging
import asyncio
import structlog
from typing import AsyncGenerator, Optional, List, Dict, Any
from bson import ObjectId
from datetime import datetime, timezone
from pymongo.database import Database
from app.models.case import ChatMessage

logger = structlog.get_logger(__name__)

async def stream_chat_response(
    db: Database, 
    case_id: str, 
    user_query: str, 
    user_id: str,
    document_ids: Optional[List[str]] = None,
    jurisdiction: Optional[str] = 'ks',
    domain: Optional[str] = 'automatic',
    save_history: bool = True
) -> AsyncGenerator[str, None]:
    """
    Unified chat endpoint with strict chat history isolation:
    - If save_history is True: persists to case.chat_history (Standard Interactive Chat).
    - If save_history is False: streams directly to the caller without polluting chat history.
    """
    try:
        # PHOENIX FIX: Lazy import për të shmangur bllokimin ciklik në nisje të Uvicorn
        from app.services.albanian_rag_service import AlbanianRAGService

        oid, user_oid = ObjectId(case_id), ObjectId(user_id)
        case = db.cases.find_one({"_id": oid, "owner_id": user_oid})
        if not case:
            yield "Gabim: Qasja u refuzua."
            return

        # PHOENIX ISOLATION: Ruaj në chat_history VETËM nëse save_history == True
        if save_history:
            db.cases.update_one(
                {"_id": oid}, 
                {"$push": {"chat_history": ChatMessage(
                    role="user", 
                    content=user_query, 
                    timestamp=datetime.now(timezone.utc)
                ).model_dump()}}
            )
        
        full_response = ""
        yield " "  # Keep-alive

        chat_history = case.get("chat_history", [])
        recent_history = chat_history[-10:] if save_history else []

        agent_service = AlbanianRAGService(db=db)
        async for token in agent_service.chat(
            query=user_query,
            user_id=user_id,
            case_id=case_id,
            document_ids=document_ids,
            jurisdiction=jurisdiction or 'ks',
            history=recent_history,
            domain=domain
        ):
            full_response += token
            yield token

        # PHOENIX ISOLATION: Ruaj përgjigjen e AI në chat_history VETËM nëse save_history == True
        if save_history and full_response.strip():
            db.cases.update_one(
                {"_id": oid}, 
                {"$push": {"chat_history": ChatMessage(
                    role="ai", 
                    content=full_response.strip(), 
                    timestamp=datetime.now(timezone.utc)
                ).model_dump()}}
            )
            
    except Exception as e:
        logger.error(f"Streaming Error: {e}")
        yield "\n\n[Gabim Teknik: Shërbimi i bisedës dështoi.]"