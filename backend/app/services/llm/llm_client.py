# FILE: backend/app/services/llm/llm_client.py
# PHOENIX PROTOCOL - UNIFIED DUAL-ENGINE LLM CLIENT V88.4
# V88.4: REASONING DISABLED — Shtuar `reasoning: {enabled: false}` në
#        _get_provider_routing_payload(). Modeli DeepSeek V4 Flash 0731
#        është reasoning model: harxhon max_tokens në "mendim të brendshëm"
#        përpara se të nxjerrë përgjigjen, duke shkaktuar 0 chars output në
#        seksionet me max_tokens të vogël. Çaktivizimi i reasoning i jep
#        modelit të gjithë budget-in për përgjigjen reale.
#        Konfirmuar nga OpenRouter: filtri "Reasoning effort" + Activity
#        tregon 9.6B reasoning tokens aktualisht.
# V88.3: MODEL MIGRATION — DEEP_ANALYSIS_MODEL dhe fallback ndryshuar nga
#        "deepseek/deepseek-chat" (deprecated) në
#        "deepseek/deepseek-v4-flash-0731" (Together AI, BYOK).
# V88.2: EMBEDDING FAILURE HARDENING — get_embedding / get_embeddings_batch
#        kthejnë [] (listë bosh) në dështim, jo [0.0]*1536 (vector zero).
# V88.1: STREAM RETRY FIX — stream_text_async nuk retry pas yield-imit.
# V88.0: CLAUDE OVERRIDE REMOVED + MAX_TOKENS PARAMETRIZED.
# V87.0: Shtuar DEEP_ANALYSIS_MODEL për analiza të thella.
# V86.0: Hequr konstantja e vdekur TEMP_FORENSIC.

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
EMBEDDING_DIMENSIONS = 1536   # V88.2: konstantë referimi (dokumentim)

# ═══════════════════════════════════════════════════════════════════════════
# MODEL STRATEGY (V88.4 — Hybrid)
# ═══════════════════════════════════════════════════════════════════════════
# FAST_SEARCH_MODEL    → Detyra mekanike: NER, Metadata, Law Search
# DEEP_ANALYSIS_MODEL  → Analiza të thella: Synthesis, Document Review
# ═══════════════════════════════════════════════════════════════════════════
FAST_SEARCH_MODEL = "openai/gpt-4o-mini"
DEEP_ANALYSIS_MODEL = "deepseek/deepseek-v4-flash-0731"

TEMP_ANALYSIS = 0.0
TEMP_DRAFTING = 0.0
TEMP_CHAT = 0.05

DEFAULT_MAX_TOKENS = 8192

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
    """
    V88.3: Lexon modelin e parazgjedhur global (DeepSeek V4 Flash 0731).

    Heq override-in silent "claude" → "deepseek". Claude nuk përdoret më;
    model-i i ENV respektohet verbatim.
    """
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


def _get_provider_routing_payload() -> Dict[str, Any]:
    """
    V88.4: Shtuar `reasoning: {enabled: false}`.

    Pse: DeepSeek V4 Flash 0731 është reasoning model. Pa këtë parametër,
    harxhon max_tokens në "mendim të brendshëm" dhe nxjerr 0 chars për
    seksionet e vogla (max_tokens < 4000). Çaktivizimi i reasoning i jep
    modelit të gjithë budget-in për përgjigjen reale.

    Përputhshmëri:
    - OpenRouter e injoron automatikisht për modelet që nuk e mbështesin
      (gpt-4o-mini, etj.).
    - Në modelet reasoning (DeepSeek V4, V3.1+, GLM 5+, Kimi K3), çaktivizohet
      mendimi i brendshëm → përgjigje direkte.
    """
    return {
        "provider": {
            "allow_fallbacks": True
        },
        "reasoning": {
            "enabled": False
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
    model: Optional[str] = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> str:
    key = _get_api_key()
    if not key:
        return ""

    full_sys_prompt = _prepare_system_prompt(system_prompt)
    sanitized_user_content = _sanitize_and_disambiguate_prompt(user_content)
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
) -> str:
    key = _get_api_key()
    if not key:
        return ""

    full_sys_prompt = _prepare_system_prompt(system_prompt)
    sanitized_user_content = _sanitize_and_disambiguate_prompt(user_content)
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
                logger.warning(f"⚠️ [Rate Limit 429] në {target_model} async. Po pres {2 * attempt}s...")
                await asyncio.sleep(2.0 * attempt)
                continue
            logger.warning(f"⚠️ Përpjekja {attempt} në {target_model} dështoi: {e}")
            await asyncio.sleep(1.5)

    return ""


def get_embedding(text: str) -> List[float]:
    """
    V88.2: Kthen [] në dështim (jo [0.0]*1536).

    Vector zero shkaktonte kërkime me cosine undefined → rezultate të
    rastësishme/bosh në Atlas Vector Search. [] kalon `if not query_vector`
    te konsumatorët dhe shmang kërkime të pavlefshme.
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
    V88.2: Kthen [[] for _ in texts] në dështim total (jo retry një-nga-një
    me fallback zero).

    Konsumatorët mund të kontrollojnë `if not vec` për çdo element.
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
) -> AsyncGenerator[str, None]:
    """
    V88.4: Reasoning disabled (trashëguar nga _get_provider_routing_payload).
    V88.1: Streaming me retry të sigurt.
    """
    client = _get_async_client()
    full_sys = _prepare_system_prompt(sys_p)
    sanitized_user_p = _sanitize_and_disambiguate_prompt(user_p)
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
        "extra_body": _get_provider_routing_payload()
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
                    f"❌ [stream_text_async V88.4] Gabim MES stream-it në "
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