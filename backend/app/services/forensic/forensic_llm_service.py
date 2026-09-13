# FILE: backend/app/services/forensic/forensic_llm_service.py
# PHOENIX PROTOCOL - FORENSIC DEDICATED LLM ENGINE V8.0 (CLEAN DEEPSEEK ROUTING • ZERO 404s)
# 100% COMPLETE CODE • EXCLUSIVE DEEPSEEK CORE • UNRESTRICTED PROVIDER POOL • 429 AUTO-RETRY

import os
import time
import asyncio
import logging
from typing import Dict, Any, List, AsyncGenerator, Optional
from openai import OpenAI, AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1"

# Modeli i Vetëm dhe Ekskluziv i Padiskutueshëm
EXCLUSIVE_DEEPSEEK_MODEL = "deepseek/deepseek-chat"

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
    """Rikthen modelin e konfiguruar nga .env (LLM_MODEL) ose DeepSeek parazgjedhur."""
    model = (
        getattr(settings, "LLM_MODEL", None) or 
        getattr(settings, "LLM_DEEP_MODEL", None) or 
        os.getenv("LLM_MODEL", "") or 
        os.getenv("LLM_DEEP_MODEL", "") or 
        EXCLUSIVE_DEEPSEEK_MODEL
    )
    if "claude" in model.lower() or "anthropic" in model.lower():
        model = EXCLUSIVE_DEEPSEEK_MODEL
    return model

def _get_provider_routing_payload() -> Dict[str, Any]:
    """Lejon të gjithë ofruesit zyrtarë të DeepSeek me balancim automatik të ngarkesës."""
    return {
        "provider": {
            "allow_fallbacks": True
        }
    }

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
        "max_tokens": max_tokens,
        "extra_body": _get_provider_routing_payload()
    }
    
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    last_error: Optional[Exception] = None

    for attempt in range(1, 4):
        try:
            logger.info(f"⚖️ [Forensic LLM] Ekzekutim në {target_model} (Përpjekja {attempt})...")
            res = client.chat.completions.create(**kwargs)
            if res and res.choices and len(res.choices) > 0:
                content = getattr(res.choices[0].message, "content", "") or ""
                if content.strip():
                    return content
        except Exception as e:
            last_error = e
            err_str = str(e).lower()
            if "429" in err_str or "rate limit" in err_str:
                logger.warning(f"⚠️ [Rate Limit 429] në DeepSeek. Po pres {2 * attempt}s...")
                time.sleep(2.0 * attempt)
                continue
            logger.warning(f"⚠️ Dështoi përpjekja {attempt} në DeepSeek: {e}")
            time.sleep(1.5)

    raise ForensicLLMError(f"Shërbimi DeepSeek është përkohësisht i ngarkuar. Provoni përsëri pas pak sekondash.")

def call_forensic_llm_chat(
    conversation_turns: List[Dict[str, str]],
    system_prompt: str = "",
    temperature: float = 0.0,
    max_tokens: int = 8192
) -> str:
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
        "max_tokens": max_tokens,
        "extra_body": _get_provider_routing_payload()
    }

    last_error: Optional[Exception] = None

    for attempt in range(1, 4):
        try:
            logger.info(f"🧠 [Forensic Memory] Dërgim në {target_model} (Përpjekja {attempt})...")
            res = client.chat.completions.create(**kwargs)
            if res and res.choices and len(res.choices) > 0:
                content = getattr(res.choices[0].message, "content", "") or ""
                if content.strip():
                    return content
        except Exception as e:
            last_error = e
            err_str = str(e).lower()
            if "429" in err_str or "rate limit" in err_str:
                logger.warning(f"⚠️ [Rate Limit 429] në DeepSeek. Po pres {2 * attempt}s...")
                time.sleep(2.0 * attempt)
                continue
            time.sleep(1.5)

    raise ForensicLLMError(f"Shërbimi DeepSeek është përkohësisht i ngarkuar. Provoni përsëri pas pak sekondash.")

async def stream_forensic_llm_async(
    system_prompt: str,
    user_content: str,
    temperature: float = 0.0,
    max_tokens: int = 8192
) -> AsyncGenerator[str, None]:
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
        "max_tokens": max_tokens,
        "extra_body": _get_provider_routing_payload()
    }

    last_error: Optional[Exception] = None

    for attempt in range(1, 4):
        try:
            logger.info(f"⚖️ [Forensic Stream] Ekzekutim në {target_model} (Përpjekja {attempt})...")
            stream = await client.chat.completions.create(**kwargs)
            async for chunk in stream:
                if chunk.choices and len(chunk.choices) > 0 and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
            return
        except Exception as e:
            last_error = e
            err_str = str(e).lower()
            if "429" in err_str or "rate limit" in err_str:
                logger.warning(f"⚠️ [Rate Limit 429] në DeepSeek. Po pres {2 * attempt}s...")
                await asyncio.sleep(2.0 * attempt)
                continue
            await asyncio.sleep(1.5)

    logger.error(f"❌ [Forensic Stream Error]: {last_error}")
    yield f"\n\n[Shërbimi DeepSeek është përkohësisht i ngarkuar nga fluksi i lartë. Ju lutem provoni përsëri pas pak sekondash.]"

async def stream_forensic_llm_chat_async(
    conversation_turns: List[Dict[str, str]],
    system_prompt: str = "",
    temperature: float = 0.0,
    max_tokens: int = 8192
) -> AsyncGenerator[str, None]:
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
        "max_tokens": max_tokens,
        "extra_body": _get_provider_routing_payload()
    }

    last_error: Optional[Exception] = None

    for attempt in range(1, 4):
        try:
            logger.info(f"🧠 [Forensic Stream Chat] Ekzekutim në {target_model} (Përpjekja {attempt})...")
            stream = await client.chat.completions.create(**kwargs)
            async for chunk in stream:
                if chunk.choices and len(chunk.choices) > 0 and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
            return
        except Exception as e:
            last_error = e
            err_str = str(e).lower()
            if "429" in err_str or "rate limit" in err_str:
                logger.warning(f"⚠️ [Rate Limit 429] në DeepSeek. Po pres {2 * attempt}s për çlirim...")
                await asyncio.sleep(2.0 * attempt)
                continue
            await asyncio.sleep(1.5)

    logger.error(f"❌ [Forensic Stream Failure]: {last_error}")
    yield f"\n\n[Shërbimi DeepSeek është përkohësisht i ngarkuar nga fluksi i lartë. Ju lutem provoni përsëri pas pak sekondash.]"