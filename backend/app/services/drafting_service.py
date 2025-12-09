# FILE: backend/app/services/drafting_service.py
# PHOENIX PROTOCOL - DRAFTING ENGINE V9.2 (ASYNC FIX)
# 1. FIX: Imported and used 'AsyncGroq' instead of the sync 'Groq' client.
# 2. STATUS: Resolves the "not awaitable" Pylance error for the keyword extractor.

import os
import asyncio
import structlog
import json
import re
from typing import AsyncGenerator, Optional, List, Any, cast, Dict
from openai import AsyncOpenAI
from groq import AsyncGroq # PHOENIX FIX: Import the ASYNC client
from openai.types.chat import ChatCompletionMessageParam 
from pymongo.database import Database
from bson import ObjectId

from ..models.user import UserInDB
from app.services.text_sterilization_service import sterilize_text_for_llm 
from .vector_store_service import query_legal_knowledge_base
from .embedding_service import generate_embedding
from .graph_service import graph_service 

logger = structlog.get_logger(__name__)

# --- CONFIG ---
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY") 
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat" 
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL_NAME = "llama3-8b-8192"

# --- KEYWORD EXTRACTOR (FIXED) ---
async def _extract_keywords_with_groq(prompt: str, context: str) -> str:
    if not GROQ_API_KEY: return prompt
    try:
        # PHOENIX FIX: Use the AsyncGroq client
        client = AsyncGroq(api_key=GROQ_API_KEY)
        response = await client.chat.completions.create(
            model=GROQ_MODEL_NAME,
            messages=[
                {"role": "system", "content": "Ti je ekspert ligjor. Ekstrakto 3-5 fjalët kyçe ligjore (në Shqip) nga teksti. Përgjigju vetëm me fjalët, ndarë me presje. Shembull: Padi, Dëmshpërblim, Kontratë Qiraje."},
                {"role": "user", "content": f"Prompt: {prompt}\n\nKonteksti: {context[:1000]}"}
            ],
            temperature=0.0
        )
        keywords = response.choices[0].message.content
        return f"{prompt} {keywords}"
    except Exception as e:
        logger.warning(f"Groq keyword extraction failed: {e}")
        return prompt

# --- CONTEXT ENRICHER ---
def _build_case_context_sync(db: Database, case_id: str) -> str:
    try:
        documents = list(db.documents.find({"case_id": ObjectId(case_id)}))
        context_parts = []
        for doc in documents:
            name = doc.get("file_name", "Unknown")
            summary = doc.get("summary", "")
            findings = list(db.findings.find({"document_id": doc["_id"]}))
            findings_text = "\n".join([f"- {f.get('finding_text')}" for f in findings])
            doc_block = f"DOKUMENTI: {name}\nPËRMBLEDHJE: {summary}\nFAKTE KYÇE: {findings_text}\n"
            context_parts.append(doc_block)
        return "\n".join(context_parts)
    except Exception as e:
        logger.error(f"Context enrichment failed: {e}")
        return ""

def _fetch_graph_intelligence_sync(case_id: Optional[str], prompt_text: str) -> str:
    buffer = []
    if case_id:
        try:
            conflicts = graph_service.find_contradictions(case_id)
            if conflicts and "No direct contradictions" not in conflicts:
                buffer.append(f"⚠️ KONTRAST FAKTESH (NGA GRAFI):\n{conflicts}")
        except Exception: pass
    return "\n\n".join(buffer) if buffer else ""

async def _fetch_relevant_laws_async(prompt_text: str, context_text: str, jurisdiction: str = "ks") -> str:
    try:
        search_query = await _extract_keywords_with_groq(prompt_text, context_text)
        embedding = generate_embedding(search_query)
        if not embedding: return ""
        laws = query_legal_knowledge_base(embedding, n_results=3, jurisdiction=jurisdiction)
        if not laws: return ""
        buffer = [f"\n=== BAZA LIGJORE ({jurisdiction.upper()}) ==="]
        for law in laws:
            buffer.append(f"BURIMI: {law.get('document_name','Ligj')}\nNENET: {law.get('text','l')[:1500]}\n---")
        return "\n".join(buffer)
    except Exception: return ""

