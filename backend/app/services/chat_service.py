# FILE: backend/app/services/chat_service.py
# PHOENIX PROTOCOL - CHAT SERVICE V13.3 (DATE HIERARCHY FIX)
# 1. FIX: Distinguishes between 'Application Date' (Footer) and 'Hearing Date'.
# 2. LOGIC: Explicitly bans predicting future dates based on system time.

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

# --- KOSOVO SMART PROMPT (DATE FORENSICS) ---
SYSTEM_PROMPT_KOSOVO = """
Ti je "Juristi AI", një analist ligjor rigoroz për ligjet e REPUBLIKËS SË KOSOVËS.

PROTOKOLLI I PËRGJIGJES (STRICT):

Hapi 1: **VERIFIKIMI I PALËVE**: 
   - Identifiko saktësisht Paditësin dhe të Paditurin nga kreu i dokumentit.

Hapi 2: **SAKTËSIA E DATAVE (KRITIKE)**:
   - Cito VETËM datat që janë fizikisht të shkruara në tekst (formati DD.MM.YYYY).
   - **KUJDES:** Data në fund të dokumentit (poshtë nënshkrimit) është **Data e Dorëzimit/Hartimit**. Ajo NUKE ËSHTË datë seance.
   - **NDALIM:** Mos përdor datën e sotme për të parashikuar "seanca të ardhshme". Nëse nuk shkruan "Seanca caktohet më...", atëherë NUK KA SEANCË.

Hapi 3: **ANALIZA E FAKTEVE**: 
   - Përmblidh kërkesëpadinë bazuar në tekst.

Hapi 4: **PËRFUNDIMI**: 
   - Përgjigju pyetjes bazuar vetëm në provat e gjetura.

RREGULLAT E VDEKJES (DO NOT BREAK):
1. MOS PËRMEND emra apo data që nuk janë në tekst.
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
        if not context_dossier or len(context_dossier.strip()) < 50:
            logger.warning(f"⚠️ Empty Context for Case {case_id}. Aborting AI generation.")
            response_text = (
                "⚠️ **Nuk u gjet informacion.**\n\n"
                "Sistemi nuk mundi të lexojë tekstin nga dokumentet e këtij rasti. "
                "Ju lutem sigurohuni që keni klikuar 'Skanim i Thellë' (Deep Scan) tek dokumenti."
            )
        else:
            # 5. GENERATION STEP
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
                    temperature=0.0, # ZERO CREATIVITY
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