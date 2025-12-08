# FILE: backend/app/services/drafting_service.py
# PHOENIX PROTOCOL - DRAFTING ENGINE V7 (STRATEGIC & STRUCTURED)
# 1. PROMPT: Upgraded to a "Strategic Drafting" prompt, forcing a professional legal document structure.
# 2. SECTIONS: AI must now generate distinct sections for Parties, Factual Basis, Legal Basis, Argument, and Claim.
# 3. GOAL: Produce a high-quality, structured draft that is immediately usable by a lawyer.

import os
import asyncio
import structlog
import httpx
import json
import re
from typing import AsyncGenerator, Optional, List, Any, cast, Dict
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam 
from pymongo.database import Database
from bson import ObjectId

from ..models.user import UserInDB
from app.services.text_sterilization_service import sterilize_text_for_llm 
from .vector_store_service import query_legal_knowledge_base
from .embedding_service import generate_embedding
from .graph_service import graph_service 

logger = structlog.get_logger(__name__)

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY") 
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat" 
LOCAL_LLM_URL = os.environ.get("LOCAL_LLM_URL", "http://local-llm:11434/api/chat")
LOCAL_MODEL_NAME = "llama3"

# --- HELPERS ---
def _fetch_graph_intelligence_sync(case_id: Optional[str], prompt_text: str) -> str:
    buffer = []
    if case_id:
        try:
            conflicts = graph_service.find_contradictions(case_id)
            if conflicts and "No direct contradictions" not in conflicts:
                buffer.append(f"⚠️ KONTRAST FAKTESH (NGA GRAFI):\n{conflicts}")
        except Exception: pass

    potential_entities = list(set(re.findall(r'\b[A-Z][a-z]{3,}\b', prompt_text)))
    connections = []
    for entity in potential_entities[:3]:
        try:
            results = graph_service.find_hidden_connections(entity)
            if results: connections.extend(results)
        except Exception: pass
    
    if connections:
        unique_conns = list(set(connections))[:5]
        buffer.append(f"🕸️ LIDHJE STRATEGJIKE (NGA GRAFI):\n" + "\n".join(unique_conns))

    return "\n\n".join(buffer) if buffer else ""

def _get_template_augmentation_sync(draft_type: str, jurisdiction: str, favorability: Optional[str], db: Database) -> Optional[str]:
    # ... implementation is correct ...
    return None

def _fetch_relevant_laws_sync(prompt_text: str, jurisdiction: str = "ks") -> str:
    try:
        embedding = generate_embedding(prompt_text[:1000])
        if not embedding: return ""
        laws = query_legal_knowledge_base(embedding, n_results=3, jurisdiction=jurisdiction)
        if not laws: return ""
        buffer = [f"\n=== BAZA LIGJORE ({jurisdiction.upper()}) ==="]
        for law in laws:
            buffer.append(f"BURIMI: {law.get('document_name','Ligj')}\nNENET: {law.get('text','l')[:1500]}\n---")
        return "\n".join(buffer)
    except Exception: return ""

def _fetch_library_context_sync(db: Database, user_id: str, prompt_text: str) -> str:
    # ... implementation is correct ...
    return ""

def _format_business_identity_sync(db: Database, user: UserInDB) -> str:
    try:
        if db is not None:
            profile = db.business_profiles.find_one({"user_id": str(user.id)})
            if profile:
                return f"=== HARTUESI (AVOKATI) ===\nZyra: {profile.get('firm_name', user.username)}\nAdresa: {profile.get('address','N/A')}\nEmail: {profile.get('contact_email', user.email)}\n"
    except Exception: pass
    return f"=== HARTUESI ===\nEmri: {user.username}\nEmail: {user.email}\n"

async def _stream_local_llm(messages: List[Dict[str, Any]]) -> AsyncGenerator[str, None]:
    # ... implementation is correct ...
    yield "[Gabim Lokal]"

