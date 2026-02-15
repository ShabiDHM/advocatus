# FILE: backend/app/services/drafting_service.py
# PHOENIX PROTOCOL - JURISTI HYDRA DRAFTING V29.0 (STRICT DETERMINISTIC CITATION)
# 1. FIX: Explicitly prohibited placeholders ("Neni përkatës", brackets, placeholders).
# 2. FIX: Enforced Markdown Hierarchy (# and ##) to match Frontend V10.1 design.
# 3. FIX: Mandatory specific citation extraction from Law Context.
# 4. STATUS: 100% Deterministic legal output mandate.

import os
import io
import asyncio
import structlog
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, AsyncGenerator
from pymongo.database import Database
from . import llm_service, vector_store_service

logger = structlog.get_logger(__name__)

async def stream_draft_generator(db: Database, user_id: str, case_id: Optional[str], draft_type: str, user_prompt: str) -> AsyncGenerator[str, None]:
    logger.info(f"Hydra Drafting V29.0 initiated", user=user_id)
    
    # 1. High-Density Retrieval
    tasks = [
        asyncio.to_thread(vector_store_service.query_case_knowledge_base, user_id=user_id, query_text=user_prompt, n_results=15, case_context_id=case_id),
        asyncio.to_thread(vector_store_service.query_global_knowledge_base, query_text=user_prompt, n_results=15)
    ]
    results = await asyncio.gather(*tasks)
    
    facts_block = "\n".join([f"- **DOKUMENTI: {f.get('source')} (Fq. {f.get('page')}):** {f.get('text')}" for f in results[0]])
    laws_block = "\n".join([f"- **LIGJI: {l.get('source')}:** {l.get('text')}" for l in results[1]])
    
    # 2. Strict Legal Mandate Construction
    system_prompt = f"""
    MISIONI: Ti je një Kryeavokat i nivelit Senior në Republikën e Kosovës me 20 vite përvojë në shkrimin juridik.
    DETYRA: Harto një {draft_type.upper()} profesionale, të detajuar dhe të saktë.

    PROTOKOLLI I PANEGOCIUESHËM:
    1. NDALOHET përdorimi i placeholder-ave si "Neni përkatës", "Neni përkatës i Ligjit...", "Neni [X]", ose çdo lloj kllape kërkimore.
    2. Duhet të nxjerrësh numrin e saktë të Nenit dhe Paragrafit nga teksti i ofruar në [LIGJET E DISPONUESHME]. Nëse teksti përmban një numër neni, përdore atë.
    3. Secili argument duhet të jetë i lidhur direkt me një Nen ekzakt.
    4. Nëse një ligj përmendet, formatimi i detyrueshëm është: [Emri i Ligjit, Neni X](doc://ligji).

    STRUKTURA E FORMATIMIT (Për përputhje me sistemin):
    - Përdor # për Titullin e Gjykatës dhe llojin e dokumentit (p.sh. # GJYKATA THEMELORE NË PRISHTINË - PADI).
    - Përdor ## për Titujt e Seksioneve (BAZA LIGJORE, FAKTET, KËRKESAPADIA, PROVAT).
    - Përdor bold (**) për emrat e palëve, numrat e lëndëve, dhe shumat monetare.
    - Teksti duhet të jetë i strukturuar në paragrafë të numëruar aty ku është e përshtatshme.

    KONTEKSTI I RASTIT (FAKTET):
    {facts_block}
    
    LIGJET E DISPONUESHME (BURIMI I CITIMEVE):
    {laws_block}
    
    UDHËZIMI I OPERATORIT: {user_prompt}
    
    MANDATI FINAL: Prodhoni vetëm dokumentin profesional përfundimtar. Mos përdor fjali hyrëse ose shpjegime. Dokumenti duhet të jetë gati për t'u dorëzuar në Gjykatë.
    """
    
    full_content = ""
    # Setting temp to 0.0 for maximum determinism and citation accuracy
    async for token in llm_service.stream_text_async(system_prompt, "Filloni hartimin profesional tani pa asnjë placeholder.", temp=0.0):
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