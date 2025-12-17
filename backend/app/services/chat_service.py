# FILE: backend/app/services/chat_service.py
# PHOENIX PROTOCOL - CHAT SERVICE V18.3 (TYPE SAFETY FIX)
# 1. FIX: Used `cast` to resolve Pylance's strict type checking for ChatCompletionMessageParam.
# 2. STATUS: Clean build, zero warnings.

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
from app.services.llm_service import STRICT_FORENSIC_RULES

logger = logging.getLogger(__name__)

# --- CONFIG ---
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat" 

# --- THE HYBRID (ACCURATE + CONVERSATIONAL) PROMPT ---
SYSTEM_PROMPT_HYBRID = f"""
Ti je "Asistenti Ligjor i Dosjes". Roli yt është t'i përgjigjesh pyetjeve të Avokatit shkurt, saktë dhe në mënyrë konverzacionale.

RREGULLAT E TUA TË PANIGOCIUESHME JANË KËTO:
{STRICT_FORENSIC_RULES}

UDHËZIME SHTESË PËR Bisedë:
1. PËRGJIGJU VETËM NGA KONTEKSTI: Konteksti i dhënë është e vetmja e vërtetë. Nëse përgjigja nuk gjendet aty, thuaj: "Ky informacion nuk gjendet në dokumentet e analizuara."
2. LEXO BURIMET: Konteksti përmban etiketa [[BURIMI: ...]]. Përdori ato për të treguar nga cili dokument vjen informacioni (psh. "Sipas Padisë..."). Raporto konfliktet mes dokumenteve.
3. BASHKËBISEDO, MOS RAPORTO: Përgjigju pyetjes direkt. Mos krijo lista të gjata apo raporte të pa kërkuara, përveç nëse avokati e kërkon specifikisht.
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
    Orchestrates the Strict Forensic Chat.
    """
    try:
        oid = ObjectId(case_id)
        user_oid = ObjectId(user_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    # 1. Verify access
    case = await db.cases.find_one({"_id": oid, "owner_id": user_oid})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")

    # 2. Get Chat History (Memory)
    raw_history = case.get("chat_history", [])
    memory_messages: List[ChatCompletionMessageParam] = []
    
    if raw_history:
        try:
            recent_history = raw_history[-6:] 
            for msg in recent_history:
                raw_role = msg.get('role') if isinstance(msg, dict) else getattr(msg, 'role', 'user')
                content = msg.get('content') if isinstance(msg, dict) else getattr(msg, 'content', '')
                
                api_role = "assistant" if raw_role == "ai" else "user"
                
                if content:
                    # PHOENIX FIX: Use 'cast' to satisfy strict type checker
                    message = cast(ChatCompletionMessageParam, {"role": api_role, "content": str(content)})
                    memory_messages.append(message)
        except Exception as e:
            logger.warning(f"Failed to parse chat history: {e}")

    # 3. Save User Message
    try:
        await db.cases.update_one(
            {"_id": oid},
            {"$push": {"chat_history": ChatMessage(role="user", content=user_query, timestamp=datetime.now(timezone.utc)).model_dump()}}
        )
    except Exception as e:
        logger.error(f"DB Write Error: {e}")
    
    response_text: str = "" 
    try:
        # 4. RETRIEVAL STEP (RAG)
        rag_service = _get_rag_service_instance(db)
        
        context_dossier = ""
        if rag_service:
            context_dossier = await rag_service.retrieve_context(
                query=user_query, 
                case_id=case_id, 
                document_ids=[document_id] if document_id else None
            )
            
        # 5. GENERATION STEP (Strict LLM)
        if not context_dossier:
            context_dossier = "NUK U GJET ASNJË DOKUMENT OSE FAKT PËRKATËS NË DOSJE PËR KËTË ÇËSHTJE."

        final_user_prompt = (
            f"=== KONTEKSTI NGA DOSJA ===\n{context_dossier}\n\n"
            f"=== PYETJA E AVOKATIT ===\n{user_query}"
        )

        messages_payload: List[ChatCompletionMessageParam] = [cast(ChatCompletionMessageParam, {"role": "system", "content": SYSTEM_PROMPT_HYBRID})]
        
        if memory_messages:
            messages_payload.extend(memory_messages)
            
        # PHOENIX FIX: Use 'cast' to satisfy strict type checker on the final user message
        final_message = cast(ChatCompletionMessageParam, {"role": "user", "content": final_user_prompt})
        messages_payload.append(final_message)

        if DEEPSEEK_API_KEY:
            client = AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url=OPENROUTER_BASE_URL)
            
            completion = await client.chat.completions.create(
                model=OPENROUTER_MODEL,
                messages=messages_payload,
                temperature=0.0,
                max_tokens=1500, 
                extra_headers={"HTTP-Referer": "https://juristi.tech", "X-Title": "Juristi AI Chat"}
            )
            
            content = completion.choices[0].message.content
            response_text = content if content is not None else "Gabim në gjenerim nga AI."
        else:
            response_text = "⚠️ Konfigurimi i AI mungon (API Key missing)."

    except Exception as e:
        logger.error(f"AI Error: {e}", exc_info=True)
        response_text = "Kërkoj ndjesë, ndodhi një problem teknik gjatë procesimit."

    # 6. Save AI Response
    try:
        await db.cases.update_one(
            {"_id": oid},
            {"$push": {"chat_history": ChatMessage(role="ai", content=response_text, timestamp=datetime.now(timezone.utc)).model_dump()}}
        )
    except Exception:
        pass

    return response_text