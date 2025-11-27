# FILE: backend/app/services/drafting_service.py
# PHOENIX PROTOCOL - FULL IMPLEMENTATION
# 1. ANALYSIS: Pylance errors were caused by empty helper functions that violated their declared return types.
# 2. FIX: Restored the full, correct implementations for '_get_template_augmentation', '_fetch_relevant_laws', and '_stream_local_llm'.
# 3. RESULT: All functions now adhere to their type contracts, resolving all 'reportReturnType' and 'reportGeneralTypeIssues' errors.

import os
import asyncio
import structlog
import httpx
import json
from typing import AsyncGenerator, Optional, List, Any, cast, Dict
from groq import AsyncGroq
from groq.types.chat import ChatCompletionMessageParam
from pymongo.database import Database

from ..models.user import UserInDB
from app.services.text_sterilization_service import sterilize_text_for_llm
from .vector_store_service import query_legal_knowledge_base
from .embedding_service import generate_embedding

logger = structlog.get_logger(__name__)

# --- CONFIGURATION ---
LOCAL_LLM_URL = os.environ.get("LOCAL_LLM_URL", "http://local-llm:11434/api/chat")
LOCAL_MODEL_NAME = "llama3"

def _get_template_augmentation(draft_type: str, jurisdiction: str, favorability: Optional[str], db: Database) -> Optional[str]:
    template_filter = {
        "document_type": draft_type,
        "jurisdiction": jurisdiction,
        "favorability": favorability
    }
    template = db.document_templates.find_one(template_filter)
    if not template:
        return None
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
        logger.error("drafting_service.template_augmentation_error", error=str(e), exc_info=True)
        return None

def _fetch_relevant_laws(prompt_text: str) -> str:
    """
    Searches the Vector Database for laws relevant to the drafting request.
    """
    try:
        embedding = generate_embedding(prompt_text[:1000])
        if not embedding: return ""

        laws = query_legal_knowledge_base(embedding, n_results=3)
        if not laws: return ""

        law_buffer = ["\n=== BAZA LIGJORE E DETYRUESHME (NGA DATABAZA) ==="]
        for law in laws:
            source = law.get('document_name', 'Ligj')
            text = law.get('text', '')[:1500]
            law_buffer.append(f"BURIMI: {source}\nNENET: {text}\n---")
        return "\n".join(law_buffer)
    except Exception as e:
        logger.warning(f"Drafting RAG Lookup failed: {e}")
        return ""

async def _stream_local_llm(messages: List[Dict[str, Any]]) -> AsyncGenerator[str, None]:
    """Tier 2: Local LLM Stream"""
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

async def generate_draft_stream(
    context: str,
    prompt_text: Optional[str],
    user: UserInDB,
    draft_type: Optional[str] = None,
    case_id: Optional[str] = None,
    jurisdiction: Optional[str] = None,
    favorability: Optional[str] = None,
    db: Optional[Database] = None
) -> AsyncGenerator[str, None]:
    log = logger.bind(case_id=case_id, user_id=str(user.id), draft_type=draft_type)
    prompt_text = prompt_text or ""
    log.info("drafting_service.stream_start", prompt_length=len(prompt_text))

    sanitized_context = sterilize_text_for_llm(context)
    sanitized_prompt_text = sterilize_text_for_llm(prompt_text)

    relevant_laws = await asyncio.to_thread(_fetch_relevant_laws, sanitized_prompt_text)

    system_prompt = (
        "Ti je 'Juristi AI', një ekspert për hartimin e dokumenteve ligjore në Kosovë dhe Shqipëri. "
        "DETYRA: Harto një dokument profesional bazuar në kërkesën e përdoruesit. "
        "RREGULLAT: "
        "1. Përdor gjuhë formale juridike. "
        "2. Nëse ka 'BAZA LIGJORE' të ofruar më poshtë, sigurohu që drafti të jetë në përputhje me to. "
        "3. Mos shto komente shtesë, vetëm tekstin e dokumentit."
    )

    full_prompt = f"Context:\n{sanitized_context}\n\n---\n\nPrompt:\n{sanitized_prompt_text}"
    
    if relevant_laws:
        full_prompt = f"{relevant_laws}\n\n{full_prompt}"
        log.info("drafting_service.rag_injected")

    if draft_type and jurisdiction and db is not None:
        template_augment = await asyncio.to_thread(_get_template_augmentation, draft_type, jurisdiction, favorability, db)
        if template_augment:
            system_prompt += f" Përdor strukturën specifike për: {draft_type} ({jurisdiction})."
            full_prompt = f"Template Instructions:\n{template_augment}\n\n---\n\n{full_prompt}"

    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": full_prompt}
    ]

    tier1_failed = False
    groq_api_key = os.environ.get("GROQ_API_KEY")
    
    if groq_api_key:
        try:
            groq_model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
            GROQ_CLIENT = AsyncGroq(api_key=groq_api_key)
            typed_messages = cast(List[ChatCompletionMessageParam], messages)
            
            stream = await GROQ_CLIENT.chat.completions.create(
                messages=typed_messages,
                model=groq_model,
                temperature=0.3,
                stream=True,
            )
            async for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
            
            log.info("drafting_service.stream_success_cloud")
            return

        except Exception as e:
            log.warning(f"⚠️ Groq Drafting Failed: {e}")
            tier1_failed = True
    else:
        tier1_failed = True

    if tier1_failed:
        yield "**[Draft i Gjeneruar nga AI Lokale]**\n\n"
        async for chunk in _stream_local_llm(messages):
            yield chunk
        log.info("drafting_service.stream_success_local")

# Legacy
def generate_draft_from_prompt(*args, **kwargs):
    raise NotImplementedError("Use generate_draft_stream instead.")
def generate_draft(*args, **kwargs):
    raise NotImplementedError("Use generate_draft_stream instead.")