# FILE: backend/app/services/forensic/forensic_llm_service.py
# PHOENIX PROTOCOL - FORENSIC DEDICATED LLM ENGINE V5.0 (HIGH-CONTEXT 64K+ ROUTING)
# 100% COMPLETE CODE • EXCLUSIVE DEEPSEEK CORE • BYPASS 32K CRIPPLED PROVIDERS (DEEPINFRA IGNORED)

import os
import time
import asyncio
import logging
from typing import Dict, Any, List, AsyncGenerator, Optional
from openai import OpenAI, AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1"

FORENSIC_SYSTEM_IDENTITY = """You are a senior forensic legal expert specialized in the legislation and jurisprudence of the Republic of Kosovo.
Provide accurate, highly professional, doctrinally sound, and exhaustive responses in standard Albanian legal language.
Do not use marketing phrases, filler words, or emojis.
Strictly cite statutes article-by-article and extract literal evidentiary facts from the court dossier."""

class ForensicLLMError(Exception):
    pass

def _get_openrouter_key() -> str:
    key = getattr(settings, "OPENROUTER_API_KEY", None) or os.getenv("OPENROUTER_API_KEY", "")
    if not key:
        raise ForensicLLMError("OPENROUTER_API_KEY nuk është konfiguruar në server për Zyrën Forenzike.")
    return key

def _get_forensic_model() -> str:
    """Garanton ekskluzivisht modelin DeepSeek pa asnjë mundësi devijimi."""
    model = getattr(settings, "LLM_DEEP_MODEL", None) or os.getenv("LLM_DEEP_MODEL", "") or "deepseek/deepseek-chat"
    if not model or "claude" in model.lower() or "anthropic" in model.lower():
        model = "deepseek/deepseek-chat"
    return model

def _get_provider_routing_payload(model_name: str) -> Dict[str, Any]:
    """
    Rrugëzon DeepSeek VETËM te ofruesit me kapacitet të lartë (64k-128k)
    dhe PËRJASHTON DeepInfra sepse ka tavan të vogël 32k.
    """
    if "deepseek" in model_name.lower():
        return {
            "provider": {
                "order": ["DeepSeek", "Fireworks", "Nebius", "Together"],
                "ignore": ["DeepInfra"],
                "allow_fallbacks": True
            }
        }
    return {}

def _get_sync_client() -> OpenAI:
    return OpenAI(
        api_key=_get_openrouter_key(),
        base_url=OPENROUTER_URL,
        timeout=300.0,
        default_headers={
            "HTTP-Referer": "https://juristi.tech",
            "X-Title": "Juristi AI - Forensic High-Precision Engine"
        }
    )

def _get_async_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=_get_openrouter_key(),
        base_url=OPENROUTER_URL,
        timeout=300.0,
        default_headers={
            "HTTP-Referer": "https://juristi.tech",
            "X-Title": "Juristi AI - Forensic High-Precision Engine"
        }
    )

