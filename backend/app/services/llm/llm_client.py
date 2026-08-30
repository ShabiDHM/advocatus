# FILE: backend/app/services/llm/llm_client.py
# PHOENIX PROTOCOL - LLM CLIENT V28.0 (HALLUCINATION FILTER INTEGRATED)

import os
import json
import logging
import re
import asyncio
from typing import List, Dict, Any, AsyncGenerator
from dotenv import load_dotenv
from openai import OpenAI, AsyncOpenAI

from app.core.config import settings
from app.services.llm.prompt_templates import build_dynamic_identity_header, _sanitize_and_disambiguate_prompt, AI_DISCLAIMER

load_dotenv()
logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1"
EMBEDDING_MODEL = "openai/text-embedding-3-small" 

FAST_MODEL = "deepseek/deepseek-chat"
DEEP_MODEL = "deepseek/deepseek-r1"

TEMP_DRAFTING = 0.0
TEMP_ANALYSIS = 0.0
TEMP_CHAT = 0.05

def _get_api_key() -> str:
    return getattr(settings, "OPENROUTER_API_KEY", None) or os.getenv("OPENROUTER_API_KEY", "") or os.getenv("OPENAI_API_KEY", "")

def _get_sync_client() -> OpenAI: 
    key = _get_api_key()
    return OpenAI(api_key=key, base_url=OPENROUTER_URL, timeout=60.0)

def _get_async_client() -> AsyncOpenAI: 
    key = _get_api_key()
    return AsyncOpenAI(api_key=key, base_url=OPENROUTER_URL, timeout=60.0)

def _apply_hallucination_filter(text: str) -> str:
    """
    PHOENIX FIX V28.0: Aplikon filtrin e halucinacioneve në çdo përgjigje.
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
        logger.warning(f"⚠️ JSON parsing extraction fallback failed: {parse_err}")
        pass

    return {}

def _call_llm(system_prompt: str, user_content: str, json_mode: bool = False, temperature: float = 0.0, model: str = FAST_MODEL) -> str:
    key = _get_api_key()
    if not key:
        logger.error("❌ Mungon OPENROUTER_API_KEY")
        return ""

    identity_header = build_dynamic_identity_header()
    albanian_enforcement = "RREGULL GJUHËSOR: Përgjigju VETËM në gjuhën shqipe standarde juridike të Republikës së Kosovës."
    full_sys_prompt = f"{identity_header}\n{albanian_enforcement}\n\n{system_prompt}" if "MANDATI RIGOROZ" not in system_prompt else system_prompt
    sanitized_user_content = _sanitize_and_disambiguate_prompt(user_content)

    client = _get_sync_client()
    kwargs = {
        "model": model or FAST_MODEL,
        "messages": [
            {"role": "system", "content": full_sys_prompt},
            {"role": "user", "content": sanitized_user_content}
        ],
        "temperature": temperature,
        "max_tokens": 8192
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    for attempt in range(3):
        try:
            res = client.chat.completions.create(**kwargs)
            if res and hasattr(res, 'choices') and res.choices and len(res.choices) > 0:
                msg = res.choices[0].message
                raw_content = getattr(msg, 'content', '') or ""
                # PHOENIX FIX: Aplikoni filtrin
                return _apply_hallucination_filter(raw_content)
            return ""
        except Exception as e:
            if "429" in str(e) and attempt < 2:
                import time
                time.sleep(1.5 * (attempt + 1))
                continue
            logger.error(f"❌ Error in _call_llm ({model}): {e}")
            return ""
    return ""

async def _call_llm_async(system_prompt: str, user_content: str, json_mode: bool = False, temperature: float = 0.0, model: str = FAST_MODEL) -> str:
    key = _get_api_key()
    if not key:
        logger.error("❌ Mungon OPENROUTER_API_KEY")
        return ""

    identity_header = build_dynamic_identity_header()
    albanian_enforcement = "RREGULL GJUHËSOR: Përgjigju VETËM në gjuhën shqipe standarde juridike të Republikës së Kosovës."
    full_sys_prompt = f"{identity_header}\n{albanian_enforcement}\n\n{system_prompt}" if "MANDATI RIGOROZ" not in system_prompt else system_prompt
    sanitized_user_content = _sanitize_and_disambiguate_prompt(user_content)

    client = _get_async_client()
    kwargs = {
        "model": model or FAST_MODEL,
        "messages": [
            {"role": "system", "content": full_sys_prompt},
            {"role": "user", "content": sanitized_user_content}
        ],
        "temperature": temperature,
        "max_tokens": 8192
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    for attempt in range(3):
        try:
            res = await client.chat.completions.create(**kwargs)
            if res and hasattr(res, 'choices') and res.choices and len(res.choices) > 0:
                msg = res.choices[0].message
                content = getattr(msg, 'content', '') or ""
                if content:
                    # PHOENIX FIX: Aplikoni filtrin
                    return _apply_hallucination_filter(content)
            logger.warning(f"⚠️ Empty choice response on attempt {attempt + 1}")
        except Exception as e:
            if "429" in str(e) and attempt < 2:
                await asyncio.sleep(1.5 * (attempt + 1))
                continue
            logger.error(f"❌ Error in _call_llm_async ({model}): {e}")
            return ""
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

async def stream_text_async(sys_p: str, user_p: str, temp: float = 0.05, model: str = FAST_MODEL) -> AsyncGenerator[str, None]:
    client = _get_async_client()
    try:
        identity_header = build_dynamic_identity_header()
        full_sys = f"{identity_header}\n\n{sys_p}" if "MANDATI RIGOROZ" not in sys_p else sys_p
        sanitized_user_p = _sanitize_and_disambiguate_prompt(user_p)

        stream = await client.chat.completions.create(
            model=model,
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
        yield f"[Gabim: {str(e)}]"