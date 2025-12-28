# FILE: backend/app/services/chat_service.py
# PHOENIX PROTOCOL - CHAT SERVICE V21.1 (TYPE SAFETY FIX)
# 1. FIX: Added a default value for 'jurisdiction' to ensure it's always a 'str'.
# 2. STATUS: Resolves the final Pylance error.

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
    jurisdiction: Optional[str] = 'ks'
) -> str:
    """
    Orchestrates the Agentic Chat Response.
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
        # 3. DELEGATE TO AGENT EXECUTOR
        agent_service = AlbanianRAGService(db=db)
        
        # PHOENIX FIX: Ensure jurisdiction is never None
        final_jurisdiction = jurisdiction if jurisdiction is not None else 'ks'

        response_text = await agent_service.chat(
            query=user_query,
            user_id=user_id,
            case_id=case_id,
            document_ids=[document_id] if document_id else None,
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