def call_forensic_llm(
    system_prompt: str,
    user_content: str,
    json_mode: bool = False,
    temperature: float = 0.0,
    max_tokens: int = 8192
) -> str:
    """Thirrje sinkrone e optimizuar për DeepSeek."""
    client = _get_sync_client()
    target_model = _get_forensic_model()
    full_system = f"{FORENSIC_SYSTEM_IDENTITY}\n\n{system_prompt}"
    
    kwargs: Dict[str, Any] = {
        "model": target_model,
        "messages": [
            {"role": "system", "content": full_system},
            {"role": "user", "content": user_content}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    
    extra_body = _get_provider_routing_payload(target_model)
    if extra_body:
        kwargs["extra_body"] = extra_body

    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    retries = 3
    last_error: Optional[Exception] = None

    for attempt in range(retries):
        try:
            logger.info(f"⚖️ [Forensic LLM] Ekzekutim në {target_model} (Përpjekja {attempt + 1})...")
            res = client.chat.completions.create(**kwargs)
            if res and res.choices and len(res.choices) > 0:
                content = getattr(res.choices[0].message, "content", "") or ""
                if content.strip():
                    return content
        except Exception as e:
            last_error = e
            logger.warning(f"⚠️ [Forensic LLM Retry {attempt + 1}] {e}")
            if attempt < retries - 1:
                time.sleep(2.0 * (attempt + 1))
                continue

    raise ForensicLLMError(f"Motori Forenzik ({target_model}) dështoi: {last_error}")

def call_forensic_llm_chat(
    conversation_turns: List[Dict[str, str]],
    system_prompt: str = "",
    temperature: float = 0.0,
    max_tokens: int = 8192
) -> str:
    """Thirrje me kujtesë multi-turn e optimizuar për DeepSeek."""
    client = _get_sync_client()
    target_model = _get_forensic_model()
    full_system = f"{FORENSIC_SYSTEM_IDENTITY}\n\n{system_prompt}"

    formatted_messages: List[Dict[str, str]] = [
        {"role": "system", "content": full_system}
    ]

    for turn in conversation_turns:
        role = turn.get("role", "user")
        standard_role = "assistant" if role in ["assistant", "ai"] else "user"
        content = turn.get("content", "").strip()
        if content:
            formatted_messages.append({"role": standard_role, "content": content})

    kwargs: Dict[str, Any] = {
        "model": target_model,
        "messages": formatted_messages,
        "temperature": temperature,
        "max_tokens": max_tokens
    }

    extra_body = _get_provider_routing_payload(target_model)
    if extra_body:
        kwargs["extra_body"] = extra_body

    retries = 3
    last_error: Optional[Exception] = None

    for attempt in range(retries):
        try:
            logger.info(f"🧠 [Forensic Memory] Dërgim i {len(formatted_messages)} mesazheve te {target_model} (Përpjekja {attempt + 1})...")
            res = client.chat.completions.create(**kwargs)
            if res and res.choices and len(res.choices) > 0:
                content = getattr(res.choices[0].message, "content", "") or ""
                if content.strip():
                    return content
        except Exception as e:
            last_error = e
            logger.warning(f"⚠️ [Forensic Memory Retry {attempt + 1}] {e}")
            if attempt < retries - 1:
                time.sleep(2.0 * (attempt + 1))
                continue

    raise ForensicLLMError(f"Motori me kujtesë ({target_model}) nuk u përgjigj: {last_error}")

async def stream_forensic_llm_async(
    system_prompt: str,
    user_content: str,
    temperature: float = 0.0,
    max_tokens: int = 8192
) -> AsyncGenerator[str, None]:
    """Transmetim asinkron për streaming (single-turn)."""
    client = _get_async_client()
    target_model = _get_forensic_model()
    full_system = f"{FORENSIC_SYSTEM_IDENTITY}\n\n{system_prompt}"

    kwargs: Dict[str, Any] = {
        "model": target_model,
        "messages": [
            {"role": "system", "content": full_system},
            {"role": "user", "content": user_content}
        ],
        "temperature": temperature,
        "stream": True,
        "max_tokens": max_tokens
    }

    extra_body = _get_provider_routing_payload(target_model)
    if extra_body:
        kwargs["extra_body"] = extra_body

    try:
        logger.info(f"⚖️ [Forensic Stream] Ekzekutim në {target_model}...")
        stream = await client.chat.completions.create(**kwargs)
        async for chunk in stream:
            if chunk.choices and len(chunk.choices) > 0 and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    except Exception as e:
        logger.error(f"❌ [Forensic LLM Stream] Gabim: {e}")
        yield f"\n\n[GABIM: Lidhja me {target_model} u ndërpre: {str(e)}]"

async def stream_forensic_llm_chat_async(
    conversation_turns: List[Dict[str, str]],
    system_prompt: str = "",
    temperature: float = 0.0,
    max_tokens: int = 8192
) -> AsyncGenerator[str, None]:
    """Transmetim asinkron me kujtesë të plotë multi-turn përmes DeepSeek."""
    client = _get_async_client()
    target_model = _get_forensic_model()
    full_system = f"{FORENSIC_SYSTEM_IDENTITY}\n\n{system_prompt}"

    formatted_messages: List[Dict[str, str]] = [
        {"role": "system", "content": full_system}
    ]
    for turn in conversation_turns:
        role = turn.get("role", "user")
        standard_role = "assistant" if role in ["assistant", "ai"] else "user"
        content = turn.get("content", "").strip()
        if content:
            formatted_messages.append({"role": standard_role, "content": content})

    kwargs: Dict[str, Any] = {
        "model": target_model,
        "messages": formatted_messages,
        "temperature": temperature,
        "stream": True,
        "max_tokens": max_tokens
    }

    extra_body = _get_provider_routing_payload(target_model)
    if extra_body:
        kwargs["extra_body"] = extra_body

    try:
        logger.info(f"🧠 [Forensic Stream Chat] Transmetim te {target_model}...")
        stream = await client.chat.completions.create(**kwargs)
        async for chunk in stream:
            if chunk.choices and len(chunk.choices) > 0 and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    except Exception as e:
        logger.error(f"❌ [Forensic LLM Stream Chat] Gabim: {e}")
        yield f"\n\n[GABIM: Lidhja me {target_model} u ndërpre: {str(e)}]"