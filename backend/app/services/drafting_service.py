# FILE: backend/app/services/drafting_service.py
# PHOENIX PROTOCOL - HYBRID DRAFTING ENGINE
# 1. TIER 1: Groq Cloud (High Precision).
# 2. TIER 2: Local Ollama (Offline/Fallback Mode).
# 3. STREAMING: Supports streaming for both Cloud and Local engines.

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

async def _stream_local_llm(messages: List[Dict[str, Any]]) -> AsyncGenerator[str, None]:
    """
    Tier 2: Streams the draft from the internal Local LLM (Ollama).
    Used when Cloud API is down or rate-limited.
    """
    logger.info("🔄 Switching to LOCAL LLM (Ollama) for drafting...")
    
    payload = {
        "model": LOCAL_MODEL_NAME,
        "messages": messages,
        "stream": True,
        "options": {
            "temperature": 0.3, 
            "num_ctx": 8192 # Increased context for drafting
        }
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", LOCAL_LLM_URL, json=payload) as response:
                if response.status_code != 200:
                    logger.error(f"Local LLM Error: {response.status_code}")
                    yield "\n[Gabim: Sistemi lokal nuk u përgjigj.]"
                    return

                async for line in response.aiter_lines():
                    if not line: continue
                    try:
                        data = json.loads(line)
                        # Ollama chat response format
                        content = data.get("message", {}).get("content", "")
                        if content:
                            yield content
                        if data.get("done", False):
                            break
                    except Exception:
                        continue
    except Exception as e:
        logger.error("drafting_service.local_llm_failed", error=str(e))
        yield "\n\n[Gabim Kritik: Edhe sistemi lokal nuk është i disponueshëm.]"

async def generate_draft_stream(
    context: str,
    prompt_text: str,
    user: UserInDB,
    draft_type: Optional[str] = None,
    case_id: Optional[str] = None,
    jurisdiction: Optional[str] = None,
    favorability: Optional[str] = None,
    db: Optional[Database] = None
) -> AsyncGenerator[str, None]:
    log = logger.bind(case_id=case_id, user_id=str(user.id), draft_type=draft_type)
    if prompt_text is None: prompt_text = ""
    log.info("drafting_service.stream_start", prompt_length=len(prompt_text))

    sanitized_context = sterilize_text_for_llm(context)
    sanitized_prompt_text = sterilize_text_for_llm(prompt_text)

    # Prepare Prompts
    system_prompt = (
        "You are an expert legal drafter for the legal markets of Kosovo and Albania named Phoenix. "
        "Your task is to generate a professional, well-structured document in response to the user's request. "
        "Maintain a formal, objective, and precise tone. "
        "Your response MUST be ONLY the generated legal text. Do not add any commentary. "
        "The generated text MUST be in the Albanian language."
    )
    full_prompt = f"Context:\n{sanitized_context}\n\n---\n\nPrompt:\n{sanitized_prompt_text}"

    # Template Augmentation
    if draft_type and jurisdiction and db is not None:
        template_augment = await asyncio.to_thread(_get_template_augmentation, draft_type, jurisdiction, favorability, db)
        if template_augment:
            system_prompt = system_prompt.replace("well-structured document", f"well-structured {draft_type} for {jurisdiction}")
            full_prompt = f"Template/Clause Guidance:\n{template_augment}\n\n---\n\n{full_prompt}"
            log.info("drafting_service.template_augmented", template=draft_type)

    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": full_prompt}
    ]

    # --- TIER 1: GROQ CLOUD ---
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
            return # Tier 1 Success

        except Exception as e:
            error_str = str(e).lower()
            log.warning(f"⚠️ Groq Drafting Failed: {e}")
            if "rate limit" in error_str or "429" in error_str or "quota" in error_str or "model" in error_str:
                tier1_failed = True
            else:
                # For network errors, we also fallback
                tier1_failed = True
    else:
        tier1_failed = True # No key configured

    # --- TIER 2: LOCAL LLM FALLBACK ---
    if tier1_failed:
        yield "**[Draft i Gjeneruar nga AI Lokale (Offline Mode)]**\n\n"
        async for chunk in _stream_local_llm(messages):
            yield chunk
        log.info("drafting_service.stream_success_local")


# --- Legacy Functions ---
def generate_draft_from_prompt(*args, **kwargs):
    raise NotImplementedError("Use generate_draft_stream instead.")
def generate_draft(*args, **kwargs):
    raise NotImplementedError("This legacy template function is not implemented.")