def _format_business_identity_sync(db: Database, user: UserInDB) -> str:
    try:
        if db is not None:
            profile = db.business_profiles.find_one({"user_id": str(user.id)})
            if profile:
                return f"=== HARTUESI (AVOKATI) ===\nZyra: {profile.get('firm_name', user.username)}\nAdresa: {profile.get('address','N/A')}\n"
    except Exception: pass
    return f"=== HARTUESI ===\nEmri: {user.username}\n"

# --- MAIN GENERATION FUNCTION ---
async def generate_draft_stream(
    context: str, prompt_text: str, user: UserInDB, draft_type: Optional[str] = None,
    case_id: Optional[str] = None, jurisdiction: Optional[str] = "ks",
    use_library: bool = False, db: Optional[Database] = None
) -> AsyncGenerator[str, None]:
    
    sanitized_prompt = sterilize_text_for_llm(prompt_text)
    
    db_context = ""
    if case_id and db is not None:
        db_context = await asyncio.to_thread(_build_case_context_sync, db, case_id)
    
    final_context = f"{context}\n{db_context}"
    sanitized_context = sterilize_text_for_llm(final_context)

    future_laws = _fetch_relevant_laws_async(sanitized_prompt, sanitized_context, jurisdiction or "ks")
    future_identity = asyncio.to_thread(_format_business_identity_sync, cast(Database, db), user)
    future_graph = asyncio.to_thread(_fetch_graph_intelligence_sync, case_id, sanitized_prompt)
    
    results = await asyncio.gather(future_laws, future_identity, future_graph, return_exceptions=True)
    relevant_laws, business_identity, graph_intelligence = [r if not isinstance(r, Exception) else "" for r in results]

    jurisdiction_name = "Shqipërisë" if jurisdiction == "al" else "Kosovës"
    
    system_prompt = f"""
    Ti je "Juristi AI", Avokat Ekspert në hartimin e dokumenteve për {jurisdiction_name}.
    DETYRA: Harto një dokument ligjor bazuar në "KONTEKSTI NGA DOSJA".
    RREGULLAT E REPTA:
    1. **PËRDOR EMRA REALË:** Mos përdor kurrë [placeholder]. Përdor emrat (psh. 'AgroTech SH.P.K.') dhe faktet që gjenden në kontekst.
    2. **BAZA LIGJORE:** Justifiko kërkesat duke cituar nenet specifike nga "BAZA LIGJORE".
    3. **KORRIGJO FAKTET:** Nëse "INTELIGJENCA NGA GRAFI" tregon kontradikta (psh. data të gabuara), korrigjoji ato në draftin final.
    STRUKTURA: Titull | Palët | Preambula (arsyetimi) | Nenet e Marrëveshjes | Nënshkrimet
    """
    
    full_prompt = (
        f"{business_identity}\n{relevant_laws}\n{graph_intelligence}\n"
        f"KONTEKSTI NGA DOSJA (Përdor këto të dhëna):\n{sanitized_context}\n---\n"
        f"UDHËZIMI I PËRDORUESIT:\n{sanitized_prompt}"
    )

    messages: List[ChatCompletionMessageParam] = [{"role": "system", "content": system_prompt}, {"role": "user", "content": full_prompt}]

    if DEEPSEEK_API_KEY:
        try:
            client = AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url=OPENROUTER_BASE_URL)
            stream = await client.chat.completions.create(
                model=OPENROUTER_MODEL, messages=messages, temperature=0.1, stream=True,
                extra_headers={"HTTP-Referer": "https://juristi.tech", "X-Title": "Juristi AI Drafting"}
            )
            async for chunk in stream:
                if chunk.choices[0].delta.content: yield chunk.choices[0].delta.content
            return
        except Exception as e:
            logger.error(f"Drafting generation failed: {e}")

    yield "**[Draftimi dështoi. Kontrolloni API Key ose Lidhjen.]**"