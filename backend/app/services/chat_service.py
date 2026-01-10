# FILE: backend/app/services/chat_service.py
# PHOENIX PROTOCOL - CHAT SERVICE V23.0 (DUAL GEAR LOGIC)
# 1. FEAT: Accepts 'mode' parameter.
# 2. LOGIC: Switches between 'chat' (Agent) and 'fast_rag' (Direct).
# 3. SAFETY: Type checking for all ObjectIds.

from __future__ import annotations
import logging
from typing import Any, Optional

from fastapi import HTTPException
from bson import ObjectId
from bson.errors import InvalidId
from datetime import datetime, timezone

from app.models.case import ChatMessage
from app.services.albanian_rag_service import AlbanianRAGService

logger = logging.getLogger(__name__)

async def get_http_chat_response(
    db: Any, 
    case_id: str, 
    user_query: str, 
    user_id: str,
    document_id: Optional[str] = None,
    jurisdiction: Optional[str] = 'ks',
    mode: Optional[str] = 'FAST'
) -> str:
    """
    Orchestrates the Chat Response.
    Routes to 'fast_rag' or 'chat' based on mode.
    """
    try:
        oid = ObjectId(case_id)
        user_oid = ObjectId(user_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    # 1. Verify access
    case = await db.cases.find_one({"_id": oid, "owner_id": user_oid})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found or access denied.")

    # 2. Save User Message to DB History
    try:
        await db.cases.update_one(
            {"_id": oid},
            {"$push": {"chat_history": ChatMessage(role="user", content=user_query, timestamp=datetime.now(timezone.utc)).model_dump()}}
        )
    except Exception as e:
        logger.error(f"DB Write Error (User Message): {e}")
    
    response_text: str = "" 
    try:
        agent_service = AlbanianRAGService(db=db)
        
        final_jurisdiction = jurisdiction if jurisdiction else 'ks'
        doc_ids = [document_id] if document_id else None
        
        # PHOENIX: Dual Gear Switching
        if mode and mode.upper() == 'DEEP':
            # Use the Agentic Loop (Slower, Reasoning-based)
            response_text = await agent_service.chat(
                query=user_query,
                user_id=user_id,
                case_id=case_id,
                document_ids=doc_ids,
                jurisdiction=final_jurisdiction
            )
        else:
            # Use the Fast RAG (Faster, Vector-based)
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

    # 4. Save AI Response to DB History
    try:
        await db.cases.update_one(
            {"_id": oid},
            {"$push": {"chat_history": ChatMessage(role="ai", content=response_text, timestamp=datetime.now(timezone.utc)).model_dump()}}
        )
    except Exception as e:
        logger.error(f"DB Write Error (AI Response): {e}")

    return response_text