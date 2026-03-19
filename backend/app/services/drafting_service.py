# FILE: backend/app/services/drafting_service.py
# PHOENIX PROTOCOL - ULTIMATE FIX: INCLUDE FULL LAW TITLE IN CONTEXT
# 1. ADDED: Law title and article number to the laws_block.
# 2. STRENGTHENED: Instruction to use the exact title from context.
# 3. RETAINED: All previous improvements.

import os
import asyncio
import structlog
from datetime import datetime, timezone
from typing import Optional, Dict, List, AsyncGenerator
from pymongo.database import Database
from . import llm_service, vector_store_service

logger = structlog.get_logger(__name__)

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
    
    domain_context = detect_legal_domain(user_prompt)
    detected_law = domain_context["law"]
    context_note = domain_context["context_note"]
    logger.info(f"Domain Detected: {detected_law}")

    search_query = f"{user_prompt} {detected_law} neni dispozita"

    # Parallel RAG retrieval
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

    facts_block = "\n".join([f"- {f.get('text', '')}" for f in case_facts_list]) if case_facts_list else "Nuk u gjetën fakte specifike në dosje."
    
    # Format laws block with full metadata
    if legal_articles_list:
        laws_lines = []
        for l in legal_articles_list:
            law_title = l.get('law_title', 'Ligji i panjohur')
            article_num = l.get('article_number', 'neni i panjohur')
            text = l.get('text', '')
            source = l.get('source', 'Ligji')
            laws_lines.append(f"- Ligji: {law_title}, Neni {article_num}\n  {text}\n  (Burimi: {source})")
        laws_block = "\n".join(laws_lines)
    else:
        laws_block = "Nuk u gjetën nene specifike në bazën ligjore."

    # === STRENGTHENED SYSTEM PROMPT ===
    system_prompt = f"""
ROLI: Avokat i Licencuar në Republikën e Kosovës.

UDHËZIME TË RREPTA:
1. **Ndiq me përpikëri strukturën e kërkuar nga përdoruesi** – përdor saktësisht titujt që ai ka specifikuar (p.sh., PALËT:, OBJEKTI:, BAZA LIGJORE:, etj.). Mos i ndrysho.
2. **Mos shpik kurrë ligje ose nene** – nëse nuk je i sigurt për një citim, përdor një vendmbajtës si "[Neni përkatës i Ligjit ...]".
3. **Përdor ligjin e identifikuar si primar: {detected_law}.** Ky është ligji kryesor që duhet të përdorësh në citime. Materialet e tjera ligjore (nëse jepen) janë vetëm ndihmëse dhe duhet të përdoren vetëm nëse përputhen me këtë ligj ose janë absolutisht të nevojshme për të plotësuar përgjigjen.
4. **Mos përziej ligje nga fusha të ndryshme** – për shembull, mos përdor ligjin tregtar në një mosmarrëveshje pronësore, përveç nëse përdoruesi i referohet qartë atyre.
5. **Për çdo citim, përdor formatin e plotë zyrtar të ligjit, duke përfshirë numrin, saktësisht siç shfaqet në kontekstin më poshtë (p.sh., "Ligji Nr. 03/L-154 për Pronësinë dhe të Drejtat Tjera Sendore").** Nëse numri i nenit nuk dihet, përdor "Neni përkatës".
6. Përdor kontekstin e mëposhtëm VETËM për të pasuruar përgjigjen, jo për të ndryshuar format.

[KONTEKSTI LIGJOR I DETEKTUAR]
Ligji primar i identifikuar: {detected_law}
Udhëzim: {context_note}

[MATERIALI LIGJOR NDIHMËS (NGA BAZA JONË E LIGJEVE)]
{laws_block}

[FAKTET NGA DOSJA E RASTIT (NËSE KA)]
{facts_block}

Tani, përgjigju kërkesës së përdoruesit duke ndjekur me përpikëri udhëzimet e tij për format dhe duke shmangur çdo trillim ligjor.
"""

    full_content = ""
    try:
        async for token in llm_service.stream_text_async(system_prompt, user_prompt, temp=0.2):
            full_content += token
            yield token

        if full_content.strip() and case_id:
            asyncio.create_task(save_draft_result(db, user_id, case_id, draft_type, full_content))
    except Exception as e:
        logger.error(f"LLM Generation Failed: {e}")
        yield f"\n\n[GABIM SISTEMI]: {str(e)}"

async def save_draft_result(db: Database, user_id: str, case_id: str, draft_type: str, content: str):
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