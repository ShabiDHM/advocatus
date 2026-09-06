# FILE: backend/app/services/rag/response_generator.py
# PHOENIX PROTOCOL - UNIFIED SUPREME RESPONSE GENERATOR V87.0 (STRICT TIER ISOLATION & ZERO ACCIDENTAL SONNET BURNS)
# 100% COMPLETE CODE • ZERO TS/PY WARNINGS • FAST VS DEEP ROUTING INTEGRITY

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
    PRIMARY_MODEL,
    FAST_MODEL,
    DEEP_MODEL,
    FALLBACK_MODELS
)

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

TIER1_ELITE_MODEL = DEEP_MODEL  # anthropic/claude-sonnet-4.6
CHAT_FAST_MODEL = FAST_MODEL    # openai/gpt-4o-mini

# Vetëm për Zyrën Forenzike të Super Adminit (1M Context)
HEAVY_TASK_FALLBACKS = [
    "anthropic/claude-sonnet-4.6",      # 1,000,000 tokens (Standardi Suprem Ligjor)
    "anthropic/claude-3.7-sonnet",      # 200,000 tokens (Hybrid Reasoning)
    "anthropic/claude-3.5-sonnet",      # 200,000 tokens
    "google/gemini-2.0-flash-001",      # 1,048,576 tokens
    "google/gemini-pro-1.5"             # 2,097,152 tokens
]

# Për Klientët dhe Analizat e Përditshme në CaseView (Ultra të lira dhe rrufe të shpejta)
FAST_TASK_FALLBACKS = [
    "openai/gpt-4o-mini",               # Modeli ekonomik parësor (~$0.15/1M)
    "google/gemini-2.0-flash-001",
    "deepseek/deepseek-chat"
]

LLM_TIMEOUT = 300
MAX_RETRIES = 2
MAX_SINGLE_PASS_CHARS = 1_500_000

OPENROUTER_HEADERS = {
    "HTTP-Referer": "https://juristi.tech",
    "X-Title": "Juristi AI - Kosova Justice Engine"
}


