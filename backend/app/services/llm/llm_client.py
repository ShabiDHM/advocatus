# FILE: backend/app/services/llm/llm_client.py
# PHOENIX PROTOCOL - UNIFIED DUAL-ENGINE LLM CLIENT V88.7
# V88.7: DOUBLE REDACTION FIX —
#        - `_apply_pii_redaction`: system_prompt tani përdor VETËM regex
#          (redact_names=False), jo NER. System prompt është template statik
#          me zero PII → NER ishte kosto e panevojshme LLM (~50% reduktim).
#        - User content ruan full redaction (regex + NER).
#        - Përputhet me strategjinë e response_generator V98.6.
# V88.6: PII REDACTION (GDPR) — INTEGRIM text_sterilization_service
#        - `_call_llm`, `_call_llm_async`, `stream_text_async` aplikojnë
#          `sterilize_text_for_llm` PARA dërgimit te OpenRouter.
#        - Parametër i ri `redact_pii: bool = True` për opt-out (NER).
# V88.5: CONDITIONAL REASONING FLAG —
#        - `reasoning: {enabled: false}` aplikohet vetëm për modelet që e
#          mbështesin (deepseek, glm, kimi, o1/o3, qwq, etc.).

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
from app.services.text_sterilization_service import sterilize_text_for_llm

load_dotenv()
logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1"
EMBEDDING_MODEL = "openai/text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536

# ═══════════════════════════════════════════════════════════════════════════
# MODEL STRATEGY (V88.5 — Hybrid)
# ═══════════════════════════════════════════════════════════════════════════
FAST_SEARCH_MODEL = "openai/gpt-4o-mini"
DEEP_ANALYSIS_MODEL = "deepseek/deepseek-v4-flash-0731"

TEMP_ANALYSIS = 0.0
TEMP_DRAFTING = 0.0
TEMP_CHAT = 0.05

DEFAULT_MAX_TOKENS = 8192

# V88.6: Default i redaktimit të PII. NER service kalon `redact_pii=False`.
DEFAULT_REDACT_PII = True

OPENROUTER_HEADERS = {
    "HTTP-Referer": "https://juristi.tech",
    "X-Title": "Juristi AI - Kosova Legal Tech Orchestrator"
}

# ═══════════════════════════════════════════════════════════════════════════
# V88.5: REASONING MODEL DETECTION
# ═══════════════════════════════════════════════════════════════════════════
_REASONING_MODEL_PREFIXES = (
    "deepseek/",
    "deepseek-ai/",
    "z-ai/",
    "zhipuai/",
    "glm-",
    "moonshotai/",
    "kimi-",
    "openai/o1",
    "openai/o3",
    "openai/o4",
    "qwen/qwq",
    "qwen/qwen-3-max",
)


def _model_supports_reasoning_flag(model: str) -> bool:
    """V88.5: True nëse modeli mbështet parametrin `reasoning`."""
    if not model:
        return False
    m = model.lower()
    return any(m.startswith(p) for p in _REASONING_MODEL_PREFIXES)


def _get_api_key() -> str:
    return (
        getattr(settings, "OPENROUTER_API_KEY", None)
        or os.getenv("OPENROUTER_API_KEY", "")
        or os.getenv("OPENAI_API_KEY", "")
    )


def _get_target_model() -> str:
    """V88.3: Lexon modelin e parazgjedhur global (DeepSeek V4 Flash 0731)."""
    model = (
        getattr(settings, "LLM_MODEL", None)
        or os.getenv("LLM_MODEL", "")
        or "deepseek/deepseek-v4-flash-0731"
    )
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


def _get_provider_routing_payload(model: Optional[str] = None) -> Dict[str, Any]:
    """
    V88.5: `reasoning: {enabled: false}` VETËM për modelet që e mbështesin.
    """
    payload: Dict[str, Any] = {
        "provider": {
            "allow_fallbacks": True
        }
    }

    effective_model = model or _get_target_model()
    if _model_supports_reasoning_flag(effective_model):
        payload["reasoning"] = {"enabled": False}

    return payload


