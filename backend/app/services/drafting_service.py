# FILE: backend/app/services/drafting_service.py
# PHOENIX PROTOCOL - DRAFTING ENGINE V4.2 (STRICT TYPING FIX)
# 1. FIX: Imported 'ChatCompletionMessageParam' to resolve Pylance argument error.
# 2. TYPE: Explicitly typed the 'messages' list for OpenAI compatibility.
# 3. CLEANUP: Removed unused Groq imports.

import os
import asyncio
import structlog
import httpx
import json
from typing import AsyncGenerator, Optional, List, Any, cast, Dict
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam # PHOENIX FIX: Added type import
from pymongo.database import Database
from bson import ObjectId

from ..models.user import UserInDB
from app.services.text_sterilization_service import sterilize_text_for_llm 
from .vector_store_service import query_legal_knowledge_base
from .embedding_service import generate_embedding

logger = structlog.get_logger(__name__)

# --- CONFIGURATION ---
# OpenRouter / DeepSeek Configuration
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY") 
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat" 

# Local Fallback
LOCAL_LLM_URL = os.environ.get("LOCAL_LLM_URL", "http://local-llm:11434/api/chat")
LOCAL_MODEL_NAME = "llama3"

# --- HELPER FUNCTIONS ---

def _get_template_augmentation(draft_type: str, jurisdiction: str, favorability: Optional[str], db: Database) -> Optional[str]:
    if db is None: return None
    
    template_filter = {
        "document_type": draft_type,
        "jurisdiction": jurisdiction,
        "favorability": favorability
    }
    template = db.document_templates.find_one(template_filter)
    if not template: return None
    try:
        augmentation_text = f"The generated document MUST be a {draft_type} for the jurisdiction of {jurisdiction}."
        clauses_text = "\n".join([
            clause.get("clause_text", "") for clause in template.get("clauses", [])
            if clause.get("is_default", False)
        ])
        if clauses_text:
            augmentation_text += f"\n\nInclude the following mandatory clause text:\n{clauses_text}"
        return augmentation_text
    except Exception as e:
        logger.error("drafting_service.template_augmentation_error", error=str(e))
        return None

def _fetch_relevant_laws(prompt_text: str) -> str:
    try:
        embedding = generate_embedding(prompt_text[:1000])
        if not embedding: return ""
        laws = query_legal_knowledge_base(embedding, n_results=3)
        if not laws: return ""

        law_buffer = ["\n=== BAZA LIGJORE E DETYRUESHME (NGA DATABAZA PUBLIKE) ==="]
        for law in laws:
            source = law.get('document_name', 'Ligj')
            text = law.get('text', '')[:1500] 
            law_buffer.append(f"BURIMI: {source}\nNENET: {text}\n---")
        return "\n".join(law_buffer)
    except Exception as e:
        logger.warning(f"Drafting RAG Lookup failed: {e}")
        return ""

def _fetch_library_context(db: Database, user_id: str, prompt_text: str) -> str:
    if db is None: return ""
    try:
        cursor = db.library.find({"user_id": ObjectId(user_id)})
        templates = list(cursor)
        if not templates: return ""

        matches = []
        prompt_lower = prompt_text.lower()

        for t in templates:
            title = t.get("title", "").lower()
            if title in prompt_lower or any(word in prompt_lower for word in title.split() if len(word) > 4):
                matches.append(t)
                continue
            
            tags = [tag.lower() for tag in t.get("tags", [])]
            if any(tag in prompt_lower for tag in tags):
                matches.append(t)
                continue
            
            category = t.get("category", "").lower() 
            if category in prompt_lower:
                matches.append(t)

        if not matches: return ""

        buffer = ["\n=== ARKIVA LIGJORE E PËRDORUESIT (MODELET PERSONALIZUARA) ==="]
        buffer.append("Instruksion: Përdoruesi ka modele të ruajtura që mund të jenë relevante. Nëse përshtaten, përdori ato me përparësi.")
        
        for m in matches[:3]: 
            buffer.append(f"--- MODEL: {m.get('title')} ---")
            buffer.append(f"TIPI: {m.get('category', 'N/A')}")
            buffer.append(f"PËRMBAJTJA:\n{m.get('content')}\n")
        
        buffer.append("============================================================\n")
        return "\n".join(buffer)

    except Exception as e:
        logger.error(f"Library lookup failed: {e}")
        return ""

