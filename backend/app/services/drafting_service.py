# FILE: backend/app/services/drafting_service.py
# PHOENIX PROTOCOL - JURISTI HYDRA DRAFTING V30.0 (MULTI-TEMPLATE INTELLIGENCE)
# 1. ADDED: Legal Persona Mapper for all 15+ new templates.
# 2. FIXED: Structural hints for Corporate vs. Litigation documents.
# 3. RETAINED: Strict Deterministic Citation Protocol (No placeholders).
# 4. RETAINED: V16.3 High-density RAG (n=15).

import os
import io
import asyncio
import structlog
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, AsyncGenerator
from pymongo.database import Database
from . import llm_service, vector_store_service

logger = structlog.get_logger(__name__)

# Template context mapper for Kosovo Jurisdiction
TEMPLATE_MAPPER = {
    "padi": "Padi (Paditëse) - Fokusohu në qartësinë e kërkesëpadisë dhe bazën ligjore procedurale.",
    "pergjigje": "Përgjigje në Padi - Fokusohu në kundërshtimin e fakteve dhe prapësimet ligjore.",
    "kunderpadi": "Kundërpadi - Fokusohu në kërkesat e reja që rrjedhin nga e njëjta marrëdhënie juridike.",
    "ankese": "Ankesë Gjyqësore - Fokusohu në shkeljet procedurale dhe zbatimin e gabuar të së drejtës materiale.",
    "prapësim": "Prapësim ndaj Urdhrit Përmbarimor - Fokusohu në Ligjin për Procedurën Përmbarimore.",
    "nda": "Marrëveshje për Mos-shpalosje (NDA) - Fokusohu në konfidencialitetin, penalitetet dhe kohëzgjatjen.",
    "mou": "Memorandum Mirëkuptimi (MoU) - Fokusohu në qëllimet e përbashkëta dhe natyrën jo-detyruese (ose pjesërisht detyruese).",
    "shareholders": "Marrëveshje e Aksionarëve - Fokusohu në qeverisjen korporative, vendimmarrjen dhe transferimin e aksioneve.",
    "sla": "Marrëveshje mbi Nivelin e Shërbimit (SLA) - Fokusohu në KPI-të, përgjegjësitë dhe zgjidhjen e kontesteve.",
    "employment_contract": "Kontratë Pune - Fokusohu në Ligjin e Punës, orarin, pushimet dhe detyrat specifike.",
    "termination_notice": "Njoftim për Shkëputje të Kontratës - Fokusohu në arsyetimin ligjor dhe afatet e njoftimit.",
    "warning_letter": "Vërejtje me shkrim - Fokusohu në procedurën disiplinore dhe pasojat ligjore.",
    "terms_conditions": "Kushtet e Përdorimit (T&C) - Fokusohu në mbrojtjen e pronësisë intelektuale dhe kufizimin e përgjegjësisë.",
    "privacy_policy": "Politika e Privatësisë - Fokusohu në Ligjin për Mbrojtjen e Të Dhënave Personale (GDPR compliant).",
    "lease_agreement": "Kontratë Qiraje - Fokusohu në objektin, çmimin, mirëmbajtjen dhe kushtet e lirimit.",
    "sales_purchase": "Kontratë Shitblerje - Fokusohu në bartjen e pronësisë, çmimin dhe garancitë për të metat.",
    "power_of_attorney": "Autorizim (Prokurë) - Fokusohu në fushëveprimin e autorizimeve dhe vlefshmërinë kohore."
}

async def stream_draft_generator(db: Database, user_id: str, case_id: Optional[str], draft_type: str, user_prompt: str) -> AsyncGenerator[str, None]:
    logger.info(f"Hydra Drafting V30.0 initiated", user=user_id, type=draft_type)
    
    # 1. Categorize instructions based on template
    legal_focus = TEMPLATE_MAPPER.get(draft_type, "Hartim Ligjor i Përgjithshëm.")
    
    # 2. High-Density Retrieval
    tasks = [
        asyncio.to_thread(vector_store_service.query_case_knowledge_base, user_id=user_id, query_text=user_prompt, n_results=15, case_context_id=case_id),
        asyncio.to_thread(vector_store_service.query_global_knowledge_base, query_text=user_prompt, n_results=15)
    ]
    results = await asyncio.gather(*tasks)
    
    facts_block = "\n".join([f"- **DOKUMENTI: {f.get('source')} (Fq. {f.get('page')}):** {f.get('text')}" for f in results[0]])
    laws_block = "\n".join([f"- **LIGJI: {l.get('source')}:** {l.get('text')}" for l in results[1]])
    
    # 3. Enhanced System Mandate
    system_prompt = f"""
    MISIONI: Ti je një Kryeavokat Senior në Republikën e Kosovës. 
    OBJEKTIVI: {legal_focus.upper()}

    PROTOKOLLI I PANEGOCIUESHËM:
    1. NDALOHET përdorimi i placeholder-ave si "Neni përkatës" ose kllapa [ ]. Gjej nenin ekzakt në materialin e ofruar.
    2. Formatimi i detyrueshëm i citimit: [Emri i Ligjit, Neni X](doc://ligji).
    3. STRUKTURA: Përdor # për titullin kryesor dhe ## për seksionet.
    4. GJUHA: Shqipe profesionale juridike (Gjuha standarde).

    KONTEKSTI I RASTIT:
    {facts_block}
    
    LIGJET E DISPONUESHME:
    {laws_block}
    
    UDHËZIMI SPECIFIK I OPERATORIT: {user_prompt}
    
    MANDATI FINAL: Prodhoni vetëm dokumentin. Pa hyrje, pa komente.
    """
    
    full_content = ""
    async for token in llm_service.stream_text_async(system_prompt, "Filloni hartimin tani.", temp=0.0):
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