def _apply_hallucination_filter(text: str) -> str:
    try:
        from app.services.pillars.hallucination_filter import HallucinationFilter
        return HallucinationFilter.filter_precedents(text)
    except Exception:
        return text


def _apply_pii_redaction(system_prompt: str, user_content: str) -> tuple:
    """
    V88.7: Redaktim PII selektiv për të shmangur DOUBLE REDACTION.

    Strategji:
    - system_prompt → regex-only (redact_names=False). Është template statik
      me zero PII; NER do ishte kosto e panevojshme LLM.
    - user_content → full (regex + NER). Ky është teksti real i përdoruesit.

    Kthim: (system_prompt_redaktuar, user_content_redaktuar)
    Fail-safe: në exception, kthen input-et e paprekura.
    """
    try:
        redacted_sys = sterilize_text_for_llm(system_prompt, redact_names=False)
        redacted_user = sterilize_text_for_llm(user_content, redact_names=True)

        orig_len = len(system_prompt) + len(user_content)
        new_len = len(redacted_sys) + len(redacted_user)
        if new_len != orig_len:
            logger.info(
                f"🔒 [PII Redaction V88.7] U aplikua: "
                f"{orig_len} → {new_len} chars "
                f"(sys: regex-only, user: full)"
            )
        return redacted_sys, redacted_user
    except Exception as e:
        logger.error(f"❌ [PII Redaction V88.7] Dështoi — dërgim pa redaktim: {e}")
        return system_prompt, user_content


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
    model: Optional[str] = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    redact_pii: bool = DEFAULT_REDACT_PII,
) -> str:
    key = _get_api_key()
    if not key:
        return ""

    full_sys_prompt = _prepare_system_prompt(system_prompt)
    sanitized_user_content = _sanitize_and_disambiguate_prompt(user_content)

    # V88.7: PII REDACTION — hapi i fundit para dërgimit
    if redact_pii:
        full_sys_prompt, sanitized_user_content = _apply_pii_redaction(
            full_sys_prompt, sanitized_user_content
        )

    client = _get_sync_client()
    target_model = model if model else _get_target_model()

    kwargs: Dict[str, Any] = {
        "model": target_model,
        "messages": [
            {"role": "system", "content": full_sys_prompt},
            {"role": "user", "content": sanitized_user_content}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "extra_body": _get_provider_routing_payload(target_model)
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
                logger.warning(f"⚠️ [Rate Limit 429] në {target_model}. Po pres {2 * attempt}s...")
                time.sleep(2.0 * attempt)
                continue
            logger.warning(f"⚠️ Përpjekja {attempt} në {target_model} dështoi: {e}")
            time.sleep(1.5)

    return ""


async def _call_llm_async(
    system_prompt: str,
    user_content: str,
    json_mode: bool = False,
    temperature: float = TEMP_ANALYSIS,
    model: Optional[str] = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    redact_pii: bool = DEFAULT_REDACT_PII,
) -> str:
    key = _get_api_key()
    if not key:
        return ""

    full_sys_prompt = _prepare_system_prompt(system_prompt)
    sanitized_user_content = _sanitize_and_disambiguate_prompt(user_content)

    # V88.7: PII REDACTION — hapi i fundit para dërgimit
    if redact_pii:
        full_sys_prompt, sanitized_user_content = _apply_pii_redaction(
            full_sys_prompt, sanitized_user_content
        )

    client = _get_async_client()
    target_model = model if model else _get_target_model()

    kwargs: Dict[str, Any] = {
        "model": target_model,
        "messages": [
            {"role": "system", "content": full_sys_prompt},
            {"role": "user", "content": sanitized_user_content}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "extra_body": _get_provider_routing_payload(target_model)
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
                logger.warning(f"⚠️ [Rate Limit 429] në {target_model} async. Po pres {2 * attempt}s...")
                await asyncio.sleep(2.0 * attempt)
                continue
            logger.warning(f"⚠️ Përpjekja {attempt} në {target_model} dështoi: {e}")
            await asyncio.sleep(1.5)

    return ""


def get_embedding(text: str) -> List[float]:
    """
    V88.2: Kthen [] në dështim (jo [0.0]*1536).

    V88.6 NOTE: Nuk aplikohet redaktim PII këtu (embedding nuk ekspozon tekst).
    """
    key = _get_api_key()
    if not text or not key:
        return []
    try:
        client = _get_sync_client()
        res = client.embeddings.create(input=[text.replace("\n", " ")], model=EMBEDDING_MODEL)
        vec = res.data[0].embedding if res.data else None
        if vec:
            return vec
        logger.warning("⚠️ [Embedding] Përgjigjja pa vector — kthim []")
        return []
    except Exception as e:
        logger.warning(f"⚠️ [Embedding] Dështoi — kthim []: {e}")
        return []


def get_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """
    V88.2: Kthen [[] for _ in texts] në dështim total.

    V88.6 NOTE: Nuk aplikohet redaktim PII këtu (embedding nuk ekspozon tekst).
    """
    key = _get_api_key()
    if not texts:
        return []
    if not key:
        return [[] for _ in texts]
    try:
        clean_inputs = [t.replace("\n", " ").strip() or " " for t in texts]
        client = _get_sync_client()
        res = client.embeddings.create(input=clean_inputs, model=EMBEDDING_MODEL)
        if res and res.data and len(res.data) == len(texts):
            return [item.embedding if item.embedding else [] for item in res.data]
        logger.warning(
            f"⚠️ [Batch Embedding] Përgjigjje me {len(res.data) if res and res.data else 0} "
            f"elemente për {len(texts)} input — kthim [[] ...]"
        )
        return [[] for _ in texts]
    except Exception as e:
        logger.warning(f"⚠️ [Batch Embedding] Dështoi — kthim [[] ...]: {e}")
        return [[] for _ in texts]


async def stream_text_async(
    sys_p: str,
    user_p: str,
    temp: float = TEMP_CHAT,
    model: Optional[str] = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    redact_pii: bool = DEFAULT_REDACT_PII,
) -> AsyncGenerator[str, None]:
    """
    V88.7: PII redaction selektive. NER service duhet të kalojë
    `redact_pii=False` (shih NER V33.7).
    """
    client = _get_async_client()
    full_sys = _prepare_system_prompt(sys_p)
    sanitized_user_p = _sanitize_and_disambiguate_prompt(user_p)

    # V88.7: PII REDACTION — hapi i fundit para dërgimit
    if redact_pii:
        full_sys, sanitized_user_p = _apply_pii_redaction(full_sys, sanitized_user_p)

    target_model = model if model else _get_target_model()

    kwargs: Dict[str, Any] = {
        "model": target_model,
        "messages": [
            {"role": "system", "content": full_sys},
            {"role": "user", "content": sanitized_user_p}
        ],
        "temperature": temp,
        "stream": True,
        "max_tokens": max_tokens,
        "extra_body": _get_provider_routing_payload(target_model)
    }

    for attempt in range(1, 4):
        stream_started = False

        try:
            stream = await client.chat.completions.create(**kwargs)
            async for chunk in stream:
                if chunk.choices and len(chunk.choices) > 0 and chunk.choices[0].delta.content:
                    stream_started = True
                    yield chunk.choices[0].delta.content

            yield AI_DISCLAIMER
            return
        except Exception as e:
            err_msg = str(e).lower()

            if stream_started:
                logger.error(
                    f"❌ [stream_text_async V88.7] Gabim MES stream-it në "
                    f"{target_model} — retry nuk bëhet (shmang dublimin): {e}"
                )
                yield f"\n\n[Gabim i rrjetit mes përgjigjes. Ju lutem rifreskoni faqen dhe provoni përsëri.]"
                return

            if "429" in err_msg or "rate limit" in err_msg:
                logger.warning(f"⚠️ [Rate Limit 429] në {target_model} stream. Po pres {2 * attempt}s...")
                await asyncio.sleep(2.0 * attempt)
                continue
            await asyncio.sleep(1.5)

    yield f"\n\n[Shërbimi {target_model} është përkohësisht i ngarkuar. Ju lutem provoni përsëri pas pak sekondash.]"