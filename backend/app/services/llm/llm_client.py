# FILE: backend/app/services/llm/llm_client.py
# PHOENIX PROTOCOL - PURE UNIFIED DEEPSEEK CLIENT V84.0 (ZERO REDUNDANT CONSTANTS)
# 100% COMPLETE CODE • ZERO ALIASES • ZERO MULTI-MODEL LEFTOVERS • 429 AUTO-RETRY

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

OPENROUTER_URL = "https://openrouter.ai/api/v1"
EMBEDDING_MODEL = "openai/text-embedding-3-small"

TEMP_ANALYSIS = 0.0
TEMP_FORENSIC = 0.0
TEMP_DRAFTING = 0.0
TEMP_CHAT = 0.05

OPENROUTER_HEADERS = {
    "HTTP-Referer": "https://juristi.tech",
    "X-Title": "Juristi AI - Kosova Legal Tech Orchestrator"
}

def _get_api_key() -> str:
    return (
        getattr(settings, "OPENROUTER_API_KEY", None)
        or os.getenv("OPENROUTER_API_KEY", "")
        or os.getenv("OPENAI_API_KEY", "")
    )

def _get_target_model() -> str:
    """Lexon modelin e vetëm global nga settings.LLM_MODEL."""
    model = (
        getattr(settings, "LLM_MODEL", None) or 
        os.getenv("LLM_MODEL", "") or 
        "deepseek/deepseek-chat"
    )
    if "claude" in model.lower() or "anthropic" in model.lower():
        model = "deepseek/deepseek-chat"
    return model

def _get_sync_client() -> OpenAI: 
    key = _get_api_key()
    return OpenAI(
        api_key=key, 
        base_url=OPENROUTER_URL, 
        timeout=300.0,
        default_headers=OPENROUTER_HEADERS
    )

def _get_async_client() -> AsyncOpenAI: 
    key = _get_api_key()
    return AsyncOpenAI(
        api_key=key, 
        base_url=OPENROUTER_URL, 
        timeout=300.0,
        default_headers=OPENROUTER_HEADERS
    )

def _get_provider_routing_payload() -> Dict[str, Any]:
    """Lejon të gjitha nyjet e DeepSeek me failover automatik dhe zero bllokime 404."""
    return {
        "provider": {
            "allow_fallbacks": True
        }
    }

def _apply_hallucination_filter(text: str) -> str:
    try:
        from app.services.pillars.hallucination_filter import HallucinationFilter
        return HallucinationFilter.filter_precedents(text)
    except Exception:
        return text

def clean_and_parse_json(text: str) -> Dict[str, Any]:
    if not text:
        return {}
    
    cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
    
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
            return json.loads(cleaned[first_brace:last_brace + 1])
    except Exception:
        pass

    return {}

def _prepare_system_prompt(system_prompt: str) -> str:
    if "[MANDATI DHE IDENTITETI I LËNDËS]" in system_prompt or "MANDATI RIGOROZ" in system_prompt:
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
        return ""

    full_sys_prompt = _prepare_system_prompt(system_prompt)
    sanitized_user_content = _sanitize_and_disambiguate_prompt(user_content)
    client = _get_sync_client()
    target_model = _get_target_model()

    kwargs: Dict[str, Any] = {
        "model": target_model,
        "messages": [
            {"role": "system", "content": full_sys_prompt},
            {"role": "user", "content": sanitized_user_content}
        ],
        "temperature": temperature,
        "max_tokens": 8192,
        "extra_body": _get_provider_routing_payload()
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    for attempt in range(1, 4):
        try:
            res = client.chat.completions.create(**kwargs)
            if res and hasattr(res, 'choices') and res.choices and len(res.choices) > 0:
                raw_content = getattr(res.choices[0].message, 'content', '') or ""
                if raw_content.strip():
                    return _apply_hallucination_filter(raw_content)
        except Exception as e:
            err_msg = str(e).lower()
            if "429" in err_msg or "rate limit" in err_msg:
                logger.warning(f"⚠️ [Rate Limit 429] në DeepSeek. Po pres {2 * attempt}s...")
                time.sleep(2.0 * attempt)
                continue
            logger.warning(f"⚠️ Përpjekja {attempt} në DeepSeek dështoi: {e}")
            time.sleep(1.5)

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
        return ""

    full_sys_prompt = _prepare_system_prompt(system_prompt)
    sanitized_user_content = _sanitize_and_disambiguate_prompt(user_content)
    client = _get_async_client()
    target_model = _get_target_model()

    kwargs: Dict[str, Any] = {
        "model": target_model,
        "messages": [
            {"role": "system", "content": full_sys_prompt},
            {"role": "user", "content": sanitized_user_content}
        ],
        "temperature": temperature,
        "max_tokens": 8192,
        "extra_body": _get_provider_routing_payload()
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    for attempt in range(1, 4):
        try:
            res = await client.chat.completions.create(**kwargs)
            if res and hasattr(res, 'choices') and res.choices and len(res.choices) > 0:
                content = getattr(res.choices[0].message, 'content', '') or ""
                if content.strip():
                    return _apply_hallucination_filter(content)
        except Exception as e:
            err_msg = str(e).lower()
            if "429" in err_msg or "rate limit" in err_msg:
                logger.warning(f"⚠️ [Rate Limit 429] në DeepSeek async. Po pres {2 * attempt}s...")
                await asyncio.sleep(2.0 * attempt)
                continue
            logger.warning(f"⚠️ Përpjekja {attempt} në DeepSeek dështoi: {e}")
            await asyncio.sleep(1.5)

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
    target_model = _get_target_model()

    kwargs: Dict[str, Any] = {
        "model": target_model,
        "messages": [
            {"role": "system", "content": full_sys},
            {"role": "user", "content": sanitized_user_p}
        ],
        "temperature": temp,
        "stream": True,
        "max_tokens": 8192,
        "extra_body": _get_provider_routing_payload()
    }

    last_err: Optional[Exception] = None

    for attempt in range(1, 4):
        try:
            stream = await client.chat.completions.create(**kwargs)
            async for chunk in stream:
                if chunk.choices and len(chunk.choices) > 0 and chunk.choices[0].delta.content: 
                    yield chunk.choices[0].delta.content
            
            yield AI_DISCLAIMER
            return
        except Exception as e:
            last_err = e
            err_msg = str(e).lower()
            if "429" in err_msg or "rate limit" in err_msg:
                logger.warning(f"⚠️ [Rate Limit 429] në DeepSeek stream. Po pres {2 * attempt}s...")
                await asyncio.sleep(2.0 * attempt)
                continue
            await asyncio.sleep(1.5)

    yield f"\n\n[Shërbimi DeepSeek është përkohësisht i ngarkuar nga fluksi i lartë. Ju lutem provoni përsëri pas pak sekondash.]"