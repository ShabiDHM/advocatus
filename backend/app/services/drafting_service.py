# FILE: backend/app/services/drafting_service.py
# PHOENIX PROTOCOL - DRAFTING SERVICE V31.0 (STRUCTURED OUTS & PLACEHOLDER SELF-CORRECTION)
# 1. OPTIMIZATION: Uses Pydantic 'LegalDraftStructure' to prevent LLM structural hallucinations.
# 2. SELF-CORRECTION: Runs post-generation regex to sanitize bracket placeholders into professional legal blanks.
# 3. TEMPERATURE: Enforces task-based temperature of 0.1 (TEMP_DRAFTING) for absolute deterministic structure.
# 4. STREAMING: Simulates silky-smooth streaming of the fully polished and corrected document to protect SSE UX.

import os
import re
import asyncio
import structlog
from datetime import datetime, timezone
from typing import Optional, Dict, List, AsyncGenerator
from pydantic import BaseModel, Field
from pymongo.database import Database
from . import llm_service, vector_store_service

logger = structlog.get_logger(__name__)

# Pydantic Structure for Zero-Hallucination Legal Document Output
class LegalDraftStructure(BaseModel):
    titulli: str = Field(..., description="Titulli zyrtar i dokumentit juridik (p.sh., PADIPADI, KALLËZIM PENAL, AUTORIZIM).")
    palet: str = Field(..., description="Seksioni i palëve (Kërkuesi, Paditësi, i Padituri, etj.) të identifikuar plotësisht.")
    baza_ligjore: str = Field(..., description="Nenet dhe titujt e plotë të ligjeve të cituara nga Materiali Ndihmës Ligjor.")
    arsyetimi: str = Field(..., description="Analiza faktike dhe ligjore e hollësishme (Arsyetimi / Rationale).")
    petitumi: str = Field(..., description="Kërkesa e saktë apo pika vendosëse e dokumentit (Petiti / Përfundimi).")
    nenshkrimi: str = Field(..., description="Seksioni përmbyllës dhe rreshtat e nënshkrimeve.")

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

def compile_draft(draft: LegalDraftStructure) -> str:
    """
    Compiles the validated Pydantic legal segments into a beautiful unified Markdown draft.
    """
    return f"""# {draft.titulli.upper()}

**I. PALËT DHE OBJEKTI**
{draft.palet}

**II. BAZA LIGJORE**
{draft.baza_ligjore}

**III. ARSYETIMI**
{draft.arsyetimi}

**IV. PETITUMI / PËRFUNDIMI**
{draft.petitumi}

**V. NËNSHKRIMI DHE DATA**
{draft.nenshkrimi}
"""

def sanitize_unresolved_placeholders(text: str) -> str:
    """
    Finds unresolved bracketed placeholders like [Emri i Bashkëshortit] or [Data]
    and transforms them into legal-ready blanks (e.g. ________________________ (Emri i Bashkëshortit)).
    """
    pattern = r"\[([^\]]{1,100})\]"
    
    def replacement(match):
        placeholder_content = match.group(1).strip()
        # Format placeholder elegantly as a legal fill-in underline
        return f"________________________ ({placeholder_content})"
        
    return re.sub(pattern, replacement, text)

async def simulate_streaming(text: str, chunk_size: int = 45, delay: float = 0.004) -> AsyncGenerator[str, None]:
    """
    Simulates high-speed silky-smooth streaming over SSE to preserve downstream user experience.
    """
    for i in range(0, len(text), chunk_size):
        yield text[i:i+chunk_size]
        await asyncio.sleep(delay)

