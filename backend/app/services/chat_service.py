# FILE: backend/app/services/chat_service.py
# PHOENIX PROTOCOL - CHAT SERVICE V25.1 (TYPE INTEGRITY FIX)
# 1. FIX: Added missing 'structlog' import to resolve Pylance error.
# 2. FIX: Ensured compatibility with llm_service.stream_text_async.
# 3. STATUS: Hybrid Streaming Engine is now type-safe and operational.

from __future__ import annotations
import logging
import asyncio
import structlog # PHOENIX FIX: Added missing import
from typing import AsyncGenerator, Optional, List, Dict, Any
from fastapi import HTTPException
from bson import ObjectId
from bson.errors import InvalidId
from datetime import datetime, timezone
from pymongo.database import Database

from app.models.case import ChatMessage
from app.services.albanian_rag_service import AlbanianRAGService
from app.services import llm_service, vector_store_service

# PHOENIX: Setup logger with fallback
try:
    logger = structlog.get_logger(__name__)
except Exception:
    logger = logging.getLogger(__name__)

async def stream_chat_response(
    db: Database, 
    case_id: str, 
    user_query: str, 
    user_id: str,
    document_id: Optional[str] = None,
    jurisdiction: Optional[str] = 'ks',
    mode: Optional[str] = 'FAST'
) -> AsyncGenerator[str, None]:
    """
    Generator that yields tokens for the chat response.
    Orchestrates between direct RAG (Fast) and Agentic reasoning (Deep).
    """
    try:
        oid = ObjectId(case_id)
        user_oid = ObjectId(user_id)
    except InvalidId:
        yield "Gabim: ID e pavlefshme."
        return

    # 1. Verify access (Sync check against MongoDB)
    case = db.cases.find_one({"_id": oid, "owner_id": user_oid})
    if not case:
        yield "Gabim: Rasti nuk u gjet ose nuk keni akses."
        return

    # 2. Save User Message immediately (Sync Write)
    try:
        db.cases.update_one(
            {"_id": oid},
            {"$push": {"chat_history": ChatMessage(role="user", content=user_query, timestamp=datetime.now(timezone.utc)).model_dump()}}
        )
    except Exception as e:
        logger.error(f"DB Write Error (User): {e}")

    full_response = ""
    
    # 3. Initial "Keep-Alive" token to break the UI spinner instantly
    yield " " 

    try:
        # --- FAST MODE: Direct Prompt (Bypasses Agent Logic for low latency) ---
        if not mode or mode.upper() == 'FAST':
            context_text = ""
            try:
                # Query vector store directly from ChromaDB
                snippets = vector_store_service.query_case_knowledge_base(
                    user_id=user_id,
                    query_text=user_query,
                    n_results=5,
                    case_context_id=case_id,
                    document_ids=[document_id] if document_id else None
                )
                if snippets:
                    context_text = "\n".join([f"- {s['text']} (Burimi: {s['source']})" for s in snippets])
            except Exception as e:
                logger.error(f"RAG Retrieval Failed: {e}")
            
            system_prompt = f"""
            Ti je 'Juristi AI', asistent ligjor profesional për Kosovën.
            Përgjigju në GJUHËN SHQIPE.
            Përdor këtë kontekst nga dokumentet e rastit nëse është relevant:
            {context_text}
            
            Nëse konteksti nuk përmban përgjigjen, bazohesh në njohuritë e tua të përgjithshme për ligjet e Kosovës ({jurisdiction}).
            Ji i saktë, profesional dhe i drejtpërdrejtë.
            """
            
            # PHOENIX: Stream tokens directly from the LLM service
            async for token in llm_service.stream_text_async(system_prompt, user_query, temp=0.3):
                full_response += token
                yield token

        # --- DEEP MODE: Agentic Search (Complex multi-step reasoning) ---
        else:
            yield "⏳ *Duke analizuar dokumentet dhe bazën ligjore...*\n\n"
            
            agent_service = AlbanianRAGService(db=db)
            
            # Agentic logic usually requires full context before answering
            deep_text = await agent_service.chat(
                query=user_query,
                user_id=user_id,
                case_id=case_id,
                document_ids=[document_id] if document_id else None,
                jurisdiction=jurisdiction or 'ks'
            )
            
            # Yield in chunks to simulate a real-time typing experience for the UI
            chunk_size = 20
            for i in range(0, len(deep_text), chunk_size):
                chunk = deep_text[i:i+chunk_size]
                full_response += chunk
                yield chunk
                await asyncio.sleep(0.01)

    except Exception as e:
        logger.error(f"Streaming Error: {e}", exc_info=True)
        err_msg = "\n\n[Gabim Teknik: Shërbimi AI nuk u përgjigj. Provoni përsëri.]"
        yield err_msg
        full_response += err_msg

    # 4. Save Final AI Response to DB for history persistence
    if full_response.strip():
        try:
            db.cases.update_one(
                {"_id": oid},
                {"$push": {"chat_history": ChatMessage(role="ai", content=full_response.strip(), timestamp=datetime.now(timezone.utc)).model_dump()}}
            )
        except Exception as e:
            logger.error(f"DB Write Error (AI): {e}")