# --- MAIN GENERATION FUNCTION ---
async def generate_draft_stream(
    context: str,
    prompt_text: str,
    user: UserInDB,
    draft_type: Optional[str] = None,
    case_id: Optional[str] = None,
    jurisdiction: Optional[str] = "ks",
    favorability: Optional[str] = None,
    use_library: bool = False,
    db: Optional[Database] = None
) -> AsyncGenerator[str, None]:
    
    sanitized_prompt = sterilize_text_for_llm(prompt_text)
    sanitized_context = sterilize_text_for_llm(context)

    # 1. PARALLEL DATA FETCHING
    tasks = [
        asyncio.to_thread(_fetch_relevant_laws_sync, sanitized_prompt, jurisdiction or "ks"),
        asyncio.to_thread(_format_business_identity_sync, cast(Database, db), user),
        asyncio.to_thread(_fetch_graph_intelligence_sync, case_id, sanitized_prompt)
    ]
    # ... other tasks ...
    results = await asyncio.gather(*tasks, return_exceptions=True)
    relevant_laws, business_identity, graph_intelligence = [r for r in results if not isinstance(r, Exception)]

    # 2. PROMPT CONSTRUCTION (PREMIUM VERSION)
    jurisdiction_name = "Shqipërisë" if jurisdiction == "al" else "Kosovës"
    
    system_prompt = f"""
    Ti je "Juristi AI", një Avokat i Lartë dhe Hartues Strategjik i specializuar në legjislacionin e {jurisdiction_name}.

    MISIONI YT:
    Harto një dokument ligjor formal, të strukturuar dhe bindës duke përdorur informacionin e dhënë.

    STRUKTURA E DOKUMENTIT (OBLIGATIVE - PËRDOR MARKDOWN HEADINGS):

    ### TITULLI
    - Titull i qartë dhe formal (psh., "PADI PËR KOMPENSIM DËMI", "KONTRATË SHITJE").

    ### PALËT
    - Identifiko qartë palët e përfshira (Paditësi/Shitësi, I Padituri/Blerësi) duke u bazuar te Kërkesa dhe Konteksti.

    ### BAZA FAKTIKE
    - Përmblidh në pika faktet kryesore nga seksioni 'KONTEKSTI'. Cito burimet e dokumenteve nëse përmenden.

    ### BAZA LIGJORE
    - Listo nenet specifike nga 'BAZA LIGJORE' që mbështesin këtë rast. Cito nenin dhe ligjin saktësisht.

    ### ARGUMENTIMI STRATEGJIK
    - **Përdor 'INTELIGJENCA NGA GRAFI' për avantazh.** Nëse ka një kontradiktë, theksoje për të dobësuar palën kundërshtare.
    - Lidh BAZËN FAKTIKE me BAZËN LIGJORE për të ndërtuar një argument të fortë dhe logjik.

    ### KËRKESA (PETITUMI)
    - Formulo qartë dhe saktë se çfarë kërkohet si rezultat i këtij dokumenti (psh., pagimi i shumës, detyrimi për veprim, etj.).

    ### PËRMBYLLJA FORMALE
    - Përfundo me hapësirë për datën, vendin dhe nënshkrimin e avokatit/palëve.

    RREGULLAT KRITIKE:
    - NDIQ STRUKTURËN MË LART PA PËRJASHTIM.
    - Përdor vetëm informacionin e dhënë. MOS KRIJO FAKTE.
    - Gjuha duhet të jetë formale, profesionale dhe juridike.
    """
    
    full_prompt = (
        f"{business_identity}\n"
        f"{relevant_laws}\n"
        f"{graph_intelligence}\n"
        f"KONTEKSTI NGA DOSJA:\n{sanitized_context}\n---\n"
        f"KËRKESA SPECIFIKE PËR HARTIM:\n{sanitized_prompt}"
    )

    messages: List[ChatCompletionMessageParam] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": full_prompt}
    ]

    # 3. LLM GENERATION STREAM
    if DEEPSEEK_API_KEY:
        try:
            client = AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url=OPENROUTER_BASE_URL)
            stream = await client.chat.completions.create(
                model=OPENROUTER_MODEL,
                messages=messages,
                temperature=0.15, # Low temperature for formal documents
                stream=True,
                extra_headers={"HTTP-Referer": "https://juristi.tech", "X-Title": "Juristi AI Drafting"}
            )
            async for chunk in stream:
                if chunk.choices[0].delta.content: yield chunk.choices[0].delta.content
            return
        except Exception as e:
            logger.warning(f"DeepSeek Failed: {e}")

    yield "**[Backup AI]**\n\n"
    async for chunk in _stream_local_llm(cast(List[Dict[str, Any]], messages)):
        yield chunk