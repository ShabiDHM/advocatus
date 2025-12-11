# FILE: backend/app/services/drafting_service.py
# PHOENIX PROTOCOL - DRAFTING ENGINE V11.2 (SELF-CORRECTION)
# 1. PROMPT UPGRADE: Added a "SELF-CORRECTION" rule to the system prompt.
# 2. PRIORITY: Explicitly instructs the AI to prioritize facts from the case file over generic legal text.
# 3. GOAL: To eliminate placeholder hallucination permanently.

import os
import asyncio
import structlog
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

logger = structlog.get_logger(__name__)

# --- CONFIG ---
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY") 
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat" 
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL_NAME = "llama3-8b-8192"

# --- CONTEXT ENRICHER (HYBRID RETRIEVAL - SYNC VERSION) ---
def _build_case_context_hybrid_sync(db: Database, case_id: str, user_prompt: str) -> str:
    try:
        from .embedding_service import generate_embedding
        search_query = user_prompt
        query_embedding = generate_embedding(search_query)
        if not query_embedding: return ""

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

async def _fetch_relevant_laws_async(prompt_text: str, context_text: str, jurisdiction: str = "ks") -> str:
    try:
        from .embedding_service import generate_embedding
        embedding = generate_embedding(prompt_text)
        if not embedding: return ""
        laws = query_legal_knowledge_base(embedding, n_results=2, jurisdiction=jurisdiction) # Reduced to 2 for less noise
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
    
    # PHOENIX V11.2 UPGRADE: SELF-CORRECTION PROMPT
    system_prompt = f"""
    Ti je "Juristi AI", Avokat Ekspert në hartimin e dokumenteve për {jurisdiction_name}.
    DETYRA: Harto një dokument ligjor profesional.

    RREGULLAT E REPTA (NUK NEGOCIOHEN):
    1. **FAKTET MBI LIGJET:** Prioriteti yt #1 është të përdorësh emrat, shumat dhe datat specifike nga seksioni "FAKTE TË VERIFIKUARA NGA DOSJA". Mos përdor kurrë [placeholder] si [Emri i paditurit].
    2. **VETË-KORRIGJIM:** Para se të përfundosh, rishiko draftin tënd. Nëse sheh ndonjë [placeholder], fshije dhe zëvendësoje me faktin korrekt nga konteksti. NESE FAKTI NUK EKZISTON, LËRE BOSH, MOS VENDOS PLACEHOLDER.
    3. **PRECISION:** Adreso direkt kërkesën e përdoruesit.
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
                model=OPENROUTER_MODEL, messages=messages, temperature=0.0, stream=True, # Temperature ZERO for strictness
                extra_headers={"HTTP-Referer": "https://juristi.tech", "X-Title": "Juristi AI Drafting"}
            )
            async for chunk in stream:
                if chunk.choices[0].delta.content: yield chunk.choices[0].delta.content
            return
        except Exception as e:
            logger.error(f"Drafting generation failed: {e}")

    yield "**[Draftimi dështoi.]**"