def _format_business_identity(db: Database, user: UserInDB) -> str:
    if db is None: return _fallback_identity(user)
    try:
        profile = db.business_profiles.find_one({"user_id": str(user.id)})
        if profile:
            name_to_use = profile.get('firm_name') or user.username
            info = f"""
            === HARTUESI I DOKUMENTIT (ZYRA LIGJORE/BIZNESI) ===
            Emri i Zyrës: {name_to_use}
            Adresa: {profile.get('address', 'N/A')}
            Email: {profile.get('contact_email', user.email)}
            """
            if profile.get('phone'): info += f"Tel: {profile.get('phone')}\n"
            if profile.get('website'): info += f"Web: {profile.get('website')}\n"
            info += "==============================================\n"
            return info
    except Exception as e:
        logger.warning(f"Failed to fetch business profile: {e}")
    return _fallback_identity(user)

def _fallback_identity(user: UserInDB) -> str:
    return f"""
    === HARTUESI (INFORMACION NGA LLOGARIA) ===
    Emri: {user.username}
    Email: {user.email}
    ===========================================
    """

# --- LOCAL LLM STREAMER ---
async def _stream_local_llm(messages: List[Dict[str, Any]]) -> AsyncGenerator[str, None]:
    logger.info("🔄 Switching to LOCAL LLM (Ollama) for drafting...")
    payload = {
        "model": LOCAL_MODEL_NAME,
        "messages": messages,
        "stream": True,
        "options": {"temperature": 0.3, "num_ctx": 8192}
    }
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", LOCAL_LLM_URL, json=payload) as response:
                if response.status_code != 200:
                    yield "\n[Gabim: Sistemi lokal nuk u përgjigj.]"
                    return
                async for line in response.aiter_lines():
                    if not line: continue
                    try:
                        data = json.loads(line)
                        content = data.get("message", {}).get("content", "")
                        if content: yield content
                        if data.get("done", False): break
                    except: continue
    except Exception as e:
        logger.error("drafting_service.local_llm_failed", error=str(e))
        yield "\n\n[Gabim Kritik: Edhe sistemi lokal nuk është i disponueshëm.]"

