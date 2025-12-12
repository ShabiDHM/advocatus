# FILE: backend/app/services/chat_service.py
# PHOENIX PROTOCOL - CHAT SERVICE V13.4 (LOGIC REFINEMENT)
# 1. FIX: Added specific rule to distinguish "Proposed Judgment" inside a Lawsuit vs Real Judgment.
# 2. FIX: OCR Correction rule for numbers (250 vs 280).

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

# --- KOSOVO SMART PROMPT (LOGIC & STRUCTURE) ---
SYSTEM_PROMPT_KOSOVO = """
Ti je "Juristi AI", analist ligjor për Kosovën.

PROTOKOLLI I ANALIZËS (LEXO ME KUJDES):

1. **IDENTIFIKIMI I DOKUMENTIT (KRITIKE):**
   - Nëse dokumenti fillon me "PADI", atëherë çdo gjë e shkruar në fund (nën "AKTGJYKIM" ose "PROPOZIM") është **KËRKESË E PADITËSIT**, NUK është vendim i Gjykatës.
   - **GABIMI PËR TË SHMANGUR:** Mos thuaj "Gjykata ka vendosur". Thuaj "Paditësi KËRKON që Gjykata të vendosë".

2. **SAKTËSIA E NUMRAVE (OCR):**
   - Nëse teksti është i paqartë midis 250 dhe 280, shiko kontekstin. Nëse kërkohet rritje nga 200, zakonisht hapi logjik është 250. 
   - Cito vetëm numrat që shihen qartë.

3. **VERIFIKIMI I PALËVE:**
   - Paditësi dhe I Padituri janë zakonisht në krye të faqes së parë.

4. **DATAT:**
   - Data në fund të faqes së fundit është data e hartimit të padisë.

HAPAT E PËRGJIGJES:
Hapi 1: Kush janë palët? (Nëse nuk i gjen, thuaj "Nuk u gjetën në tekstin e skanuar").
Hapi 2: Çfarë kërkon paditësi? (Përmblidh kërkesëpadinë).
Hapi 3: Cilat janë faktet kryesore? (Alimentacioni, kontaktet, etj).
Hapi 4: Konkluzion (Kjo është Padi, jo Aktgjykim).

STILI:
Ji i saktë, i shkurtër dhe profesional.
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
    Orchestrates the Socratic Chat.
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
            
        if not context_dossier or len(context_dossier.strip()) < 50:
            logger.warning(f"⚠️ Empty Context for Case {case_id}")
            response_text = "⚠️ Nuk u gjet informacion i mjaftueshëm në tekstin e skanuar. Ju lutem provoni 'Skanim i Thellë' përsëri."
        else:
            # 5. GENERATION STEP
            final_user_prompt = (
                f"=== KONTEKSTI I DOKUMENTIT ===\n{context_dossier}\n\n"
                f"=== PYETJA ===\n{user_query}"
            )

            if DEEPSEEK_API_KEY:
                client = AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url=OPENROUTER_BASE_URL)
                
                completion = await client.chat.completions.create(
                    model=OPENROUTER_MODEL,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT_KOSOVO},
                        {"role": "user", "content": final_user_prompt}
                    ],
                    temperature=0.0, 
                    max_tokens=1000,
                    extra_headers={"HTTP-Referer": "https://juristi.tech", "X-Title": "Juristi AI Chat"}
                )
                
                content = completion.choices[0].message.content
                response_text = content if content is not None else "Gabim në gjenerim."
            else:
                response_text = "⚠️ Konfigurimi i AI mungon."

    except Exception as e:
        logger.error(f"AI Error: {e}", exc_info=True)
        response_text = "Problem teknik."

    # 6. Save AI Response
    try:
        await db.cases.update_one(
            {"_id": oid},
            {"$push": {"chat_history": ChatMessage(role="ai", content=response_text, timestamp=datetime.now(timezone.utc)).model_dump()}}
        )
    except Exception:
        pass

    return response_text