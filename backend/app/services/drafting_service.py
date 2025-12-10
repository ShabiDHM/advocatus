# FILE: backend/app/services/drafting_service.py
# PHOENIX PROTOCOL - DRAFTING ENGINE V10.2 (INTELLIGENCE RESTORED)
# 1. FIX: Re-integrated 'Graph Intelligence' (Contradictions) which was lost in V10.0.
# 2. LOGIC: Drafter now sees both 'Findings' (Facts) and 'Graph' (Conflicts).
# 3. PROMPT: Instructs the AI to handle contradictions gracefully in the draft.

import os
import asyncio
import structlog
import json
import re
from typing import AsyncGenerator, Optional, List, Any, cast, Dict
from openai import AsyncOpenAI
from groq import AsyncGroq 
from openai.types.chat import ChatCompletionMessageParam 
from pymongo.database import Database
from bson import ObjectId

from ..models.user import UserInDB
from app.services.text_sterilization_service import sterilize_text_for_llm 
from .vector_store_service import query_legal_knowledge_base, query_findings_by_similarity
from .embedding_service import generate_embedding
from .graph_service import graph_service 

logger = structlog.get_logger(__name__)

# --- CONFIG ---
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY") 
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat" 
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL_NAME = "llama3-8b-8192"

# --- KEYWORD EXTRACTOR ---
async def _extract_keywords_with_groq(prompt: str, context: str) -> str:
    if not GROQ_API_KEY: return prompt
    try:
        client = AsyncGroq(api_key=GROQ_API_KEY)
        response = await client.chat.completions.create(
            model=GROQ_MODEL_NAME,
            messages=[
                {"role": "system", "content": "Ti je ekspert ligjor. Ekstrakto 3-5 konceptet kyçe ligjore (në Shqip) nga teksti. Përgjigju vetëm me fjalët, ndarë me presje."},
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
async def _build_case_context_with_rag(db: Database, case_id: str, user_prompt: str) -> str:
    try:
        search_query = await _extract_keywords_with_groq(user_prompt, "")
        query_embedding = generate_embedding(search_query)
        if not query_embedding: return ""

        relevant_findings = query_findings_by_similarity(
            case_id=case_id, 
            embedding=query_embedding, 
            n_results=10
        )

        if not relevant_findings: return ""

        context_parts = ["FAKTE RELEVANTE NGA DOSJA:"]
        for finding in relevant_findings:
            category = finding.get('category', 'FAKT')
            text = finding.get('finding_text', 'N/A')
            context_parts.append(f"- [{category}]: {text}")
        
        return "\n".join(context_parts)
    except Exception as e:
        logger.error(f"Precision RAG context enrichment failed: {e}")
        return ""

def _fetch_graph_intelligence_sync(case_id: Optional[str]) -> str:
    """
    Fetches contradictions or critical flags from the Graph Service.
    """
    if not case_id: return ""
    try:
        conflicts = graph_service.find_contradictions(case_id)
        if conflicts and "No direct contradictions" not in conflicts:
            return f"⚠️ INTELIGJENCA E GRAFIT (KONTRADIKTA):\n{conflicts}"
    except Exception: pass
    return ""

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
    
    # 1. Facts from RAG
    db_context = ""
    if case_id and db is not None:
        db_context = await _build_case_context_with_rag(db, case_id, sanitized_prompt)
    
    final_context = f"{context}\n\n{db_context}"
    sanitized_context = sterilize_text_for_llm(final_context)

    # 2. Parallel Fetch: Laws, Identity, AND Graph Intelligence
    future_laws = _fetch_relevant_laws_async(sanitized_prompt, sanitized_context, jurisdiction or "ks")
    future_identity = asyncio.to_thread(_format_business_identity_sync, cast(Database, db), user)
    # PHOENIX FIX: Restored Graph Intelligence Call
    future_graph = asyncio.to_thread(_fetch_graph_intelligence_sync, case_id)
    
    results = await asyncio.gather(future_laws, future_identity, future_graph, return_exceptions=True)
    relevant_laws, business_identity, graph_intelligence = [r if not isinstance(r, Exception) else "" for r in results]

    jurisdiction_name = "Shqipërisë" if jurisdiction == "al" else "Kosovës"
    
    system_prompt = f"""
    Ti je "Juristi AI", Avokat Ekspert në hartimin e dokumenteve për {jurisdiction_name}.
    DETYRA: Harto një dokument ligjor profesional bazuar në faktet nga dosja dhe udhëzimet e përdoruesit.
    
    RREGULLAT E REPTA:
    1. **PËRDOR FAKTE REALE:** Përdor emrat, shumat dhe datat specifike nga "FAKTE RELEVANTE".
    2. **KUJDES ME KONTRADIKTAT:** Nëse "INTELIGJENCA E GRAFIT" tregon mospërputhje (psh. data të kontestuara), harto dokumentin në mënyrë që të mbrosh interesin e klientit, ose shto shënime për avokatin.
    3. **BAZA LIGJORE:** Cito nenet nga "BAZA LIGJORE".
    4. **STILI:** Ligjor, formal, preciz.
    """
    
    full_prompt = (
        f"{business_identity}\n{relevant_laws}\n{graph_intelligence}\n"
        f"--- KONTEKSTI I RASTIT ---\n{sanitized_context}\n---\n"
        f"UDHËZIMI I PËRDORUESIT:\n'{sanitized_prompt}'"
    )

    messages: List[ChatCompletionMessageParam] = [{"role": "system", "content": system_prompt}, {"role": "user", "content": full_prompt}]

    if DEEPSEEK_API_KEY:
        try:
            client = AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url=OPENROUTER_BASE_URL)
            stream = await client.chat.completions.create(
                model=OPENROUTER_MODEL, messages=messages, temperature=0.15, stream=True,
                extra_headers={"HTTP-Referer": "https://juristi.tech", "X-Title": "Juristi AI Drafting"}
            )
            async for chunk in stream:
                if chunk.choices[0].delta.content: yield chunk.choices[0].delta.content
            return
        except Exception as e:
            logger.error(f"Drafting generation failed: {e}")

    yield "**[Draftimi dështoi. Kontrolloni API Key ose Lidhjen.]**"