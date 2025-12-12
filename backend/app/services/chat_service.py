# FILE: backend/app/services/chat_service.py
# PHOENIX PROTOCOL - CHAT SERVICE V14.0 (GRAPH-AWARE ORCHESTRATION)
# 1. UPGRADE: System Prompt now explicitly understands Graph vs Vector context structure.
# 2. LOGIC: Enforces "Hierarchy of Truth" (Graph > Text > General Knowledge).
# 3. SAFETY: Strict "No Data = No Answer" policy.

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

# --- KOSOVO SMART PROMPT (CONTEXT-AWARE) ---
SYSTEM_PROMPT_KOSOVO = """
Ti je "Juristi AI", një Asistent Ligjor i Avancuar për sistemin e Kosovës.
Ti ke akses në një "DOSJE KONTEKSTI" të strukturuar me burime të ndryshme (Graf, Dokumente, Ligje).

HIERARKIA E TË VËRTETËS (STRIKTE):
1. **EVIDENCA NGA GRAFI:** Kjo është e vërteta absolute për lidhjet (Kush njeh kë, rolet, datat kyçe). Besoji kësaj mbi tekstin e lirë.
2. **FRAGMENTE DOKUMENTESH:** Përdori këto për citime specifike dhe nuanca gjuhësore.
3. **BAZA LIGJORE:** Përdore vetëm për interpretim ligjor, jo për fakte të çështjes.

PROTOKOLLI I ANALIZËS:
1. **Verifikimi:** A ka dosja informacion për pyetjen? Nëse jo, thuaj: "Nuk kam informacion të mjaftueshëm në dokumentet e skanuara."
2. **Identifikimi:** Dalloni qartë midis 'Pretendimit të Palës' (Padi) dhe 'Vendimit të Gjykatës' (Aktgjykim). 
   - KUJDES: Shumë padi përfundojnë me "PROPOZIM: AKTGJYKIM". Kjo NUK është vendim, është dëshira e paditësit.
3. **Saktësia:** Mos shpik numra. Nëse OCR është i paqartë, thuaj "Teksti është i palexueshëm".

FORMATI I PËRGJIGJES:
- Përdor **Markdown** (Bold për emra/data).
- Cito burimin ku është e mundur (p.sh., "Sipas grafit...", "Në dokumentin X...").
"""

def _get_rag_service_instance(db: Any) -> Any:
    """
    Factory for RAG Service. 
    Note: We pass a dummy client because ChatService handles the generation 
    (the 'Brain'), while RAG Service handles the retrieval (the 'Eyes').
    """
    try:
        from app.services.albanian_rag_service import AlbanianRAGService
        from app.services.albanian_language_detector import AlbanianLanguageDetector
    except ImportError as e:
        logger.error(f"❌ Critical Import Error in Chat Service: {e}")
        return None

    try:
        detector = AlbanianLanguageDetector()
        # We don't need a real client inside RAG service for retrieval-only mode
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
    Orchestrates the Socratic Chat with Graph-Enhanced Retrieval.
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
        # 3. RETRIEVAL STEP (The "Eyes")
        rag_service = _get_rag_service_instance(db)
        
        context_dossier = ""
        if rag_service:
            # Retrieves Graph + Vector + Findings
            context_dossier = await rag_service.retrieve_context(
                query=user_query, 
                case_id=case_id, 
                document_ids=[document_id] if document_id else None
            )
            
        # 4. SAFETY CHECK
        if not context_dossier or len(context_dossier.strip()) < 50:
            logger.warning(f"⚠️ Empty Context for Case {case_id}")
            response_text = "⚠️ Nuk gjeta informacion relevant në dosje për këtë pyetje. Ju lutem provoni të formuloni pyetjen ndryshe ose bëni 'Skanim të Thellë' të dokumenteve."
        else:
            # 5. GENERATION STEP (The "Brain")
            # We explicitly label the dossier for the System Prompt to understand
            final_user_prompt = (
                f"=== DOSJA E KONTEKSTIT (BURIMET) ===\n{context_dossier}\n\n"
                f"=== PYETJA E PËRDORUESIT ===\n{user_query}"
            )

            if DEEPSEEK_API_KEY:
                client = AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url=OPENROUTER_BASE_URL)
                
                completion = await client.chat.completions.create(
                    model=OPENROUTER_MODEL,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT_KOSOVO},
                        {"role": "user", "content": final_user_prompt}
                    ],
                    temperature=0.0, # Zero temp to reduce hallucination
                    max_tokens=1000,
                    extra_headers={"HTTP-Referer": "https://juristi.tech", "X-Title": "Juristi AI Chat"}
                )
                
                content = completion.choices[0].message.content
                response_text = content if content is not None else "Gabim në gjenerim nga AI."
            else:
                response_text = "⚠️ Konfigurimi i AI mungon (API Key missing)."

    except Exception as e:
        logger.error(f"AI Error: {e}", exc_info=True)
        response_text = "Ndodhi një problem teknik gjatë procesimit."

    # 6. Save AI Response
    try:
        await db.cases.update_one(
            {"_id": oid},
            {"$push": {"chat_history": ChatMessage(role="ai", content=response_text, timestamp=datetime.now(timezone.utc)).model_dump()}}
        )
    except Exception:
        pass

    return response_text