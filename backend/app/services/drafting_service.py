# FILE: backend/app/services/drafting_service.py
# PHOENIX PROTOCOL - DRAFTING ENGINE V12.0 (DEEP RAG & ANTI-HALLUCINATION)
# 1. RAG UPGRADE: Search query now combines User Prompt + Case Facts for better legal retrieval.
# 2. SAFETY: If no laws are found, strict "No Hallucination" instruction is injected.
# 3. CONTEXT: Increased retrieval depth to 5 chunks to capture multi-faceted legal issues.

import os
import asyncio
import structlog
from typing import AsyncGenerator, Optional, List, Any, cast, Dict
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam 
from pymongo.database import Database
from bson import ObjectId

from ..models.user import UserInDB
from app.services.text_sterilization_service import sterilize_text_for_llm 
from .vector_store_service import query_legal_knowledge_base, query_findings_by_similarity
from .embedding_service import generate_embedding

logger = structlog.get_logger(__name__)

# --- CONFIG ---
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY") 
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat" 

# --- CONTEXT ENRICHER (HYBRID RETRIEVAL - SYNC VERSION) ---
def _build_case_context_hybrid_sync(db: Database, case_id: str, user_prompt: str) -> str:
    try:
        search_query = user_prompt
        query_embedding = generate_embedding(search_query)
        if not query_embedding: return ""

        # Retrieve relevant findings (facts) from the case file
        vector_findings = query_findings_by_similarity(
            case_id=case_id, 
            embedding=query_embedding, 
            n_results=10
        )
        
        direct_db_findings = list(db.findings.find({"case_id": {"$in": [ObjectId(case_id), case_id]}}))

        all_findings: Dict[str, Dict] = {}
        for f in vector_findings:
            all_findings[f['finding_text']] = f
        for f in direct_db_findings:
            f_text = f.get('finding_text', '')
            if f_text and f_text not in all_findings:
                 all_findings[f_text] = {"finding_text": f_text, "category": f.get("category", "FAKT")}

        if not all_findings: return ""

        context_parts = ["FAKTE TË VERIFIKUARA NGA DOSJA:"]
        for finding in all_findings.values():
            category = finding.get('category', 'FAKT')
            text = finding.get('finding_text', 'N/A')
            context_parts.append(f"- [{category}]: {text}")
        
        return "\n".join(context_parts)
    except Exception as e:
        logger.error(f"Hybrid context for drafting failed: {e}")
        return ""

# --- LAW RETRIEVAL (RAG CORE) ---
async def _fetch_relevant_laws_async(query_text: str, jurisdiction: str = "ks") -> str:
    """
    Retrieves laws based on a rich query (Prompt + Facts).
    """
    try:
        # PHOENIX FIX: Ensure query is not empty
        if not query_text or len(query_text) < 5:
            return ""

        embedding = generate_embedding(query_text)
        if not embedding: return ""
        
        # PHOENIX FIX: Increased results to 5 for broader legal context
        laws = query_legal_knowledge_base(embedding, n_results=5, jurisdiction=jurisdiction) 
        
        if not laws: 
            return "VËREJTJE: Nuk u gjetën ligje specifike në bazën e të dhënave për këtë kërkesë."

        buffer = [f"\n=== BAZA LIGJORE RELEVANTE (BURIMI: {jurisdiction.upper()}) ==="]
        for law in laws:
            # PHOENIX FIX: Strict formatting to help AI distinguish separate articles
            doc_name = law.get('document_name','Ligj')
            content = law.get('text','N/A')
            buffer.append(f"DOKUMENTI: {doc_name}\nPËRMBAJTJA:\n{content}\n--------------------------------")
        
        return "\n".join(buffer)
    except Exception as e: 
        logger.error(f"Law retrieval failed: {e}")
        return ""

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
    
    # 1. BUILD FACTUAL CONTEXT (FROM CASE FILE)
    db_context = ""
    if case_id and db is not None:
        db_context = await asyncio.to_thread(
            _build_case_context_hybrid_sync, db, case_id, sanitized_prompt
        )
    
    final_context = f"{context}\n\n{db_context}"
    sanitized_context = sterilize_text_for_llm(final_context)

    # 2. BUILD SEARCH QUERY FOR RAG (RICH QUERY)
    # Combine the prompt with the top facts to find relevant laws
    # e.g., "Divorce violence" + "Wife beaten on Sunday" -> Retrieves "Protection Order Law"
    rag_search_query = f"{sanitized_prompt} {sanitized_context[:500]}" # First 500 chars of context usually contain key facts

    # 3. FETCH LAWS & IDENTITY
    future_laws = _fetch_relevant_laws_async(rag_search_query, jurisdiction or "ks")
    future_identity = asyncio.to_thread(_format_business_identity_sync, cast(Database, db), user)
    
    results = await asyncio.gather(future_laws, future_identity, return_exceptions=True)
    relevant_laws, business_identity = [r if not isinstance(r, Exception) else "" for r in results]

    # 4. CONSTRUCT SYSTEM PROMPT (ANTI-HALLUCINATION)
    # Strict instructions to use ONLY the provided laws.
    system_prompt = f"""
    Ti je "Juristi AI", Avokat Ekspert për legjislacionin e KOSOVËS.
    DETYRA: Harto dokumentin e kërkuar duke u bazuar EKSKLUZIVISHT në ligjet e dhëna më poshtë.

    RREGULLAT E ARTA (ANTI-HALUCINACION):
    1. **JURISDIKSIONI:** Përdor VETËM ligjet e KOSOVËS. Injoro ligjet e Shqipërisë.
    2. **CITIMET:** Nëse seksioni "BAZA LIGJORE RELEVANTE" është bosh, MOS shpik nene. Shkruaj thjesht "Sipas ligjeve në fuqi".
    3. **FAKTET:** Përdor saktë emrat dhe datat nga "KONTEKSTI I RASTIT".
    4. **STILI:** Formal, juridik, objektiv.
    """
    
    full_prompt = (
        f"{business_identity}\n"
        f"{relevant_laws}\n\n"
        f"=== KONTEKSTI I RASTIT (FAKTET) ===\n{sanitized_context}\n\n"
        f"=== UDHËZIMI I PËRDORUESIT ===\n'{sanitized_prompt}'\n\n"
        f"KËRKESA: Harto dokumentin e plotë tani."
    )

    messages: List[ChatCompletionMessageParam] = [{"role": "system", "content": system_prompt}, {"role": "user", "content": full_prompt}]

    if DEEPSEEK_API_KEY:
        try:
            client = AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url=OPENROUTER_BASE_URL)
            stream = await client.chat.completions.create(
                model=OPENROUTER_MODEL, messages=messages, temperature=0.1, stream=True, # Temp 0.1 allows slight creativity for phrasing but strict for facts
                extra_headers={"HTTP-Referer": "https://juristi.tech", "X-Title": "Juristi AI Drafting"}
            )
            async for chunk in stream:
                if chunk.choices[0].delta.content: yield chunk.choices[0].delta.content
            return
        except Exception as e:
            logger.error(f"Drafting generation failed: {e}")

    yield "**[Gabim gjatë gjenerimit. Ju lutemi provoni përsëri.]**"