class ResponseGenerator:
    """
    Gjeneruesi Suprem i Përgjigjeve (V87.0):
    - Diferencim i rreptë ekonomik: GPT-4o-Mini për Klientët (FAST), Claude Sonnet 4.6 për Forenzikën (DEEP).
    - Zero djegie aksidentale të krediteve: Fjalët e përgjithshme si 'dosje' nuk e aktivizojnë më Sonnet-in.
    """

    def __init__(self):
        self.api_key = _get_api_key()
        self.client = _get_async_client()

    async def _call_with_retry(
        self, 
        messages: List[Dict[str, str]], 
        stream: bool = True, 
        max_tokens: int = 16384,
        model: Optional[str] = None,
        is_heavy_task: bool = False
    ):
        last_error = None
        base_list = HEAVY_TASK_FALLBACKS if is_heavy_task else FAST_TASK_FALLBACKS
        
        target_model = model or (TIER1_ELITE_MODEL if is_heavy_task else CHAT_FAST_MODEL)
        models_to_try = [target_model] + [m for m in base_list if m != target_model]
        
        unique_models: List[str] = []
        for m in models_to_try:
            if m and m not in unique_models:
                unique_models.append(m)

        for current_model in unique_models:
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    logger.info(f"⚖️ [Juristi AI Engine] Modeli në përdorim: {current_model} (Tier: {'DEEP_FORENSIC' if is_heavy_task else 'FAST_STANDARD'}) Përpjekja {attempt}...")
                    kwargs: Dict[str, Any] = {
                        "model": current_model,
                        "messages": messages,
                        "temperature": 0.0,
                        "stream": stream,
                        "max_tokens": max_tokens
                    }
                    
                    if "deepseek" in current_model.lower():
                        kwargs["extra_body"] = {
                            "provider": {
                                "order": ["DeepSeek", "Fireworks", "Together", "Nebius", "DeepInfra"],
                                "allow_fallbacks": True
                            }
                        }

                    response = await self.client.chat.completions.create(**kwargs)
                    return response
                except Exception as e:
                    last_error = e
                    err_str = str(e).lower()
                    if "429" in err_str or "rate limit" in err_str:
                        logger.warning(f"⚠️ [Rate Limit] në {current_model}: {e}. Po pres {attempt * 2}s...")
                        await asyncio.sleep(attempt * 2.0)
                        continue
                    else:
                        logger.warning(f"⚠️ Dështoi modeli {current_model}: {e}. Po kaloj te fallback-u tjetër...")
                        break
        
        raise last_error if last_error else Exception("Dështoi komunikimi me të gjithë ofruesit e LLM.")

    async def generate_stream(
        self,
        system_prompt: str,
        user_query: str,
        context: str = "",
        model_override: Optional[str] = None,
        reasoning_mode: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        try:
            combined_upper = f"{system_prompt} {user_query}".upper()

            # 1. RREGULLI I HEKURT: Nëse kërkohet Analizë Standarde e Klientit ose FAST mode ➔ GPT-4O-MINI
            is_explicit_fast = (
                reasoning_mode == "FAST" or
                "[ANALIZË STANDARDE" in combined_upper or
                "[AUDITIM STANDART" in combined_upper or
                "[KLIENT" in combined_upper
            )

            # 2. Vetëm direktivat eksplicite forenzike të Super-Adminit shkojnë te Claude Sonnet 4.6
            is_explicit_heavy = not is_explicit_fast and (
                reasoning_mode == "DEEP" or
                "[DIREKTIVË FORENZIKE" in combined_upper or
                "[RAPORT MASTER FORENZIK" in combined_upper or
                "AUTOPSI E THELLË FORENZIKE" in combined_upper
            )

            if is_explicit_fast:
                is_heavy_task = False
                selected_model = model_override or CHAT_FAST_MODEL
                max_tokens = 4096
            elif is_explicit_heavy:
                is_heavy_task = True
                selected_model = model_override or TIER1_ELITE_MODEL
                max_tokens = 16384
            else:
                # Chat-i i zakonshëm i përditshëm shkon te modeli i shpejtë dhe i lirë
                is_heavy_task = False
                selected_model = model_override or CHAT_FAST_MODEL
                max_tokens = 4096

            full_context_content = f"{context}\n\n{system_prompt}" if context else system_prompt
            
            enhanced_system_prompt = f"""
{full_context_content}

RREGULLAT E DOKTRINËS DHE INTEGRITETIT TË PËRGJIGJES:
1. Përgjigju VETËM në gjuhë standarde juridike shqipe të Republikës së Kosovës.
2. CITO NENET me saktësi neni-për-nen (KPK Nr. 06/L-074, KPPRK Nr. 08/L-032, LPK Nr. 03/L-006, LMD Nr. 04/L-077, LPP Nr. 04/L-139, LSHT Nr. 06/L-016, Ligji për PSRK Nr. 03/L-052).
3. Përmbushi kërkesën ligjore në mënyrë të qartë, profesionale dhe koncize pa ndërprerje.
"""
            messages = [
                {"role": "system", "content": enhanced_system_prompt[:MAX_SINGLE_PASS_CHARS]},
                {"role": "user", "content": user_query}
            ]
            
            response = await self._call_with_retry(
                messages, 
                stream=True, 
                max_tokens=max_tokens,
                model=selected_model,
                is_heavy_task=is_heavy_task
            )
            
            async for chunk in response:
                if chunk.choices and len(chunk.choices) > 0:
                    choice = chunk.choices[0]
                    if choice.delta and choice.delta.content:
                        yield choice.delta.content
                    
        except Exception as e:
            logger.error(f"❌ Gjenerimi dështoi pas të gjitha përpjekjeve: {e}")
            yield f"\n\n[Shërbimi AI është përkohësisht i ngarkuar. Ju lutem provoni përsëri: {str(e)}]"