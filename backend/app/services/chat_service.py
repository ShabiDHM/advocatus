# FILE: backend/app/services/chat_service.py
# PHOENIX PROTOCOL - CHAT SERVICE V13.1 (ANTI-HALLUCINATION HANDCUFFS)
# 1. LOGIC: Temperature set to 0.0 (Zero Creativity).
# 2. PROMPT: Added "Party Verification" step to force AI to read names first.
# 3. SAFETY: Blocks request if Context is empty to prevent guessing.

from __future__ import annotations
import os
import logging
from datetime import datetime, timezone
from typing import Any, Optional, List, Dict

from fastapi import HTTPException
from bson import ObjectId
from bson.errors import InvalidId
from openai import AsyncOpenAI

from app.models.case import ChatMessage
import app.services.vector_store_service as vector_store_service

logger = logging.getLogger(__name__)

# --- CONFIG ---
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY") 
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat" 

# --- KOSOVO SMART PROMPT (STRICT EVIDENCE MODE) ---
SYSTEM_PROMPT_KOSOVO = """
Ti je "Juristi AI", një analist ligjor rigoroz për ligjet e REPUBLIKËS SË KOSOVËS.
Roli yt nuk është të jesh kreativ. Roli yt është të jesh "Forenzik".

PROTOKOLLI I PËRGJIGJES (STRICT):
Hapi 1: **VERIFIKIMI I PALËVE**: Lexo tekstin më poshtë ("KONTEKSTI I DOSJES"). Identifiko emrat e Paditësit dhe të Paditurit. 
   - Nëse nuk gjen emra në tekst, thuaj: "Nuk mund të identifikoj palët në këtë dokument." dhe NDALO.
   - Nëse emrat në tekst nuk përputhen me pyetjen e përdoruesit, thuaj: "Konteksti përmban palë të tjera ([Emrat e gjetur])."

Hapi 2: **ANALIZA E FAKTEVE**: Cito vetëm faktet që janë SHKRUAR në tekst. 
   - Mos supozo. Mos shpik data. Mos shpik shuma parash.

Hapi 3: **PËRFUNDIMI**: Përgjigju pyetjes bazuar vetëm në Hapi 1 dhe Hapi 2.

RREGULLAT E VDEKJES (DO NOT BREAK):
1. MOS PËRMEND "Teuta", "Ilir", "Kriptovaluta" nëse nuk janë shkruar në tekstin e mëposhtëm.
2. JURISDIKSIONI: Vetëm Kosova.
"""

def _get_rag_service_instance(db: Any) -> Any:
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
    Orchestrates the Socratic Chat with Anti-Hallucination Guardrails.
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

    # 2. Save User Message
    try:
        await db.cases.update_one(
            {"_id": oid},
            {"$push": {"chat_history": ChatMessage(role="user", content=user_query, timestamp=datetime.now(timezone.utc)).model_dump()}}
        )
    except Exception as e:
        logger.error(f"DB Write Error: {e}")
    
    response_text: str = "" 
    try:
        # 3. RETRIEVAL STEP
        rag_service = _get_rag_service_instance(db)
        
        context_dossier = ""
        if rag_service:
            context_dossier = await rag_service.retrieve_context(
                query=user_query, 
                case_id=case_id, 
                document_ids=[document_id] if document_id else None
            )
            
        # 4. SAFETY CHECK: EMPTY CONTEXT
        # If OCR failed or no text found, DO NOT send to AI. It will hallucinate.
        if not context_dossier or len(context_dossier.strip()) < 50:
            logger.warning(f"⚠️ Empty Context for Case {case_id}. Aborting AI generation.")
            response_text = (
                "⚠️ **Nuk u gjet informacion.**\n\n"
                "Sistemi nuk mundi të lexojë tekstin nga dokumentet e këtij rasti. "
                "Kjo mund të ndodhë nëse:\n"
                "1. Dokumenti është foto/skanim i paqartë (OCR dështoi).\n"
                "2. Dokumenti nuk është ngarkuar ende plotësisht.\n\n"
                "Ju lutem provoni të ngarkoni një PDF më të qartë ose prisni pak minuta."
            )
        else:
            # 5. GENERATION STEP (Only if data exists)
            final_user_prompt = (
                f"=== KONTEKSTI I DOSJES (BURIMI I VETËM I TË VËRTETËS) ===\n{context_dossier}\n\n"
                f"=== PYETJA E KLIENTIT ===\n{user_query}"
            )

            if DEEPSEEK_API_KEY:
                client = AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url=OPENROUTER_BASE_URL)
                
                completion = await client.chat.completions.create(
                    model=OPENROUTER_MODEL,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT_KOSOVO},
                        {"role": "user", "content": final_user_prompt}
                    ],
                    temperature=0.0, # ZERO CREATIVITY. STRICT FACTS.
                    max_tokens=1000,
                    extra_headers={"HTTP-Referer": "https://juristi.tech", "X-Title": "Juristi AI Chat"}
                )
                
                content = completion.choices[0].message.content
                response_text = content if content is not None else "Gabim në gjenerim."
            else:
                response_text = "⚠️ Konfigurimi i AI mungon."

    except Exception as e:
        logger.error(f"AI Error: {e}", exc_info=True)
        response_text = "Problem teknik gjatë analizës."

    # 6. Save AI Response
    try:
        await db.cases.update_one(
            {"_id": oid},
            {"$push": {"chat_history": ChatMessage(role="ai", content=response_text, timestamp=datetime.now(timezone.utc)).model_dump()}}
        )
    except Exception:
        pass

    return response_text