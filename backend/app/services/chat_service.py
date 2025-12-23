# FILE: backend/app/services/chat_service.py
# PHOENIX PROTOCOL - CHAT SERVICE V20.1 (IMPORT FIX)
# 1. FIXED: Added missing 'import asyncio'.
# 2. STATUS: Fully functional and type-safe.

from __future__ import annotations
import os
import logging
import asyncio # <--- PHOENIX FIX
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

# --- PHOENIX V19.5: BLOCKQUOTE HIGHLIGHT PROMPT ---
SYSTEM_PROMPT_FORENSIC = f"""
Ti je "Juristi AI - Auditori Forensik".
Përdoruesi është Avokati. Qëllimi yt është saktësia absolute, analiza e thellë dhe prezantimi vizual i bukur.

{STRICT_FORENSIC_RULES}

UDHËZIME PËR FORMATIM VIZUAL (E DETYRUESHME):

1. PREZANTIMI I LIGJEVE (THEKSIMI I BUKUR):
   - Për çdo nen ligjor, përdor këtë strukturë me bllok (Blockquote):
   
     **[Emri i Nenit/Ligjit]**:
     > "[Teksti ose shpjegimi i nenit këtu brenda bllokut]"

   - Kjo është kritike për t'i dhënë "highlight" tekstit ligjor.

2. CITIMI I BURIMEVE:
   - Në fund të faktit, shto burimin në kllapa të dyfishta: [[Burimi: Emri_i_Dokumentit]].

3. STRUKTURA:
   - Përdor pika (bullet points).
   - Ndaj seksionet me hapësirë.

4. PAANËSIA:
   - Prezanto konfliktin: "Paditësi thotë X, i Padituri thotë Y".

5. MOS SHPIK:
   - Nëse informacioni mungon, thuaj qartë "Nuk ka të dhëna në dosje".
"""

async def get_http_chat_response(
    db: Any, 
    case_id: str, 
    user_query: str, 
    user_id: str,
    document_id: Optional[str] = None,
    jurisdiction: Optional[str] = 'ks'
) -> str:
    """
    Orchestrates the Strict Forensic Chat using Direct Vector Access.
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
        # 4. RETRIEVAL STEP (MULTI-TENANT RAG)
        
        # PHOENIX FIX: Direct call to the new Multi-Tenant Vector Store
        rag_results = await asyncio.to_thread(
            vector_store_service.query_mixed_intelligence,
            user_id=user_id,
            query_text=user_query,
            n_results=8,
            case_context_id=case_id 
        )
        
        # Format Results for LLM
        context_parts = []
        if rag_results:
            for item in rag_results:
                source = item.get("source", "Unknown")
                text = item.get("text", "")
                type_ = item.get("type", "DATA")
                context_parts.append(f"--- {type_} (Burimi: {source}) ---\n{text}")
            
            context_dossier = "\n\n".join(context_parts)
        else:
            context_dossier = "NUK U GJET ASNJË DOKUMENT OSE FAKT PËRKATËS NË DOSJE PËR KËTË ÇËSHTJE."

        # 5. GENERATION STEP (Strict LLM)
        final_user_prompt = (
            f"=== KONTEKSTI NGA DOSJA (RAG) ===\n{context_dossier}\n\n"
            f"=== PYETJA E AVOKATIT ===\n{user_query}"
        )

        messages_payload: List[ChatCompletionMessageParam] = [cast(ChatCompletionMessageParam, {"role": "system", "content": SYSTEM_PROMPT_FORENSIC})]
        
        if memory_messages:
            messages_payload.extend(memory_messages)
            
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
        response_text = "Kërkoj ndjesë, ndodhi një problem teknik gjatë auditimit."

    # 6. Save AI Response
    try:
        await db.cases.update_one(
            {"_id": oid},
            {"$push": {"chat_history": ChatMessage(role="ai", content=response_text, timestamp=datetime.now(timezone.utc)).model_dump()}}
        )
    except Exception:
        pass

    return response_text