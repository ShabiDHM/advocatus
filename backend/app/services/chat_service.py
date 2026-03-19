# FILE: backend/app/services/chat_service.py
# PHOENIX PROTOCOL - CHAT SERVICE V26.0 (ENHANCED FAST MODE WITH ANTI-HALLUCINATION)
# 1. IMPROVED: Fast mode prompt now includes anti-hallucination rules, placeholder instructions, and relevance requirement.
# 2. PRESERVED: Deep mode uses AlbanianRAGService (which will be enhanced separately).
# 3. ADDED: Consistency with drafting page's anti-hallucination approach.

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
        if not case:
            yield "Gabim: Qasja u refuzua."
            return

        # Sync User Message to History
        db.cases.update_one({"_id": oid}, {"$push": {"chat_history": ChatMessage(role="user", content=user_query, timestamp=datetime.now(timezone.utc)).model_dump()}})
        
        full_response = ""
        yield " "  # Keep-alive

        if not mode or mode.upper() == 'FAST':
            # --- FAST MODE: Direct, Concise Summary with Anti-Hallucination ---
            snippets = vector_store_service.query_case_knowledge_base(user_id=user_id, query_text=user_query, n_results=10, case_context_id=case_id)
            context = "\n".join([f"- {s['text']} (Burimi: {s['source']})" for s in snippets]) if snippets else "Nuk u gjetën dokumente për këtë rast."

            # Enhanced system prompt with anti-hallucination and placeholder instructions
            system_prompt = f"""
ROLI: Avokat i Licencuar në Republikën e Kosovës.

DETYRA: Jep një përgjigje të shpejtë dhe të shkurtër (MAX 2 PARAGRAFE) për pyetjen e përdoruesit, duke u bazuar në kontekstin e ofruar dhe njohuritë e tua për ligjet e Kosovës.

UDHËZIME TË RREPTA:
1. **Mos shpik kurrë ligje ose nene** – nëse nuk je i sigurt për një citim, përdor një vendmbajtës si "[Neni përkatës i Ligjit ...]".
2. **Nëse nuk ke informacion të mjaftueshëm, thuaj qartë se nuk di** në vend që të hamendësosh.
3. **Për çdo ligj të cituar, shto një rresht "RELEVANCA:" që shpjegon pse ai ligj është i rëndësishëm për pyetjen.
4. **Përdor formatin e citimit:** [Emri i Ligjit, Neni XX](doc://ligji). Nëse numri i nenit nuk dihet, përdor "Neni përkatës".
5. **Bazo përgjigjen kryesisht në kontekstin e ofruar**, por mund të shtosh njohuri të përgjithshme nëse është e nevojshme.

KONTEKSTI I RASTIT:
{context}

Pyetja: {user_query}
"""
            async for token in llm_service.stream_text_async(system_prompt, user_query, temp=0.1):
                full_response += token
                yield token
        else:
            # --- DEEP MODE: Comprehensive Legal Analysis (via AlbanianRAGService) ---
            # Note: AlbanianRAGService will be enhanced separately
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