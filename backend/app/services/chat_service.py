# FILE: backend/app/services/chat_service.py
# PHOENIX PROTOCOL - CHAT SERVICE V23.1 (SYNC DB ADAPTER)
# 1. FIX: Removed 'await' from database calls (find_one, update_one) to match Sync DB.
# 2. STATUS: Hybrid Service (Sync DB + Async AI).

from __future__ import annotations
import logging
from typing import Any, Optional

from fastapi import HTTPException
from bson import ObjectId
from bson.errors import InvalidId
from datetime import datetime, timezone
from pymongo.database import Database

from app.models.case import ChatMessage
from app.services.albanian_rag_service import AlbanianRAGService

logger = logging.getLogger(__name__)

async def get_http_chat_response(
    db: Database, 
    case_id: str, 
    user_query: str, 
    user_id: str,
    document_id: Optional[str] = None,
    jurisdiction: Optional[str] = 'ks',
    mode: Optional[str] = 'FAST'
) -> str:
    """
    Orchestrates the Chat Response.
    Uses Sync DB for storage, Async for AI.
    """
    try:
        oid = ObjectId(case_id)
        user_oid = ObjectId(user_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    # 1. Verify access (SYNC)
    case = db.cases.find_one({"_id": oid, "owner_id": user_oid})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found or access denied.")

    # 2. Save User Message (SYNC)
    try:
        db.cases.update_one(
            {"_id": oid},
            {"$push": {"chat_history": ChatMessage(role="user", content=user_query, timestamp=datetime.now(timezone.utc)).model_dump()}}
        )
    except Exception as e:
        logger.error(f"DB Write Error (User Message): {e}")
    
    response_text: str = "" 
    try:
        # Initialize RAG Service with Sync DB
        # Note: AlbanianRAGService must support Sync DB or handle its own connection.
        agent_service = AlbanianRAGService(db=db)
        
        final_jurisdiction = jurisdiction if jurisdiction else 'ks'
        doc_ids = [document_id] if document_id else None
        
        # 3. Generate Response (ASYNC - assuming RAG service uses async HTTP calls)
        if mode and mode.upper() == 'DEEP':
            response_text = await agent_service.chat(
                query=user_query,
                user_id=user_id,
                case_id=case_id,
                document_ids=doc_ids,
                jurisdiction=final_jurisdiction
            )
        else:
            response_text = await agent_service.fast_rag(
                query=user_query,
                user_id=user_id,
                case_id=case_id,
                document_ids=doc_ids,
                jurisdiction=final_jurisdiction
            )

    except Exception as e:
        logger.error(f"Agent Service Error: {e}", exc_info=True)
        response_text = "Kërkoj ndjesë, ndodhi një problem teknik me agjentin AI."

    # 4. Save AI Response (SYNC)
    try:
        db.cases.update_one(
            {"_id": oid},
            {"$push": {"chat_history": ChatMessage(role="ai", content=response_text, timestamp=datetime.now(timezone.utc)).model_dump()}}
        )
    except Exception as e:
        logger.error(f"DB Write Error (AI Response): {e}")

    return response_text