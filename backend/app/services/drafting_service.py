# FILE: backend/app/services/drafting_service.py
# PHOENIX PROTOCOL - JURISTI HYDRA DRAFTING V33.0 (MULTI-DOMAIN INTELLIGENCE)
# 1. REMOVED: Hardcoded 'Template -> Law' mapping.
# 2. ADDED: Dynamic Domain Detection. The system scans the prompt for keywords (e.g., 'borxh', 'prone', 'femije') to select the right Law context.

import os
import io
import asyncio
import structlog
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, AsyncGenerator
from pymongo.database import Database
from . import llm_service, vector_store_service

logger = structlog.get_logger(__name__)

# --- TIER 1: DYNAMIC DOMAIN DETECTION ---
# Instead of hardcoding "Padi" -> "Family Law", we look at the CONTENT.
# This allows a "Padi" to be about Family, Property, or Contracts depending on the user's text.
DOMAIN_KEYWORDS = {
    # Family Law
    "familj": "Ligji për Familjen",
    "alimentacion": "Ligji për Familjen Neni 330",
    "shkuror": "Ligji për Familjen",
    "fëmij": "Ligji për Familjen",
    "martes": "Ligji për Familjen",
    "kujdestari": "Ligji për Familjen",
    
    # Contract/Obligations (LMD)
    "borxh": "Ligji për Marrëdhëniet e Detyrimeve (LMD)",
    "kontrat": "Ligji për Marrëdhëniet e Detyrimeve (LMD)",
    "dëmi": "Ligji për Marrëdhëniet e Detyrimeve",
    "fatur": "Ligji për Marrëdhëniet e Detyrimeve",
    "qira": "Ligji për Marrëdhëniet e Detyrimeve",
    "shitblerj": "Ligji për Marrëdhëniet e Detyrimeve",
    
    # Property Law
    "pron": "Ligji për Pronësinë dhe të Drejtat Tjera Sendore",
    "banes": "Ligji për Pronësinë",
    "paluajtshmëri": "Ligji për Pronësinë",
    
    # Labor Law
    "punë": "Ligji i Punës Nr. 03/L-212",
    "rrog": "Ligji i Punës",
    "pagë": "Ligji i Punës",
    "pushim": "Ligji i Punës",
    "largim": "Ligji i Punës",
    
    # Procedure (Always relevant)
    "përmbarim": "Ligji për Procedurën Përmbarimore",
    "prapësim": "Ligji për Procedurën Përmbarimore",
    "ankes": "Ligji i Procedurës Kontestimore"
}

def get_smart_search_query(user_prompt: str, draft_type: str) -> str:
    """
    Analyzes the user input to construct a targeted legal search query.
    Example: Input "Dua padi për borxh" -> Query "Ligji për Marrëdhëniet e Detyrimeve (LMD) borxh"
    """
    detected_laws = []
    prompt_lower = user_prompt.lower()
    
    # Scan prompt for domain keywords
    for keyword, law in DOMAIN_KEYWORDS.items():
        if keyword in prompt_lower:
            detected_laws.append(law)
    
    # De-duplicate
    detected_laws = list(set(detected_laws))
    
    if detected_laws:
        # Smart Mode: We found specific domains
        smart_query = f"{' '.join(detected_laws)} {draft_type} Neni"
        return smart_query
    else:
        # Fallback Mode: Broad search
        return f"{draft_type} baza ligjore Neni dispozitat"

async def stream_draft_generator(db: Database, user_id: str, case_id: Optional[str], draft_type: str, user_prompt: str) -> AsyncGenerator[str, None]:
    logger.info(f"Hydra Drafting V33.0 initiated", user=user_id, type=draft_type)
    
    # 1. Smart Query Construction
    targeted_law_query = get_smart_search_query(user_prompt, draft_type)
    logger.info(f"Context Strategy: {targeted_law_query}")

    # 2. High-Density Retrieval (Parallel)
    tasks = [
        # Search Case Files (Facts)
        asyncio.to_thread(vector_store_service.query_case_knowledge_base, user_id=user_id, query_text=user_prompt, n_results=10, case_context_id=case_id),
        # Search Law Database (Legal Basis) using the SMART QUERY
        asyncio.to_thread(vector_store_service.query_global_knowledge_base, query_text=targeted_law_query, n_results=12)
    ]
    results = await asyncio.gather(*tasks)
    
    case_facts = results[0]
    legal_articles = results[1]

    facts_block = "\n".join([f"- {f.get('text')}" for f in case_facts]) if case_facts else "Nuk u gjetën fakte specifike."
    laws_block = "\n".join([f"- {l.get('text')} (Burimi: {l.get('source')})" for l in legal_articles]) if legal_articles else "Nuk u gjetën nene specifike."

    # 3. System Mandate
    system_prompt = f"""
    ROLI: Avokat Ekspert.
    DETYRA: Hartimi i "{draft_type.upper()}".
    
    [MATERIALI LIGJOR I GJETUR - PËRDOR KËTO NENE]:
    {laws_block}
    
    [FAKTET E RASTIT]:
    {facts_block}
    
    UDHËZIME STRUKTURORE:
    1. Fillo me: # [TITULLI]
    2. Seksioni: ## BAZA LIGJORE
       - Këtu LISTO nenet konkrete që i gjete më lart. Mos shpik.
       - Nëse sheh Nenin 330, 10, ose ndonjë numër tjetër në tekstin e mësipërm, përdore.
    3. Seksioni: ## ARSYETIMI
       - Lidh faktet me ligjin. Cito ligjin në formatin: **[Ligji, Neni X]**.
    
    MANDATI: Mos bëj "parroting" (përsëritje të thatë). Argumento juridikisht duke përdorur nenet e gjetura.
    
    INPUTI I PËRDORUESIT: {user_prompt}
    """
    
    full_content = ""
    async for token in llm_service.stream_text_async(system_prompt, "Fillo hartimin.", temp=0.1):
        full_content += token
        yield token
    
    if full_content.strip() and case_id:
        await asyncio.to_thread(
            db.drafting_results.insert_one, 
            {
                "case_id": case_id, 
                "user_id": user_id, 
                "draft_type": draft_type, 
                "result_text": full_content, 
                "status": "COMPLETED", 
                "created_at": datetime.now(timezone.utc)
            }
        )