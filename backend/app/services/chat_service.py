# FILE: backend/app/services/chat_service.py
# PHOENIX PROTOCOL - CHAT SERVICE V32.0 (SINGLE-CHANNEL PERSISTENCE)
# V32.0: Hequr kanali forensic (is_forensic) — feature e fshirë.
#        Tani vetëm kanali i klientit: chat_history.

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
    save_history: bool = True,
) -> AsyncGenerator[str, None]:
    """
    Shërbimi Qendror i Bisedës për klientin.
    Historiku ruhet dhe lexohet nga `case.chat_history`.
    """
    try:
        from app.services.albanian_rag_service import AlbanianRAGService

        oid, user_oid = ObjectId(case_id), ObjectId(user_id)
        case = db.cases.find_one({"_id": oid, "$or": [{"owner_id": user_oid}, {"user_id": user_oid}, {"owner_id": str(user_oid)}]})
        if not case:
            yield "Gabim: Qasja u refuzua ose lënda nuk u gjet."
            return

        # 1. Ruajtja e pyetjes së përdoruesit
        if save_history:
            db.cases.update_one(
                {"_id": oid}, 
                {"$push": {"chat_history": ChatMessage(
                    role="user", 
                    content=user_query, 
                    timestamp=datetime.now(timezone.utc)
                ).model_dump()}}
            )
        raw_history = case.get("chat_history", [])
        recent_history = raw_history[-10:] if save_history else []

        full_response = ""
        yield " "  # Keep-alive fillestar

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

        # 2. Ruajtja e përgjigjes së AI
        if full_response.strip() and save_history:
            clean_ai_text = full_response.strip()
            db.cases.update_one(
                {"_id": oid}, 
                {"$push": {"chat_history": ChatMessage(
                    role="ai", 
                    content=clean_ai_text, 
                    timestamp=datetime.now(timezone.utc)
                ).model_dump()}}
            )
            
    except Exception as e:
        logger.error(f"Streaming Error: {e}")
        yield f"\n\n[Gabim Teknik në Transmetim: {str(e)}]"