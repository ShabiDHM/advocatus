# FILE: backend/app/services/drafting_service.py
# PHOENIX PROTOCOL - FIXED: BACKEND NOW HONORS FRONT-END PROMPT ENGINEERING
# 1. REMOVED: Overwriting system prompt with front-end's instructions embedded.
# 2. ADDED: Backend context (domain, RAG) provided as system prompt supplement.
# 3. PRESERVED: Front-end's anti-hallucination and template-specific formatting.
# 4. STATUS: Front-end now controls the document structure; backend enriches with law facts.

import os
import asyncio
import structlog
from datetime import datetime, timezone
from typing import Optional, Dict, List, AsyncGenerator
from pymongo.database import Database
from . import llm_service, vector_store_service

logger = structlog.get_logger(__name__)

# --- PHOENIX PROTOCOL: MULTI-DOMAIN KNOWLEDGE BASE (unchanged) ---
LEGAL_DOMAINS = {
    "FAMILY": {
        "keywords": ["shkurorëzim", "divorc", "alimentacion", "kujdestari", "fëmijë", "bashkëshort", "martesë"],
        "law": "Ligji Nr. 2004/32 për Familjen e Kosovës",
        "context_note": "Fokus: Interesi më i mirë i fëmijës, barazia bashkëshortore."
    },
    "CORPORATE": {
        "keywords": ["shpk", "aksion", "biznes", "bord", "divident", "falimentim", "statut", "marrëveshje themelimi", "ortak", "partneritet"],
        "law": "Ligji Nr. 06/L-016 për Shoqëritë Tregtare",
        "context_note": "Fokus: Përgjegjësia e kufizuar, qeverisja korporative."
    },
    "OBLIGATIONS": {
        "keywords": ["kontratë", "borxh", "dëm", "kredi", "faturë", "qira", "shitblerje", "marrëveshje", "përmbushje"],
        "law": "Ligji Nr. 04/L-077 për Marrëdhëniet e Detyrimeve (LMD)",
        "context_note": "Fokus: Pacta sunt servanda, kompensimi i dëmit."
    },
    "PROPERTY": {
        "keywords": ["pronë", "tokë", "banesë", "kadastër", "posedim", "hipotekë", "servitut", "shpronësim"],
        "law": "Ligji Nr. 03/L-154 për Pronësinë dhe të Drejtat Tjera Sendore",
        "context_note": "Fokus: Titulli juridik, mbrojtja e posedimit."
    },
    "LABOR": {
        "keywords": ["punë", "rrogë", "pagë", "pushim", "kontratë pune", "largim nga puna", "diskriminim", "orar"],
        "law": "Ligji Nr. 03/L-212 i Punës",
        "context_note": "Fokus: Të drejtat e punëtorit, procedurat disiplinore."
    },
    "CRIMINAL": {
        "keywords": ["vepër penale", "aktakuzë", "burgim", "gjobë", "kallëzim penal", "vjedhje", "mashtrim", "lëndim", "vrasje"],
        "law": "Kodi Penal i Republikës së Kosovës (KPRK) & Kodi i Procedurës Penale (KPPK)",
        "context_note": "Fokus: Prezumimi i pafajësisë, elementet e veprës penale."
    },
    "ADMINISTRATIVE": {
        "keywords": ["vendim administrativ", "komuna", "ministria", "leje", "licencë", "inspektorat", "konflikt administrativ"],
        "law": "Ligji për Procedurën e Përgjithshme Administrative",
        "context_note": "Fokus: Ligjshmëria, proporcionaliteti."
    }
}

def detect_legal_domain(text: str) -> Dict[str, str]:
    """
    Scans the input text for keywords to determine the primary legal domain.
    Returns a dictionary with the specific Law and Context Note.
    """
    text_lower = text.lower()
    scores = {key: 0 for key in LEGAL_DOMAINS}
    
    for domain, data in LEGAL_DOMAINS.items():
        for keyword in data["keywords"]:
            if keyword in text_lower:
                scores[domain] += 1
    
    best_match = max(scores, key=lambda k: scores[k])
    
    if scores[best_match] > 0:
        return LEGAL_DOMAINS[best_match]
    
    return {
        "law": "Legjislacioni i Aplikueshëm në Kosovë",
        "context_note": "Fokus: Zbatimi i përgjithshëm i ligjit dhe procedurës."
    }

