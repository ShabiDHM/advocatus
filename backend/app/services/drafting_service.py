# FILE: backend/app/services/drafting_service.py
# PHOENIX PROTOCOL - DRAFTING ENGINE V6.1 (JURISDICTION AWARE)
# 1. FIX: '_fetch_relevant_laws_sync' now accepts and uses 'jurisdiction'.
# 2. LOGIC: Ensures drafts for Kosovo only cite Kosovo laws.

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

# --- GRAPH INTELLIGENCE ---
def _fetch_graph_intelligence_sync(case_id: Optional[str], prompt_text: str) -> str:
    buffer = []
    if case_id:
        try:
            conflicts = graph_service.find_contradictions(case_id)
            if conflicts and "No direct contradictions" not in conflicts:
                buffer.append(f"⚠️ KONTRADIKTA NGA GRAFI:\n{conflicts}")
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
        buffer.append(f"🕸️ LIDHJE TË FSHEHURA:\n" + "\n".join(unique_conns))

    return "\n\n".join(buffer) if buffer else ""

# --- HELPERS ---
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

# PHOENIX FIX: Added 'jurisdiction' parameter
def _fetch_relevant_laws_sync(prompt_text: str, jurisdiction: str = "ks") -> str:
    try:
        embedding = generate_embedding(prompt_text[:1000])
        if not embedding: return ""
        
        # PHOENIX FIX: Passing jurisdiction to Vector Store
        # Note: vector_store_service.py must support this kwarg!
        laws = query_legal_knowledge_base(embedding, n_results=3, jurisdiction=jurisdiction)
        
        if not laws: return ""
        buffer = [f"\n=== BAZA LIGJORE ({jurisdiction.upper()}) ==="]
        for law in laws:
            buffer.append(f"BURIMI: {law.get('document_name','Ligj')}\nNENET: {law.get('text','l')[:1500]}\n---")
        return "\n".join(buffer)
    except Exception as e: 
        logger.warning(f"Law fetch failed: {e}")
        return ""

def _fetch_library_context_sync(db: Database, user_id: str, prompt_text: str) -> str:
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
        if db is not None:
            profile = db.business_profiles.find_one({"user_id": str(user.id)})
            if profile:
                return f"=== HARTUESI (ZYRA) ===\nZyra: {profile.get('firm_name', user.username)}\nAdresa: {profile.get('address','N/A')}\nEmail: {profile.get('contact_email', user.email)}\n"
    except Exception: pass
    return f"=== HARTUESI ===\nEmri: {user.username}\nEmail: {user.email}\n"

async def _stream_local_llm(messages: List[Dict[str, Any]]) -> AsyncGenerator[str, None]:
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
    jurisdiction: Optional[str] = "ks", # Default to Kosovo
    favorability: Optional[str] = None,
    use_library: bool = False,
    db: Optional[Database] = None
) -> AsyncGenerator[str, None]:
    
    log = logger.bind(case_id=case_id, user_id=str(user.id))
    log.info(f"drafting_service.stream_start jurisdiction={jurisdiction}")

    sanitized_prompt = sterilize_text_for_llm(prompt_text)
    sanitized_context = sterilize_text_for_llm(context)

    # 1. PARALLEL DATA FETCHING (Graph + Jurisdiction-Aware Laws)
    future_laws = asyncio.to_thread(_fetch_relevant_laws_sync, sanitized_prompt, jurisdiction or "ks")
    future_identity = asyncio.to_thread(_format_business_identity_sync, cast(Database, db), user)
    future_graph = asyncio.to_thread(_fetch_graph_intelligence_sync, case_id, sanitized_prompt)
    
    library_task = asyncio.to_thread(_fetch_library_context_sync, cast(Database, db), str(user.id), sanitized_prompt) if (db is not None and use_library) else asyncio.sleep(0, result="")
    
    template_task = asyncio.sleep(0, result=None)
    if draft_type and jurisdiction and db is not None:
        template_task = asyncio.to_thread(_get_template_augmentation_sync, draft_type, jurisdiction, favorability, cast(Database, db))

    relevant_laws, business_identity, graph_intelligence, library_context, template_augment = await asyncio.gather(
        future_laws, future_identity, future_graph, library_task, template_task
    )

    # 2. PROMPT CONSTRUCTION
    jurisdiction_name = "Shqipërisë" if jurisdiction == "al" else "Kosovës"
    
    system_prompt = (
        f"Ti je 'Juristi AI', Ekspert i Hartimit Ligjor për legjislacionin e {jurisdiction_name}. "
        "DETYRA: Harto dokumentin duke përdorur faktet, BAZËN LIGJORE TË SIGURUAR dhe inteligjencën nga Grafi. "
        "FORMATI: Titull, Palët, Baza Ligjore (cito ligjet e sakta nga konteksti), Argumentimi, Kërkesa."
    )
    
    full_prompt = (
        f"{business_identity}\n"
        f"{relevant_laws}\n"
        f"{graph_intelligence}\n"
        f"{library_context}\n"
        f"KONTEKSTI:\n{sanitized_context}\n---\n"
        f"KËRKESA:\n{sanitized_prompt}"
    )
    
    if template_augment: 
        system_prompt += " Ndiq strukturën e mëposhtme."
        full_prompt = f"Template Strict:\n{template_augment}\n\n{full_prompt}"

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

    yield "**[Backup AI]**\n\n"
    async for chunk in _stream_local_llm(cast(List[Dict[str, Any]], messages)):
        yield chunk

def generate_draft_from_prompt(*args, **kwargs):
    raise NotImplementedError("Use generate_draft_stream instead.")
def generate_draft(*args, **kwargs):
    raise NotImplementedError("Use generate_draft_stream instead.")