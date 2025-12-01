# FILE: backend/app/services/drafting_service.py
# PHOENIX PROTOCOL - DRAFTING ENGINE V5.1 (PYMONGO TYPE FIX)
# 1. FIX: Replaced implicit 'if db:' checks with explicit 'if db is not None:'.
# 2. STATUS: Resolves Pylance type errors regarding Database objects.

import os
import asyncio
import structlog
import httpx
import json
from typing import AsyncGenerator, Optional, List, Any, cast, Dict
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam 
from pymongo.database import Database
from bson import ObjectId

from ..models.user import UserInDB
from app.services.text_sterilization_service import sterilize_text_for_llm 
from .vector_store_service import query_legal_knowledge_base
from .embedding_service import generate_embedding

logger = structlog.get_logger(__name__)

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY") 
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat" 
LOCAL_LLM_URL = os.environ.get("LOCAL_LLM_URL", "http://local-llm:11434/api/chat")
LOCAL_MODEL_NAME = "llama3"

# --- HELPERS (Sync versions wrapped later) ---
def _get_template_augmentation_sync(draft_type: str, jurisdiction: str, favorability: Optional[str], db: Database) -> Optional[str]:
    try:
        template_filter = {"document_type": draft_type, "jurisdiction": jurisdiction, "favorability": favorability}
        template = db.document_templates.find_one(template_filter)
        if not template: return None
        
        text = f"The generated document MUST be a {draft_type} for {jurisdiction}."
        clauses = "\n".join([c.get("clause_text", "") for c in template.get("clauses", []) if c.get("is_default", False)])
        if clauses: text += f"\n\nInclude:\n{clauses}"
        return text
    except Exception: return None

def _fetch_relevant_laws_sync(prompt_text: str) -> str:
    try:
        embedding = generate_embedding(prompt_text[:1000])
        if not embedding: return ""
        laws = query_legal_knowledge_base(embedding, n_results=3)
        if not laws: return ""
        buffer = ["\n=== BAZA LIGJORE (NGA DATABAZA) ==="]
        for law in laws:
            buffer.append(f"BURIMI: {law.get('document_name','Ligj')}\nNENET: {law.get('text','l')[:1500]}\n---")
        return "\n".join(buffer)
    except Exception: return ""

def _fetch_library_context_sync(db: Database, user_id: str, prompt_text: str) -> str:
    # PHOENIX FIX: Explicit None check
    if db is None: return ""
    try:
        templates = list(db.library.find({"user_id": ObjectId(user_id)}))
        if not templates: return ""
        prompt_lower = prompt_text.lower()
        matches = [t for t in templates if t.get("title", "").lower() in prompt_lower or t.get("category", "").lower() in prompt_lower]
        if not matches: return ""
        buffer = ["\n=== ARKIVA (MODELET E RUAJTURA) ==="]
        for m in matches[:3]:
            buffer.append(f"MODEL: {m.get('title')}\nPËRMBAJTJA:\n{m.get('content')}\n")
        return "\n".join(buffer)
    except Exception: return ""

def _format_business_identity_sync(db: Database, user: UserInDB) -> str:
    try:
        # PHOENIX FIX: Explicit None check
        if db is not None:
            profile = db.business_profiles.find_one({"user_id": str(user.id)})
            if profile:
                return f"=== HARTUESI (ZYRA) ===\nZyra: {profile.get('firm_name', user.username)}\nAdresa: {profile.get('address','N/A')}\nEmail: {profile.get('contact_email', user.email)}\n"
    except Exception: pass
    return f"=== HARTUESI ===\nEmri: {user.username}\nEmail: {user.email}\n"

async def _stream_local_llm(messages: List[Dict[str, Any]]) -> AsyncGenerator[str, None]:
    logger.info("🔄 LOCAL LLM Drafting...")
    payload = {"model": LOCAL_MODEL_NAME, "messages": messages, "stream": True, "options": {"temperature": 0.3}}
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", LOCAL_LLM_URL, json=payload) as response:
                async for line in response.aiter_lines():
                    if not line: continue
                    try:
                        data = json.loads(line)
                        content = data.get("message", {}).get("content", "")
                        if content: yield content
                        if data.get("done", False): break
                    except: continue
    except Exception: yield "\n[Gabim Lokal]"

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
    
    log = logger.bind(case_id=case_id, user_id=str(user.id))
    log.info("drafting_service.stream_start")

    sanitized_prompt = sterilize_text_for_llm(prompt_text)
    sanitized_context = sterilize_text_for_llm(context)

    # 1. PARALLEL DATA FETCHING
    future_laws = asyncio.to_thread(_fetch_relevant_laws_sync, sanitized_prompt)
    future_identity = asyncio.to_thread(_format_business_identity_sync, cast(Database, db), user)
    
    # PHOENIX FIX: Explicit None check for db
    library_task = asyncio.to_thread(_fetch_library_context_sync, cast(Database, db), str(user.id), sanitized_prompt) if (db is not None and use_library) else asyncio.sleep(0, result="")
    
    template_task = asyncio.sleep(0, result=None)
    # PHOENIX FIX: Explicit None check for db
    if draft_type and jurisdiction and db is not None:
        template_task = asyncio.to_thread(_get_template_augmentation_sync, draft_type, jurisdiction, favorability, cast(Database, db))

    # Wait for all background tasks to finish concurrently
    relevant_laws, business_identity, library_context, template_augment = await asyncio.gather(
        future_laws, future_identity, library_task, template_task
    )

    # 2. PROMPT CONSTRUCTION
    system_prompt = (
        "Ti je 'Juristi AI', Ekspert i Hartimit Ligjor (Kosovë). "
        "DETYRA: Harto dokumentin. "
        "FORMATI: 1. Titull i qartë. 2. Identiteti i saktë. 3. Cito ligjet. 4. Gjuhe letrare. 5. Vetëm teksti i dokumentit."
    )
    
    full_prompt = f"{business_identity}\n{relevant_laws}\n{library_context}\nKONTEKSTI:\n{sanitized_context}\n---\nKËRKESA:\n{sanitized_prompt}"
    
    if template_augment: 
        system_prompt += " Përdor strukturën specifike."
        full_prompt = f"Template:\n{template_augment}\n\n{full_prompt}"

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
                temperature=0.3,
                stream=True,
                extra_headers={"HTTP-Referer": "https://juristi.tech", "X-Title": "Juristi AI Drafting"}
            )
            async for chunk in stream:
                if chunk.choices[0].delta.content: yield chunk.choices[0].delta.content
            return
        except Exception as e:
            log.warning(f"DeepSeek Failed: {e}")

    # Fallback
    yield "**[Backup AI]**\n\n"
    async for chunk in _stream_local_llm(cast(List[Dict[str, Any]], messages)):
        yield chunk

def generate_draft_from_prompt(*args, **kwargs):
    raise NotImplementedError("Use generate_draft_stream instead.")
def generate_draft(*args, **kwargs):
    raise NotImplementedError("Use generate_draft_stream instead.")