# FILE: backend/app/services/drafting_service.py
# PHOENIX PROTOCOL - DRAFTING ENGINE V11.1 (ASYNC FIX)
# 1. FIX: Corrected the async/sync database call conflict.
# 2. LOGIC: The context builder is now fully synchronous and wrapped correctly for async execution.
# 3. STATUS: Resolves the 'Cannot access attribute "to_list"' Pylance error.

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

# --- CONTEXT ENRICHER (HYBRID RETRIEVAL - SYNC VERSION) ---
def _build_case_context_hybrid_sync(db: Database, case_id: str, user_prompt: str) -> str:
    """
    Builds a focused context dossier using Hybrid Retrieval (SYNC).
    """
    try:
        from .embedding_service import generate_embedding
        search_query = user_prompt
        query_embedding = generate_embedding(search_query)
        if not query_embedding: return ""

        # 1. Vector Search (Sync)
        vector_findings = query_findings_by_similarity(
            case_id=case_id, 
            embedding=query_embedding, 
            n_results=10
        )
        
        # 2. Direct DB Query (Sync)
        # PHOENIX FIX: Use a standard list conversion for the sync cursor.
        direct_db_findings = list(db.findings.find({"case_id": {"$in": [ObjectId(case_id), case_id]}}))

        # 3. Merge and De-duplicate
        all_findings: Dict[str, Dict] = {}
        for f in vector_findings:
            all_findings[f['finding_text']] = f
        for f in direct_db_findings:
            f_text = f.get('finding_text', '')
            if f_text and f_text not in all_findings:
                 all_findings[f_text] = {"finding_text": f_text, "category": f.get("category", "FAKT")}

        if not all_findings: return ""

        # 4. Assemble Dossier
        context_parts = ["FAKTE TË VERIFIKUARA NGA DOSJA:"]
        for finding in all_findings.values():
            category = finding.get('category', 'FAKT')
            text = finding.get('finding_text', 'N/A')
            context_parts.append(f"- [{category}]: {text}")
        
        return "\n".join(context_parts)
    except Exception as e:
        logger.error(f"Hybrid context enrichment for drafting failed: {e}")
        return ""

async def _fetch_relevant_laws_async(prompt_text: str, context_text: str, jurisdiction: str = "ks") -> str:
    try:
        from .embedding_service import generate_embedding
        embedding = generate_embedding(prompt_text)
        if not embedding: return ""
        laws = query_legal_knowledge_base(embedding, n_results=3, jurisdiction=jurisdiction)
        if not laws: return ""
        buffer = [f"\n=== BAZA LIGJORE RELEVANTE ({jurisdiction.upper()}) ==="]
        for law in laws:
            buffer.append(f"BURIMI: {law.get('document_name','Ligj')}\nNENET: {law.get('text','N/A')[:1000]}\n---")
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
    
    # PHOENIX FIX: Execute the synchronous context builder in a separate thread.
    db_context = ""
    if case_id and db is not None:
        db_context = await asyncio.to_thread(
            _build_case_context_hybrid_sync, db, case_id, sanitized_prompt
        )
    
    final_context = f"{context}\n\n{db_context}"
    sanitized_context = sterilize_text_for_llm(final_context)

    future_laws = _fetch_relevant_laws_async(sanitized_prompt, sanitized_context, jurisdiction or "ks")
    future_identity = asyncio.to_thread(_format_business_identity_sync, cast(Database, db), user)
    
    results = await asyncio.gather(future_laws, future_identity, return_exceptions=True)
    relevant_laws, business_identity = [r if not isinstance(r, Exception) else "" for r in results]

    jurisdiction_name = "Shqipërisë" if jurisdiction == "al" else "Kosovës"
    
    system_prompt = f"""
    Ti je "Juristi AI", Avokat Ekspert në hartimin e dokumenteve për {jurisdiction_name}.
    DETYRA: Harto një dokument ligjor profesional bazuar në faktet nga dosja dhe udhëzimet e përdoruesit.
    RREGULLAT E REPTA:
    1. **PËRDOR FAKTE REALE:** Mos përdor kurrë [placeholder]. Përdor emrat, shumat dhe datat specifike që gjenden tek "FAKTE TË VERIFIKUARA NGA DOSJA".
    2. **BAZA LIGJORE:** Justifiko kërkesat duke cituar nenet specifike nga "BAZA LIGJORE".
    3. **PRECISION:** Adreso direkt kërkesën e përdoruesit. Mos devijo.
    STRUKTURA: Ndiq formatin standard ligjor për llojin e dokumentit që kërkohet.
    """
    
    full_prompt = (
        f"{business_identity}\n{relevant_laws}\n"
        f"--- KONTEKSTI I RASTIT ---\n{sanitized_context}\n---\n"
        f"UDHËZIMI I PËRDORUESIT (Detyra jote kryesore):\n'{sanitized_prompt}'"
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

    yield "**[Draftimi dështoi.]**"