# --- MAIN GENERATION FUNCTION ---
async def generate_draft_stream(
    context: str,
    prompt_text: str,
    user: UserInDB,
    draft_type: Optional[str] = None,
    case_id: Optional[str] = None,
    jurisdiction: Optional[str] = None,
    favorability: Optional[str] = None,
    use_library: bool = False,
    db: Optional[Database] = None
) -> AsyncGenerator[str, None]:
    
    log = logger.bind(case_id=case_id, user_id=str(user.id), draft_type=draft_type)
    if prompt_text is None: prompt_text = ""
    log.info("drafting_service.stream_start", prompt_length=len(prompt_text))

    sanitized_context = sterilize_text_for_llm(context)
    sanitized_prompt_text = sterilize_text_for_llm(prompt_text)

    # 1. Fetch Laws (Async)
    relevant_laws = await asyncio.to_thread(_fetch_relevant_laws, sanitized_prompt_text)
    
    # 2. Fetch Library (Async)
    library_context = ""
    if db is not None and use_library: 
        library_context = await asyncio.to_thread(
            _fetch_library_context, cast(Database, db), str(user.id), sanitized_prompt_text
        )

    # 3. Business Identity
    business_identity = ""
    if db is not None:
        business_identity = await asyncio.to_thread(
            _format_business_identity, cast(Database, db), user
        )

    # PHOENIX PROTOCOL - KOSOVO DRAFTING PROMPT
    system_prompt = (
        "Ti je 'Juristi AI', një Ekspert i Hartimit Ligjor për sistemin e drejtësisë në Kosovë. "
        "DETYRA: Harto një dokument ligjor të plotë, profesional dhe të gatshëm për nënshkrim. "
        "\n\n"
        "UDHËZIME STRIKTE TË FORMATIMIT:\n"
        "1. KOKA E DOKUMENTIT: Fillo me një titull të qartë (p.sh., 'KONTRATË PUNE' ose 'PADI PËR SHPËRBLIM DËMI') dhe datë/vend.\n"
        "2. IDENTITETI: Përdor informacionin nga 'HARTUESI I DOKUMENTIT' për palën përkatëse (avokatin ose zyrën).\n"
        "3. LIGJI: Cito saktësisht nenet nga 'BAZA LIGJORE' nëse janë relevante. Përdor terminologjinë e Ligjeve të Kosovës.\n"
        "4. STRUKTURA: Përdor numërim të qartë për nenet/klauzolat (Neni 1, Neni 2...).\n"
        "5. GJUHA: Shqipe letrare juridike, pa gabime, ton formal.\n"
        "6. PA KOMENTE: Mos shto shpjegime si 'Ja ku e keni dokumentin', vetëm tekstin e dokumentit.\n"
    )

    full_prompt = f"""
    {business_identity}
    
    {relevant_laws}

    {library_context}
    
    KONTEKSTI NGA DOSJA (OPSIONAL):
    {sanitized_context}
    
    ---
    KËRKESA E PËRDORUESIT (SPECIFIKIMET):
    {sanitized_prompt_text}
    """

    if draft_type and jurisdiction and db is not None:
        template_augment = await asyncio.to_thread(_get_template_augmentation, draft_type, jurisdiction, favorability, cast(Database, db))
        if template_augment:
            system_prompt += f" Përdor strukturën specifike për: {draft_type} ({jurisdiction})."
            full_prompt = f"Template Instructions:\n{template_augment}\n\n---\n\n{full_prompt}"

    # PHOENIX FIX: Strict type assignment for OpenAI
    messages: List[ChatCompletionMessageParam] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": full_prompt}
    ]

    tier1_failed = False
    
    # --- TIER 1: OPENROUTER / DEEPSEEK ---
    if DEEPSEEK_API_KEY:
        try:
            client = AsyncOpenAI(
                api_key=DEEPSEEK_API_KEY, 
                base_url=OPENROUTER_BASE_URL
            )
            
            stream = await client.chat.completions.create(
                model=OPENROUTER_MODEL,
                messages=messages,
                temperature=0.3,
                stream=True,
                extra_headers={
                    "HTTP-Referer": "https://juristi.tech", 
                    "X-Title": "Juristi AI Drafting"
                }
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
            
            log.info("drafting_service.stream_success_deepseek")
            return

        except Exception as e:
            log.warning(f"⚠️ DeepSeek Drafting Failed: {e}")
            tier1_failed = True
    else:
        tier1_failed = True

    # --- TIER 2: LOCAL FALLBACK ---
    if tier1_failed:
        yield "**[Draft i Gjeneruar nga AI Lokale]**\n\n"
        # We convert the typed messages back to dict for the local function if needed, 
        # but the structure is compatible.
        async for chunk in _stream_local_llm(cast(List[Dict[str, Any]], messages)):
            yield chunk
        log.info("drafting_service.stream_success_local")

def generate_draft_from_prompt(*args, **kwargs):
    raise NotImplementedError("Use generate_draft_stream instead.")
def generate_draft(*args, **kwargs):
    raise NotImplementedError("Use generate_draft_stream instead.")