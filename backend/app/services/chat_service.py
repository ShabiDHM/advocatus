# FILE: backend/app/services/chat_service.py
# PHOENIX PROTOCOL - CHAT SERVICE V26.0 (UNIFIED - NO FAST/DEEP SPLIT)
# 1. REMOVED: mode parameter and all conditional logic.
# 2. UNIFIED: Every request now uses AlbanianRAGService.chat() exclusively.
# 3. RETAINED: Multi-document support, history sync, jurisdiction, domain.

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
    db: Database, 
    case_id: str, 
    user_query: str, 
    user_id: str,
    document_ids: Optional[List[str]] = None,
    jurisdiction: Optional[str] = 'ks',
    domain: Optional[str] = 'automatic'
) -> AsyncGenerator[str, None]:
    """
    Unified chat endpoint. Every request uses the hardened AlbanianRAGService.chat()
    with full context grounding, citation mapping, and refusal rules.
    """
    try:
        oid, user_oid = ObjectId(case_id), ObjectId(user_id)
        case = db.cases.find_one({"_id": oid, "owner_id": user_oid})
        if not case:
            yield "Gabim: Qasja u refuzua."
            return

        # Sync User Message to History
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

        # Get conversation history for context
        chat_history = case.get("chat_history", [])
        recent_history = chat_history[-10:]  # last 5 exchanges

        # UNIFIED: Always use the hardened RAG service
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

        # Sync AI Message to History
        if full_response.strip():
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