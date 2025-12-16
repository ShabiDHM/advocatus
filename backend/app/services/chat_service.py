# FILE: backend/app/services/chat_service.py
# PHOENIX PROTOCOL - CHAT SERVICE V16.1 (TYPE SAFE & COMPLIANT)
# 1. FIX: Resolves Pylance type errors for OpenAI 'messages' parameter.
# 2. FIX: Maps internal role 'ai' to OpenAI specific 'assistant' role.
# 3. LOGIC: Maintains 6-message memory window for smart context.

from __future__ import annotations
import os
import logging
from datetime import datetime, timezone
from typing import Any, Optional, List, Dict, cast

from fastapi import HTTPException
from bson import ObjectId
from bson.errors import InvalidId
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from app.models.case import ChatMessage
import app.services.vector_store_service as vector_store_service

logger = logging.getLogger(__name__)

# --- CONFIG ---
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY") 
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat" 

# --- KOSOVO SMART PROMPT (STRATEGY-ALIGNED) ---
SYSTEM_PROMPT_KOSOVO = """
Ti je "Juristi AI", një Asistent Ligjor i Avancuar për sistemin e Kosovës.
Ti punon PËR përdoruesin. Përdoruesi është Avokati Kryesor (Eprori yt).

RREGULLAT E ARTË (NON-NEGOTIABLE):
1. **AUTORITETI:** Ti zbaton strategjinë e përdoruesit. Nëse përdoruesi thotë "Kundërshto këtë fakt", ti gjen prova në dosje për ta mbështetur kundërshtimin. Ti NUK e kundërshton përdoruesin.
2. **MEMORJA:** Mbaj mend çfarë është thënë në mesazhet e mëparshme. Nëse përdoruesi të ka korrigjuar një datë, përdor datën e korrigjuar.
3. **VERIFIKIMI FAKTIK:** 
   - Beso vetëm çfarë sheh në tekstin e dhënë (Dokumentet).
   - Nëse data nuk është e qartë, shkruaj "Data e panjohur" - MOS shpik data.
   - Përdor formatin DD/MM/VITI (p.sh., 16/12/2025).
4. **BURIMET:**
   - E vërteta Absolute = Çfarë shkruhet në dokumentet e gjykatës (Aktgjykimet).
   - Pretendime = Çfarë shkruhet në Padi ose Deklarata palësh.

QËLLIMI YT:
Të ndihmosh përdoruesin të fitojë rastin.
"""

def _get_rag_service_instance(db: Any) -> Any:
    """
    Factory for RAG Service. 
    """
    try:
        from app.services.albanian_rag_service import AlbanianRAGService
        from app.services.albanian_language_detector import AlbanianLanguageDetector
    except ImportError as e:
        logger.error(f"❌ Critical Import Error in Chat Service: {e}")
        return None

    try:
        detector = AlbanianLanguageDetector()
        dummy_client = AsyncOpenAI(api_key="dummy") 
        
        return AlbanianRAGService(
            vector_store=vector_store_service,
            llm_client=dummy_client, 
            language_detector=detector,
            db=db
        )
    except Exception as e:
        logger.error(f"❌ RAG Init Failed: {e}", exc_info=True)
        return None

async def get_http_chat_response(
    db: Any, 
    case_id: str, 
    user_query: str, 
    user_id: str,
    document_id: Optional[str] = None,
    jurisdiction: Optional[str] = 'ks'
) -> str:
    """
    Orchestrates the Socratic Chat with Memory and Graph-Enhanced Retrieval.
    """
    try:
        oid = ObjectId(case_id)
        user_oid = ObjectId(user_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    # 1. Verify access and fetch Case
    case = await db.cases.find_one({"_id": oid, "owner_id": user_oid})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")

    # 2. Get Chat History (The Memory)
    # We take the last 6 messages (approx 3 conversation turns) to maintain context
    raw_history = case.get("chat_history", [])
    memory_messages: List[ChatCompletionMessageParam] = []
    
    if raw_history:
        try:
            # Take last 6
            recent_history = raw_history[-6:] 
            for msg in recent_history:
                # Handle both Dict and Pydantic object
                raw_role = msg.get('role') if isinstance(msg, dict) else getattr(msg, 'role', 'user')
                content = msg.get('content') if isinstance(msg, dict) else getattr(msg, 'content', '')
                
                # PHOENIX FIX: Map internal 'ai' role to OpenAI 'assistant'
                api_role = "assistant" if raw_role == "ai" else raw_role
                
                # Strict Filtering for OpenAI Allowed Roles
                if api_role == "user" and content:
                    memory_messages.append({"role": "user", "content": str(content)})
                elif api_role == "assistant" and content:
                    memory_messages.append({"role": "assistant", "content": str(content)})
                elif api_role == "system" and content:
                     memory_messages.append({"role": "system", "content": str(content)})
                     
        except Exception as e:
            logger.warning(f"Failed to parse chat history: {e}")

    # 3. Save CURRENT User Message to DB (As 'user')
    try:
        await db.cases.update_one(
            {"_id": oid},
            {"$push": {"chat_history": ChatMessage(role="user", content=user_query, timestamp=datetime.now(timezone.utc)).model_dump()}}
        )
    except Exception as e:
        logger.error(f"DB Write Error: {e}")
    
    response_text: str = "" 
    try:
        # 4. RETRIEVAL STEP (The "Eyes")
        rag_service = _get_rag_service_instance(db)
        
        context_dossier = ""
        if rag_service:
            context_dossier = await rag_service.retrieve_context(
                query=user_query, 
                case_id=case_id, 
                document_ids=[document_id] if document_id else None
            )
            
        # 5. GENERATION STEP (The "Brain")
        final_user_prompt = (
            f"=== KONTEKSTI I RI NGA DOSJA ===\n{context_dossier}\n\n"
            f"=== PYETJA AKTUALE E AVOKATIT ===\n{user_query}"
        )

        # Initialize explicit list type
        messages_payload: List[ChatCompletionMessageParam] = [{"role": "system", "content": SYSTEM_PROMPT_KOSOVO}]
        
        # Inject Memory (History)
        if memory_messages:
            messages_payload.extend(memory_messages)
            
        # Inject Current Query with RAG Context
        messages_payload.append({"role": "user", "content": final_user_prompt})

        if DEEPSEEK_API_KEY:
            client = AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url=OPENROUTER_BASE_URL)
            
            completion = await client.chat.completions.create(
                model=OPENROUTER_MODEL,
                messages=messages_payload,
                temperature=0.0, # Zero temp for accuracy
                max_tokens=1500, 
                extra_headers={"HTTP-Referer": "https://juristi.tech", "X-Title": "Juristi AI Chat"}
            )
            
            content = completion.choices[0].message.content
            response_text = content if content is not None else "Gabim në gjenerim nga AI."
        else:
            response_text = "⚠️ Konfigurimi i AI mungon (API Key missing)."

    except Exception as e:
        logger.error(f"AI Error: {e}", exc_info=True)
        response_text = "Kërkoj ndjesë, ndodhi një problem teknik gjatë analizës."

    # 6. Save AI Response to DB (As 'ai')
    try:
        await db.cases.update_one(
            {"_id": oid},
            {"$push": {"chat_history": ChatMessage(role="ai", content=response_text, timestamp=datetime.now(timezone.utc)).model_dump()}}
        )
    except Exception:
        pass

    return response_text