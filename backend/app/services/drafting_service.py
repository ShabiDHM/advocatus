# FILE: backend/app/services/drafting_service.py
import os
import asyncio
import structlog
from datetime import datetime, timezone
from typing import Optional, Dict, List, AsyncGenerator
from pymongo.database import Database
from . import llm_service, vector_store_service

logger = structlog.get_logger(__name__)

# --- PHOENIX PROTOCOL: MULTI-DOMAIN KNOWLEDGE BASE ---
# Maps specific keywords to Kosovo Legal Frameworks.
LEGAL_DOMAINS = {
    "FAMILY": {
        "keywords": ["shkurorëzim", "divorc", "alimentacion", "kujdestari", "fëmijë", "bashkëshort", "martesë"],
        "law": "Ligji Nr. 2004/32 për Familjen e Kosovës",
        "context_note": "Fokus: Interesi më i mirë i fëmijës, barazia bashkëshortore."
    },
    "CORPORATE": {
        "keywords": ["shpk", "aksion", "biznes", "bord", "divident", "falimentim", "statut", "marrëveshje themelimi"],
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
    
    # Calculate scores based on keyword frequency
    for domain, data in LEGAL_DOMAINS.items():
        for keyword in data["keywords"]:
            if keyword in text_lower:
                scores[domain] += 1
    
    # Find the domain with the highest score
    best_match = max(scores, key=lambda k: scores[k])  # FIXED: lambda ensures int return
    
    if scores[best_match] > 0:
        return LEGAL_DOMAINS[best_match]
    
    # Default fallback if no specific keywords are found
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
    # We combine the user's specific request with the detected law to get the most relevant articles.
    search_query = f"{user_prompt} {detected_law} neni dispozita"

    # 3. Parallel Retrieval (RAG)
    try:
        tasks = [
            # Retrieve Case Facts (if a case is selected)
            asyncio.to_thread(
                vector_store_service.query_case_knowledge_base, 
                user_id=user_id, 
                query_text=user_prompt, 
                n_results=8, 
                case_context_id=case_id
            ),
            # Retrieve Legal Articles (Global Knowledge)
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
        # Graceful degradation: Proceed without RAG data rather than crashing
        case_facts_list = []
        legal_articles_list = []

    # Format Retrieved Data for the LLM
    facts_block = "\n".join([f"- {f.get('text', '')}" for f in case_facts_list]) if case_facts_list else "Përdor vetëm informacionin nga prompti i përdoruesit."
    laws_block = "\n".join([f"- {l.get('text', '')} (Burimi: {l.get('source', 'Ligji')})" for l in legal_articles_list]) if legal_articles_list else "Referoju njohurive të tua të përgjithshme për ligjet e Kosovës."

    # 4. Construct System Mandate (Aligned with Frontend 'Kosovo Style')
    system_prompt = f"""
    ROLI: Avokat i Licencuar në Republikën e Kosovës.
    DETYRA: Hartimi i dokumentit "{draft_type.upper()}" sipas standardeve të Gjykatës.
    
    KONTEKSTI LIGJOR I DETEKTUAR:
    - Ligji Primar: {detected_law}
    - Udhëzim: {context_note}
    
    [MATERIALI LIGJOR NDITMËS - RAG]:
    {laws_block}
    
    [FAKTET NGA DOSJA E RASTIT]:
    {facts_block}
    
    UDHËZIME PËR STRUKTURËN (E DETYRUESHME):
    1. HEADER: [GJYKATA THEMELORE...] (Në qendër, me shkronja të mëdha).
    2. PALËT: Paditës/Propozues vs I Paditur/Kundërshtar.
    3. OBJEKTI: Përshkrim i shkurtër (psh. Padi për...).
    4. TITULLI: "{draft_type.upper()}" (Në qendër, Bold).
    5. BAZA LIGJORE: Cito saktë nenet nga "{detected_law}" ose materialet e gjetura.
    6. ARSYETIMI: Lidh faktet me ligjin. Përdor ton bindës dhe profesional.
    7. PETITUMI / PËRFUNDIMI: Kërkesa konkrete ndaj gjykatës.
    8. NËNSHKRIMI: Vendi, Data, Avokati.

    RREGULLA:
    - Përdor gjuhën standarde shqipe (ligjore).
    - Mos shpik nene ligjore in-ekzistente.
    - Nëse nuk ka fakte të mjaftueshme, lëre hapësirë [________] për t'u plotësuar.
    
    INPUTI I PËRDORUESIT:
    {user_prompt}
    """

    # 5. Stream Execution
    full_content = ""
    try:
        async for token in llm_service.stream_text_async(system_prompt, "Fillo hartimin e dokumentit tani.", temp=0.2):
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