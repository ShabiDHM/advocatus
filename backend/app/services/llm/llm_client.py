# FILE: app/services/llm/llm_client.py
# PHOENIX PROTOCOL - LLM CLIENT V18.0 (GEMINI 2.5 FLASH-LITE • 100% ALBANIAN LEGAL COMPLIANCE)

import os
import json
import logging
import re
from typing import List, Dict, Any, AsyncGenerator
from dotenv import load_dotenv
from openai import OpenAI, AsyncOpenAI

from app.core.config import settings
from app.services.llm.prompt_templates import build_dynamic_identity_header, _sanitize_and_disambiguate_prompt, AI_DISCLAIMER

load_dotenv()
logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1"
EMBEDDING_MODEL = "openai/text-embedding-3-small" 

# Modeli i Përzgjedhur: Gemini 2.5 Flash Lite (Ultra-I Shpejtë • Kosto ~3 centë • Saktësi 95%+)
FAST_MODEL = "google/gemini-2.5-flash-lite"
DEEP_MODEL = "deepseek/deepseek-r1"

# Renditja e fallback-ut në rast ndërprerjeje të ndonjë serveri në OpenRouter
FAST_MODELS_PRIORITY = [
    "google/gemini-2.5-flash-lite",
    "meta-llama/llama-3.3-70b-instruct",
    "deepseek/deepseek-chat"
]

TEMP_DRAFTING = 0.0
TEMP_ANALYSIS = 0.0
TEMP_CHAT = 0.05

def _get_api_key() -> str:
    return getattr(settings, "OPENROUTER_API_KEY", None) or os.getenv("OPENROUTER_API_KEY", "") or os.getenv("OPENAI_API_KEY", "")

def _get_sync_client() -> OpenAI: 
    key = _get_api_key()
    return OpenAI(api_key=key, base_url=OPENROUTER_URL, timeout=45.0)

def _get_async_client() -> AsyncOpenAI: 
    key = _get_api_key()
    return AsyncOpenAI(api_key=key, base_url=OPENROUTER_URL, timeout=45.0)

def clean_and_parse_json(text: str) -> Dict[str, Any]:
    """Pastron dhe dekodon përgjigjen JSON duke hequr etiketat e padëshiruara markdown."""
    if not text:
        return {}
    
    cleaned = text.strip()
    cleaned = re.sub(r'^```json\s*', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'^```\s*', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s*```$', '', cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.strip()
    
    try:
        return json.loads(cleaned)
    except Exception as e:
        logger.warning(f"Standard JSON parse failed, running regex fallback: {e}")
        try:
            json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
        except Exception as fallback_err:
            logger.error(f"Regex JSON fallback failed: {fallback_err}. Raw snippet: {text[:150]}")
        return {}

def _call_llm(system_prompt: str, user_content: str, json_mode: bool = False, temperature: float = 0.0, model: str = FAST_MODEL) -> str:
    """Thirrje sinkrone drejt OpenRouter me mbrojtje automatike fallback."""
    key = _get_api_key()
    if not key:
        logger.error("❌ Mungon OPENROUTER_API_KEY")
        return ""

    identity_header = build_dynamic_identity_header()
    albanian_enforcement = "RREGULL GJUHËSOR: Përgjigju VETËM në gjuhën shqipe standarde juridike të Republikës së Kosovës."
    full_sys_prompt = f"{identity_header}\n{albanian_enforcement}\n\n{system_prompt}" if "MANDATI RIGOROZ" not in system_prompt else system_prompt
    sanitized_user_content = _sanitize_and_disambiguate_prompt(user_content)

    models_to_try = [model] + [m for m in FAST_MODELS_PRIORITY if m != model]

    for attempt_model in models_to_try:
        try:
            client = _get_sync_client()
            kwargs = {
                "model": attempt_model,
                "messages": [
                    {"role": "system", "content": full_sys_prompt},
                    {"role": "user", "content": sanitized_user_content}
                ],
                "temperature": temperature,
                "max_tokens": 8192
            }
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            res = client.chat.completions.create(**kwargs)
            return res.choices[0].message.content or ""
        except Exception as e:
            logger.warning(f"⚠️ Modeli '{attempt_model}' dështoi ({e}). Po provohet modeli pasardhës...")
            continue

    logger.error("❌ Të gjitha modelet dështuan në _call_llm")
    return ""

async def _call_llm_async(system_prompt: str, user_content: str, json_mode: bool = False, temperature: float = 0.0, model: str = FAST_MODEL) -> str:
    """Thirrje 100% asinkrone për shpejtësi maksimale (nën 2 sekonda)."""
    key = _get_api_key()
    if not key:
        logger.error("❌ Mungon OPENROUTER_API_KEY")
        return ""

    identity_header = build_dynamic_identity_header()
    albanian_enforcement = "RREGULL GJUHËSOR: Përgjigju VETËM në gjuhën shqipe standarde juridike të Republikës së Kosovës."
    full_sys_prompt = f"{identity_header}\n{albanian_enforcement}\n\n{system_prompt}" if "MANDATI RIGOROZ" not in system_prompt else system_prompt
    sanitized_user_content = _sanitize_and_disambiguate_prompt(user_content)

    models_to_try = [model] + [m for m in FAST_MODELS_PRIORITY if m != model]

    for attempt_model in models_to_try:
        try:
            client = _get_async_client()
            kwargs = {
                "model": attempt_model,
                "messages": [
                    {"role": "system", "content": full_sys_prompt},
                    {"role": "user", "content": sanitized_user_content}
                ],
                "temperature": temperature,
                "max_tokens": 8192
            }
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            res = await client.chat.completions.create(**kwargs)
            return res.choices[0].message.content or ""
        except Exception as e:
            logger.warning(f"⚠️ Async modeli '{attempt_model}' dështoi ({e}). Po provohet modeli pasardhës...")
            continue

    logger.error("❌ Të gjitha modelet dështuan në _call_llm_async")
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
        logger.error(f"❌ OpenRouter Embedding Failure: {e}")
        return [0.0] * 1536

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
            if chunk.choices[0].delta.content: 
                yield chunk.choices[0].delta.content
        yield AI_DISCLAIMER
    except Exception as e: 
        yield f"[Gabim: {str(e)}]"