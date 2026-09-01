# FILE: backend/app/services/llm/llm_client.py
# PHOENIX PROTOCOL - TIER-1 ORCHESTRATION CLIENT V45.1 (CLAUDE-3.5 / GPT-4O / ZERO-HALLUCINATION LOCK)

import os
import json
import logging
import re
import asyncio
import time
from typing import List, Dict, Any, AsyncGenerator, Optional
from dotenv import load_dotenv
from openai import OpenAI, AsyncOpenAI

from app.core.config import settings
from app.services.llm.prompt_templates import (
    build_dynamic_identity_header, 
    _sanitize_and_disambiguate_prompt, 
    AI_DISCLAIMER
)

load_dotenv()
logger = logging.getLogger(__name__)

# ========== KONFIGURIMI I OPENROUTER & MODELEVE TIER-1 ==========
OPENROUTER_URL = "https://openrouter.ai/api/v1"
EMBEDDING_MODEL = "openai/text-embedding-3-small"

# Modelet Parësore dhe Hierarkia e Fallback
PRIMARY_MODEL = os.getenv("LLM_PRIMARY_MODEL", "anthropic/claude-3.5-sonnet")
FAST_MODEL = os.getenv("LLM_FAST_MODEL", "anthropic/claude-3.5-sonnet")
DEEP_MODEL = os.getenv("LLM_DEEP_MODEL", "anthropic/claude-3.5-sonnet")

FALLBACK_MODELS = [
    "anthropic/claude-3.5-sonnet",
    "openai/gpt-4o",
    "deepseek/deepseek-chat",
    "deepseek/deepseek-r1"
]

# Kalibrimi i Temperaturave (Zero Hallucination)
TEMP_ANALYSIS = 0.0
TEMP_FORENSIC = 0.0
TEMP_DRAFTING = 0.0
TEMP_CHAT = 0.05

OPENROUTER_HEADERS = {
    "HTTP-Referer": "https://juristi-ai.com",
    "X-Title": "Juristi AI - Kosova Legal Tech Orchestrator"
}

def _get_api_key() -> str:
    return (
        getattr(settings, "OPENROUTER_API_KEY", None)
        or os.getenv("OPENROUTER_API_KEY", "")
        or os.getenv("OPENAI_API_KEY", "")
    )

def _get_sync_client() -> OpenAI: 
    key = _get_api_key()
    return OpenAI(
        api_key=key, 
        base_url=OPENROUTER_URL, 
        timeout=90.0,
        default_headers=OPENROUTER_HEADERS
    )

def _get_async_client() -> AsyncOpenAI: 
    key = _get_api_key()
    return AsyncOpenAI(
        api_key=key, 
        base_url=OPENROUTER_URL, 
        timeout=90.0,
        default_headers=OPENROUTER_HEADERS
    )

def _apply_hallucination_filter(text: str) -> str:
    """
    Aplikon filtrin e verifikimit të precedentëve dhe neneve ligjore.
    """
    try:
        from app.services.pillars.hallucination_filter import HallucinationFilter
        return HallucinationFilter.filter_precedents(text)
    except ImportError:
        return text
    except Exception as e:
        logger.warning(f"⚠️ [Filter] Gabim gjatë filtrimit: {e}")
        return text

def clean_and_parse_json(text: str) -> Dict[str, Any]:
    """
    Pastron përgjigjen nga tag-et <think>, markdown ```json dhe nxjerr objektin e vlefshëm JSON.
    """
    if not text:
        return {}
    
    cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    cleaned = cleaned.strip()
    
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    json_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', cleaned, re.DOTALL)
    if json_block_match:
        try:
            return json.loads(json_block_match.group(1).strip())
        except Exception:
            pass

    try:
        first_brace = cleaned.find('{')
        last_brace = cleaned.rfind('}')
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            candidate = cleaned[first_brace:last_brace + 1]
            return json.loads(candidate)
    except Exception as parse_err:
        logger.warning(f"⚠️ JSON parsing extraction fallback dështoi: {parse_err}")
        pass

    return {}

def _prepare_system_prompt(system_prompt: str) -> str:
    """
    Garanton që prompti të ketë kornizën gjuhësore pa duplikuar header-at ekzistues.
    """
    if "[MANDATI DHE IDENTITETI I LËNDËS]" in system_prompt or "MANDATI RIGOROZ" in system_prompt or "AUTORITETI DHE IDENTITETI" in system_prompt:
        return system_prompt
    
    identity_header = build_dynamic_identity_header()
    albanian_enforcement = "RREGULL GJUHËSOR I HEKURT: Përgjigju VETËM në gjuhën shqipe standarde juridike të Republikës së Kosovës."
    return f"{identity_header}\n{albanian_enforcement}\n\n{system_prompt}"

