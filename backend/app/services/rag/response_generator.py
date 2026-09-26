# FILE: backend/app/services/rag/response_generator.py
# PHOENIX PROTOCOL - UNIFIED SUPREME RESPONSE GENERATOR V98.1
# V98.1: CLAUDE OVERRIDE REMOVED — Hequr override-i silent "claude"→"deepseek"
#        në _get_target_model() (i njëjti fix si llm_client.py V88.0).
#        Claude nuk përdoret më; model-i i ENV respektohet verbatim.
# V98.0: Shtuar parametër opsional `model` në generate_stream/_call_with_retry.
#        Chat-i i klientit kalon FAST_SEARCH_MODEL (gpt-4o-mini).
#        Law Audit vazhdon me default (DEEP_ANALYSIS_MODEL - deepseek).

import logging
import asyncio
import os
import re
from typing import Optional, List, Dict, Any, AsyncGenerator
from openai import AsyncOpenAI
from app.core.config import settings

from app.services.llm.llm_client import (
    _get_api_key,
    _get_async_client
)

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

LLM_TIMEOUT = 300
MAX_RETRIES = 3
MAX_SINGLE_PASS_CHARS = 1_500_000

OPENROUTER_HEADERS = {
    "HTTP-Referer": "https://juristi.tech",
    "X-Title": "Juristi AI - Kosova Legal Tech Orchestrator"
}


def _get_target_model() -> str:
    """
    V98.1: Lexon VETËM modelin e vetëm të unifikuar nga settings.LLM_MODEL.

    Përdoret si fallback kur generate_stream nuk jep model eksplicit.
    Model-i i ENV respektohet verbatim — asnjë override silent.
    """
    model = (
        getattr(settings, "LLM_MODEL", None)
        or os.getenv("LLM_MODEL", "")
        or "deepseek/deepseek-chat"
    )
    return model


def _get_provider_routing_payload() -> Dict[str, Any]:
    """Lejon të gjithë ofruesit zyrtarë me failover automatik dhe zero bllokime 404."""
    return {
        "provider": {
            "allow_fallbacks": True
        }
    }


class ResponseGenerator:
    """
    Gjeneruesi Qendror i Përgjigjeve (V98.1):
    - Motor i vetëm me parametër opsional `model`:
        * Chat-i i klientit → FAST_SEARCH_MODEL (gpt-4o-mini)
        * Law Audit / other → default DEEP_ANALYSIS_MODEL (deepseek)
    - Mbrojtje e plotë nga mbingarkesat (429 Auto-Retry me 3 tentativa).
    """

    def __init__(self):
        self.api_key = _get_api_key()
        self.client = _get_async_client()

    async def _call_with_retry(
        self,
        messages: List[Dict[str, str]],
        stream: bool = True,
        max_tokens: int = 8192,
        model: Optional[str] = None,
    ):
        last_error = None
        target_model = model if model else _get_target_model()

        kwargs: Dict[str, Any] = {
            "model": target_model,
            "messages": messages,
            "temperature": 0.0,
            "stream": stream,
            "max_tokens": max_tokens,
            "extra_body": _get_provider_routing_payload()
        }

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"⚖️ [ResponseGenerator] Ekzekutim në {target_model} (Përpjekja {attempt})...")
                response = await self.client.chat.completions.create(**kwargs)
                return response
            except Exception as e:
                last_error = e
                err_str = str(e).lower()
                if "429" in err_str or "rate limit" in err_str:
                    logger.warning(f"⚠️ [Rate Limit 429] në {target_model}. Po pres {2 * attempt}s...")
                    await asyncio.sleep(2.0 * attempt)
                    continue
                logger.warning(f"⚠️ Dështoi përpjekja {attempt} në {target_model}: {e}")
                await asyncio.sleep(1.5)

        raise last_error if last_error else Exception("Shërbimi është përkohësisht i ngarkuar nga fluksi.")

    async def generate_stream(
        self,
        system_prompt: str,
        user_query: str,
        context: str = "",
        history: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        model: Nëse None → përdor _get_target_model() (DeepSeek).
               Nëse jepet → përdor atë model (p.sh. FAST_SEARCH_MODEL për chat).
        """
        try:
            full_context_content = f"{context}\n\n{system_prompt}" if context else system_prompt

            enhanced_system_prompt = f"""
{full_context_content}

RREGULLAT E KONSULENCËS DHE DOKTRINËS SË KOSOVËS:
1. Përgjigju VETËM në gjuhë standarde juridike shqipe të Republikës së Kosovës.
2. Dëgjoni me kujdes dhe bashkëpunoni natyrshëm me përdoruesin pa shabllone artificiale.
3. Bazo çdo zgjidhje në ligjet pozitive dhe shkresat reale të fashikullit.
"""
            messages = [{"role": "system", "content": enhanced_system_prompt[:MAX_SINGLE_PASS_CHARS]}]

            if history and isinstance(history, list):
                for h in history[-8:]:
                    r = "assistant" if h.get("role") in ["ai", "assistant"] else "user"
                    c = h.get("content") or h.get("text") or ""
                    if c and not c.startswith("[Gabim Teknik"):
                        messages.append({"role": r, "content": c})

            messages.append({"role": "user", "content": user_query})

            response = await self._call_with_retry(
                messages,
                stream=True,
                max_tokens=8192,
                model=model,
            )

            async for chunk in response:
                if chunk.choices and len(chunk.choices) > 0:
                    choice = chunk.choices[0]
                    if choice.delta and choice.delta.content:
                        yield choice.delta.content

        except Exception as e:
            target_model = model if model else _get_target_model()
            logger.error(f"❌ Gjenerimi dështoi pas të gjitha përpjekjeve në {target_model}: {e}")
            yield f"\n\n[Shërbimi është përkohësisht i ngarkuar nga fluksi i lartë. Ju lutem provoni përsëri pas pak sekondash.]"