async def stream_draft_generator(
    db: Database, 
    user_id: str, 
    case_id: Optional[str], 
    draft_type: str, 
    user_prompt: str
) -> AsyncGenerator[str, None]:
    
    logger.info(f"Drafting initiated", user=user_id, type=draft_type)
    
    # 1. Dynamic Domain Detection
    domain_context = detect_legal_domain(user_prompt)
    detected_law = domain_context["law"]
    context_note = domain_context["context_note"]
    
    logger.info(f"Domain Detected: {detected_law}")

    # 2. Smart Search Query
    search_query = f"{user_prompt} {detected_law} neni dispozita"

    # 3. Parallel Retrieval (RAG)
    try:
        tasks = [
            asyncio.to_thread(
                vector_store_service.query_case_knowledge_base, 
                user_id=user_id, 
                query_text=user_prompt, 
                n_results=8, 
                case_context_id=case_id
            ),
            asyncio.to_thread(
                vector_store_service.query_global_knowledge_base, 
                query_text=search_query, 
                n_results=10
            )
        ]
        
        results = await asyncio.gather(*tasks)
        case_facts_list = results[0] or []
        legal_articles_list = results[1] or []

    except Exception as e:
        logger.error(f"Vector Store Retrieval Failed: {e}")
        case_facts_list = []
        legal_articles_list = []

    # Format Retrieved Data for the LLM (as additional context)
    facts_block = "\n".join([f"- {f.get('text', '')}" for f in case_facts_list]) if case_facts_list else "Nuk u gjetën fakte specifike në dosje."
    laws_block = "\n".join([f"- {l.get('text', '')} (Burimi: {l.get('source', 'Ligji')})" for l in legal_articles_list]) if legal_articles_list else "Nuk u gjetën nene specifike në bazën ligjore."

    # 4. Construct System Prompt (Context Only) – NO OVERRIDING OF USER'S STRUCTURE
    system_prompt = f"""
    ROLI: Avokat i Licencuar në Republikën e Kosovës.
    DETYRA: Përdor kontekstin e mëposhtëm për të mbështetur përgjigjen tënde. Mos i ndrysho udhëzimet e formatit të dhëna nga përdoruesi.

    [KONTEKSTI LIGJOR I DETEKTUAR]
    Ligji primar i identifikuar: {detected_law}
    Udhëzim: {context_note}

    [MATERIALI LIGJOR NDIHMËS (NGA BAZA JONË E LIGJEVE)]
    {laws_block}

    [FAKTET NGA DOSJA E RASTIT (NËSE KA)]
    {facts_block}

    Përdor këtë informacion për t'i dhënë përgjigje kërkesës së përdoruesit. Mos shto pjesë strukturore që nuk janë kërkuar.
    """

    # 5. Stream Execution – PASS USER_PROMPT DIRECTLY AS THE USER MESSAGE
    full_content = ""
    try:
        # The user_prompt already contains the front-end's full instructions (including anti-hallucination, template structure)
        async for token in llm_service.stream_text_async(system_prompt, user_prompt, temp=0.2):
            full_content += token
            yield token
            
        # 6. Save Result (Async Fire-and-Forget)
        if full_content.strip() and case_id:
            asyncio.create_task(save_draft_result(db, user_id, case_id, draft_type, full_content))
            
    except Exception as e:
        logger.error(f"LLM Generation Failed: {e}")
        yield f"\n\n[GABIM SISTEMI]: {str(e)}"

async def save_draft_result(db: Database, user_id: str, case_id: str, draft_type: str, content: str):
    """Saves the generated draft to the database asynchronously."""
    try:
        await asyncio.to_thread(
            db.drafting_results.insert_one, 
            {
                "case_id": case_id, 
                "user_id": user_id, 
                "draft_type": draft_type, 
                "result_text": content, 
                "status": "COMPLETED", 
                "created_at": datetime.now(timezone.utc)
            }
        )
    except Exception as e:
        logger.error(f"Failed to save draft result: {e}")