def _call_llm(
    system_prompt: str, 
    user_content: str, 
    json_mode: bool = False, 
    temperature: float = TEMP_ANALYSIS, 
    model: Optional[str] = None
) -> str:
    key = _get_api_key()
    if not key:
        logger.error("❌ Mungon OPENROUTER_API_KEY")
        return ""

    full_sys_prompt = _prepare_system_prompt(system_prompt)
    sanitized_user_content = _sanitize_and_disambiguate_prompt(user_content)
    client = _get_sync_client()

    target_models = [model] if model else [PRIMARY_MODEL] + [m for m in FALLBACK_MODELS if m != PRIMARY_MODEL]

    for current_model in target_models:
        kwargs = {
            "model": current_model,
            "messages": [
                {"role": "system", "content": full_sys_prompt},
                {"role": "user", "content": sanitized_user_content}
            ],
            "temperature": temperature,
            "max_tokens": 8192
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        for attempt in range(2):
            try:
                res = client.chat.completions.create(**kwargs)
                if res and hasattr(res, 'choices') and res.choices and len(res.choices) > 0:
                    raw_content = getattr(res.choices[0].message, 'content', '') or ""
                    if raw_content.strip():
                        return _apply_hallucination_filter(raw_content)
            except Exception as e:
                err_msg = str(e)
                if "429" in err_msg or "rate limit" in err_msg.lower():
                    time.sleep(1.5 * (attempt + 1))
                    continue
                logger.warning(f"⚠️ Dështoi thirrja me modelin {current_model}: {err_msg}")
                break

    logger.error("❌ Të gjitha modelet e LLM dështuan në _call_llm.")
    return ""

async def _call_llm_async(
    system_prompt: str, 
    user_content: str, 
    json_mode: bool = False, 
    temperature: float = TEMP_ANALYSIS, 
    model: Optional[str] = None
) -> str:
    key = _get_api_key()
    if not key:
        logger.error("❌ Mungon OPENROUTER_API_KEY")
        return ""

    full_sys_prompt = _prepare_system_prompt(system_prompt)
    sanitized_user_content = _sanitize_and_disambiguate_prompt(user_content)
    client = _get_async_client()

    target_models = [model] if model else [PRIMARY_MODEL] + [m for m in FALLBACK_MODELS if m != PRIMARY_MODEL]

    for current_model in target_models:
        kwargs = {
            "model": current_model,
            "messages": [
                {"role": "system", "content": full_sys_prompt},
                {"role": "user", "content": sanitized_user_content}
            ],
            "temperature": temperature,
            "max_tokens": 8192
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        for attempt in range(2):
            try:
                res = await client.chat.completions.create(**kwargs)
                if res and hasattr(res, 'choices') and res.choices and len(res.choices) > 0:
                    content = getattr(res.choices[0].message, 'content', '') or ""
                    if content.strip():
                        return _apply_hallucination_filter(content)
            except Exception as e:
                err_msg = str(e)
                if "429" in err_msg or "rate limit" in err_msg.lower():
                    await asyncio.sleep(1.5 * (attempt + 1))
                    continue
                logger.warning(f"⚠️ Dështoi thirrja async me modelin {current_model}: {err_msg}")
                break

    logger.error("❌ Të gjitha modelet e LLM dështuan në _call_llm_async.")
    return ""

def get_embedding(text: str) -> List[float]:
    key = _get_api_key()
    if not text or not key: 
        return [0.0] * 1536
    try:
        client = _get_sync_client()
        res = client.embeddings.create(input=[text.replace("\n", " ")], model=EMBEDDING_MODEL)
        return res.data[0].embedding
    except Exception as e:
        logger.error(f"❌ Embedding Failure: {e}")
        return [0.0] * 1536

def get_embeddings_batch(texts: List[str]) -> List[List[float]]:
    key = _get_api_key()
    if not texts or not key: 
        return [[0.0] * 1536 for _ in texts]
    try:
        clean_inputs = [t.replace("\n", " ").strip() or " " for t in texts]
        client = _get_sync_client()
        res = client.embeddings.create(input=clean_inputs, model=EMBEDDING_MODEL)
        return [item.embedding for item in res.data]
    except Exception as e:
        logger.error(f"❌ Batch Embedding Failure: {e}")
        return [get_embedding(t) for t in texts]

async def stream_text_async(
    sys_p: str, 
    user_p: str, 
    temp: float = TEMP_CHAT, 
    model: Optional[str] = None
) -> AsyncGenerator[str, None]:
    client = _get_async_client()
    full_sys = _prepare_system_prompt(sys_p)
    sanitized_user_p = _sanitize_and_disambiguate_prompt(user_p)
    selected_model = model or PRIMARY_MODEL

    try:
        stream = await client.chat.completions.create(
            model=selected_model,
            messages=[
                {"role": "system", "content": full_sys},
                {"role": "user", "content": sanitized_user_p}
            ],
            temperature=temp,
            stream=True,
            max_tokens=8192
        )
        async for chunk in stream:
            if chunk.choices and len(chunk.choices) > 0 and chunk.choices[0].delta.content: 
                yield chunk.choices[0].delta.content
        yield AI_DISCLAIMER
    except Exception as e: 
        logger.error(f"❌ Error in stream_text_async: {e}")
        yield f"\n\n[Gabim gjatë gjenerimit: {str(e)}]"