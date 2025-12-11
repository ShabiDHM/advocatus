# FILE: backend/app/services/chat_service.py
# PHOENIX PROTOCOL - CHAT SERVICE V13.0 (SMART PROMPT)
# 1. LOGIC: Implemented "Chain of Thought" (CoT) System Prompt.
# 2. BEHAVIOR: Forces AI to think in steps (Analyze -> Link -> Conclude).
# 3. SAFETY: Strict anti-hallucination rules for Kosovo Jurisdiction.

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

# --- KOSOVO SMART PROMPT (CHAIN OF THOUGHT) ---
SYSTEM_PROMPT_KOSOVO = """
Ti je "Juristi AI", një Partner i Lartë Ligjor i specializuar në ligjet e REPUBLIKËS SË KOSOVËS.
Qëllimi yt është të ofrosh këshilla ligjore të sakta, të bazuara në fakte dhe të cituara mirë.

PROTOKOLLI I TË MENDUARIT (Zgjidhja Hap-pas-Hapi):
1. **ANALIZA:** Identifiko saktësisht se çfarë po kërkon klienti. Cila është çështja kryesore juridike?
2. **KËRKIMI:** Skano tekstin e dhënë më poshtë ("KONTEKSTI I DOSJES") për fakte relevante, data dhe nene ligjore.
3. **LIDHJA LOGJIKE:** Lidh faktet e gjetura me ligjet e aplikueshme të Kosovës.
4. **PËRFUNDIMI:** Përgjigju pyetjes direkt dhe qartë.

RREGULLAT E PANEGOCIUESHME:
1. **JURISDIKSIONI:** Përdor VETËM ligjet e KOSOVËS. Injoro çdo referencë nga Shqipëria ose legjislacioni i vjetër jugosllav nëse nuk kërkohet specifikisht.
2. **E VËRTETA E VETME:** Përgjigju VETËM bazuar në informacionin e dhënë në "KONTEKSTI I DOSJES".
3. **ANTI-HALUCINACION:** Nëse informacioni mungon në dokumente, thuaj: "Nuk kam informacion të mjaftueshëm në dokumentet e ofruara për të dhënë një përgjigje të saktë." MOS SHPIK NENE.
4. **CITIMET:** Çdo pohim duhet të mbështetet nga një citim (psh: "Sipas Nenit 4 të Kontratës...").

STILI I PËRGJIGJES:
- Profesional, i drejtpërdrejtë, pa fjalë të tepërta.
- Përdor 'Markdown' për të theksuar pikat kryesore (**bold**).
"""

def _get_rag_service_instance(db: Any) -> Any:
    """
    Factory to get the RAG Service instance for RETRIEVAL ONLY.
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
    Orchestrates the Socratic Chat using a Strict Retrieval-then-Generate model.
    """
    try:
        oid = ObjectId(case_id)
        user_oid = ObjectId(user_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    # 1. Verify user has access to the case
    case = await db.cases.find_one({"_id": oid, "owner_id": user_oid})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found or user does not have access.")

    # 2. Save User Message
    try:
        await db.cases.update_one(
            {"_id": oid},
            {"$push": {"chat_history": ChatMessage(role="user", content=user_query, timestamp=datetime.now(timezone.utc)).model_dump()}}
        )
    except Exception as e:
        logger.error(f"DB Write Error (User Message): {e}")
    
    response_text: str = "" 
    try:
        # 3. RETRIEVAL STEP
        rag_service = _get_rag_service_instance(db)
        
        context_dossier = ""
        if rag_service:
            # We specifically look for chunks related to the user query
            context_dossier = await rag_service.retrieve_context(
                query=user_query, 
                case_id=case_id, 
                document_ids=[document_id] if document_id else None
            )
        else:
            logger.warning("RAG Service unavailable, proceeding without context.")

        # 4. GENERATION STEP
        if not context_dossier:
            context_dossier = "Nuk u gjetën të dhëna specifike në dokumente. Përdor vetëm njohuritë e përgjithshme ligjore të KOSOVËS, por theksoje që po flet në përgjithësi."

        final_user_prompt = (
            f"=== KONTEKSTI I DOSJES (Provat dhe Ligjet) ===\n{context_dossier}\n\n"
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
                temperature=0.1, # Lower temperature for higher precision
                max_tokens=1000,
                extra_headers={"HTTP-Referer": "https://juristi.tech", "X-Title": "Juristi AI Chat"}
            )
            
            content = completion.choices[0].message.content
            response_text = content if content is not None else "Më vjen keq, nuk munda të gjeneroj një përgjigje."
        else:
            response_text = "⚠️ Konfigurimi i AI mungon (API Key missing)."

    except Exception as e:
        logger.error(f"AI Processing Error: {e}", exc_info=True)
        response_text = "Më vjen keq, pata një problem teknik gjatë përpunimit të përgjigjes."

    # 5. Save AI Response
    try:
        await db.cases.update_one(
            {"_id": oid},
            {"$push": {"chat_history": ChatMessage(role="ai", content=response_text, timestamp=datetime.now(timezone.utc)).model_dump()}}
        )
    except Exception as e:
        logger.error(f"DB Write Error (AI Response): {e}")

    return response_text