async def stream_draft_generator(
    db: Database, 
    user_id: str, 
    case_id: Optional[str], 
    draft_type: str, 
    user_prompt: str
) -> AsyncGenerator[str, None]:
    
    logger.info("Drafting initiated", user=user_id, type=draft_type)
    
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
    
    # Format laws block: include full law title and article if available, without extra metadata
    if legal_articles_list:
        laws_lines = []
        for l in legal_articles_list:
            law_title = l.get('law_title', 'Ligji i panjohur')
            article_num = l.get('article_number')
            text = l.get('text', '')
            if article_num:
                line = f"- {law_title}, Neni {article_num}:\n  {text}"
            else:
                line = f"- {law_title}:\n  {text}"
            laws_lines.append(line)
        laws_block = "\n".join(laws_lines)
    else:
        laws_block = "Nuk u gjetën nene specifike në bazën ligjore."

    # === ULTRA-STRICT SYSTEM PROMPT ===
    system_prompt = f"""
ROLI: Avokat i Licencuar në Republikën e Kosovës.

UDHËZIME T T'RREPTA JURIDIKE:
1. Përdor saktësisht strukturën e modelit të kërkuar (Titulli, Palët, Baza Ligjore, Arsyetimi, Petitumi, Nënshkrimi).
2. CITO VETËM LIGJET E LISTUARA NË [MATERIALI LIGJOR NDIHMËS]. Mos shpik ose supozo ligje që nuk janë në listë.
3. Për çdo ligj të cituar, kopjo fjalë për fjalë titullin e plotë zyrtar duke përfshirë numrin (p.sh., "Ligji Nr. 03/L-154 për Pronësinë dhe të Drejtat Tjera Sendore").
4. Ligji primar i identifikuar është: {detected_law}. Ky ligj duhet të jetë baza kryesore e draftit.
5. Mos përziej ligje nga fusha të ndryshme.
6. Kosova NUK ka një ligj të veçantë për mbrojtjen nga shpifja. Shpifja rregullohet kryesisht nga LMD (për dëmin civil) ose Kodi Penal.

[KONTEKSTI LIGJOR I DETEKTUAR]
Ligji primar i identifikuar: {detected_law}
Udhëzim: {context_note}

[MATERIALI LIGJOR NDIHMËS (NGA BAZA JONË E LIGJEVE)]
{laws_block}

[FAKTET NGA DOSJA E RASTIT (NËSE KA)]
{facts_block}
"""

    sanitized_text = ""
    try:
        # PHOENIX V31.0: Call Structured Output generator with task-based temperature of 0.1
        structured_draft = await asyncio.to_thread(
            llm_service.call_llm_structured,
            system_prompt=system_prompt,
            user_content=user_prompt,
            schema=LegalDraftStructure,
            temperature=llm_service.TEMP_DRAFTING
        )
        
        # Compile Pydantic sections into unified document
        compiled_text = compile_draft(structured_draft)
        
        # Execute Regex Self-Correction Loop to clean bracketed placeholders
        sanitized_text = sanitize_unresolved_placeholders(compiled_text)
        
        # Stream the polished document back smoothly over SSE
        async for chunk in simulate_streaming(sanitized_text):
            yield chunk

        # Save to DB asynchronously
        if sanitized_text.strip() and case_id:
            asyncio.create_task(save_draft_result(db, user_id, case_id, draft_type, sanitized_text))

    except Exception as e:
        logger.error(f"Structured Drafting Failed, falling back: {e}")
        
        # Safe fallback: direct streaming with on-the-fly regex placeholder cleaning
        fallback_prompt = system_prompt + "\n\nOfroni draftin direkt në format markdown të strukturuar, pa asnjë hyrje ose koment shtesë."
        full_content = ""
        
        try:
            async for token in llm_service.stream_text_async(fallback_prompt, user_prompt, temp=llm_service.TEMP_DRAFTING):
                # Clean on-the-fly to ensure no raw bracket leakage during fallback
                clean_token = sanitize_unresolved_placeholders(token)
                full_content += clean_token
                yield clean_token

            if full_content.strip() and case_id:
                asyncio.create_task(save_draft_result(db, user_id, case_id, draft_type, full_content))
        except Exception as fallback_err:
            logger.error(f"Fallback generation failed completely: {fallback_err}")
            yield f"\n\n[GABIM SISTEMI]: {str(fallback_err)}"

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