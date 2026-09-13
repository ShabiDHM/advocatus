# FILE: backend/app/services/rag/response_generator.py
# PHOENIX PROTOCOL - UNIFIED SUPREME RESPONSE GENERATOR V95.0 (EXCLUSIVE GLOBAL DEEPSEEK • ZERO FALLBACKS)
# 100% COMPLETE CODE • ZERO MODEL SWITCHING • PURE DEEPSEEK DOCTRINAL REASONING • 429 AUTO-RETRY

import logging
import asyncio
import os
import re
from typing import Optional, List, Dict, Any, AsyncGenerator
from openai import AsyncOpenAI
from app.core.config import settings

from app.services.llm.llm_client import (
    _get_api_key,
    _get_async_client,
    DEEP_MODEL
)

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# 🏛️ MODELI THEMELOR DHE I VETËM GLOBAL (EKSKLUZIVISHT DEEPSEEK)
EXCLUSIVE_DEEPSEEK_MODEL = "deepseek/deepseek-chat"

LLM_TIMEOUT = 300
MAX_RETRIES = 3
MAX_SINGLE_PASS_CHARS = 1_500_000

OPENROUTER_HEADERS = {
    "HTTP-Referer": "https://juristi.tech",
    "X-Title": "Juristi AI - Kosova Legal Tech Orchestrator"
}


def _get_provider_routing_payload() -> Dict[str, Any]:
    """Rrugëzon ekskluzivisht te nyjet më të forta të DeepSeek dhe bllokon ato me limite artificiale."""
    return {
        "provider": {
            "order": ["DeepSeek", "Fireworks", "Nebius", "Together"],
            "ignore": ["StreamLake", "DeepInfra"],
            "allow_fallbacks": True
        }
    }


class ResponseGenerator:
    """
    Gjeneruesi Qendror i Përgjigjeve (V95.0):
    - Motor Ekskluziv: DeepSeek (deepseek/deepseek-chat) për të gjithë sistemin.
    - Zero Fallback te modele të tjera (Zero Gemini, Zero Claude, Zero GPT-4o-mini).
    - Multi-provider failover vetëm brenda nyjeve të forta të DeepSeek.
    - Mbrojtje automatike nga mbingarkesat (429 Auto-Retry).
    """

    def __init__(self):
        self.api_key = _get_api_key()
        self.client = _get_async_client()

    async def _call_with_retry(
        self, 
        messages: List[Dict[str, str]], 
        stream: bool = True, 
        max_tokens: int = 8192
    ):
        last_error = None

        kwargs: Dict[str, Any] = {
            "model": EXCLUSIVE_DEEPSEEK_MODEL,
            "messages": messages,
            "temperature": 0.0,
            "stream": stream,
            "max_tokens": max_tokens,
            "extra_body": _get_provider_routing_payload()
        }

        # Riprovon deri në 3 herë me nyjet e forta të DeepSeek (me pauzë 2s nëse ka 429)
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"⚖️ [Juristi AI Engine] Ekzekutim në DeepSeek (Përpjekja {attempt}, MaxTokens: {max_tokens})...")
                response = await self.client.chat.completions.create(**kwargs)
                return response
            except Exception as e:
                last_error = e
                err_str = str(e).lower()
                if "429" in err_str or "rate limit" in err_str:
                    logger.warning(f"⚠️ [Rate Limit 429] në DeepSeek. Po pres {2 * attempt}s për çlirim të nyjes...")
                    await asyncio.sleep(2.0 * attempt)
                    continue
                logger.warning(f"⚠️ Dështoi përpjekja {attempt} në DeepSeek: {e}")
                await asyncio.sleep(1.5)
        
        raise last_error if last_error else Exception("Shërbimi DeepSeek është përkohësisht i ngarkuar nga fluksi.")

    async def generate_stream(
        self,
        system_prompt: str,
        user_query: str,
        context: str = "",
        model_override: Optional[str] = None,
        reasoning_mode: Optional[str] = None,
        history: Optional[List[Dict[str, Any]]] = None
    ) -> AsyncGenerator[str, None]:
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
                max_tokens=8192
            )
            
            async for chunk in response:
                if chunk.choices and len(chunk.choices) > 0:
                    choice = chunk.choices[0]
                    if choice.delta and choice.delta.content:
                        yield choice.delta.content
                    
        except Exception as e:
            logger.error(f"❌ Gjenerimi dështoi pas të gjitha përpjekjeve në DeepSeek: {e}")
            yield f"\n\n[Shërbimi DeepSeek është përkohësisht i ngarkuar nga fluksi i lartë. Ju lutem provoni përsëri pas pak sekondash.]"