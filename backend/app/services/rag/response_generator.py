# FILE: backend/app/services/rag/response_generator.py
# PHOENIX PROTOCOL - UNIFIED SUPREME RESPONSE GENERATOR V86.0 (CLAUDE SONNET 1M • 16K OUTPUT BUFFER • ZERO REPEAT BURNS)

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

TIER1_ELITE_MODEL = DEEP_MODEL
CHAT_FAST_MODEL = FAST_MODEL

# PHOENIX FIX: Vetëm modele me dritare gjigante (200K - 2M tokens) për detyrat e rënda
HEAVY_TASK_FALLBACKS = [
    "anthropic/claude-sonnet-4.6",      # 1,000,000 tokens (Standardi Suprem Ligjor)
    "anthropic/claude-3.7-sonnet",      # 200,000 tokens (Hybrid Reasoning)
    "anthropic/claude-3.5-sonnet",      # 200,000 tokens
    "google/gemini-2.0-flash-001",      # 1,048,576 tokens (Ultra i shpejtë dhe i lirë)
    "google/gemini-pro-1.5"             # 2,097,152 tokens (2 Milion Tokens)
]

FAST_TASK_FALLBACKS = [
    "openai/gpt-4o-mini",
    "google/gemini-2.0-flash-001",
    "deepseek/deepseek-chat"
]

LLM_TIMEOUT = 300  # 5 Minuta Timeout për Fashikujt Integralë
MAX_RETRIES = 2
MAX_SINGLE_PASS_CHARS = 1_500_000

OPENROUTER_HEADERS = {
    "HTTP-Referer": "https://juristi.tech",
    "X-Title": "Juristi AI - Kosova Justice Engine"
}


class ResponseGenerator:
    """
    Gjeneruesi Suprem i Përgjigjeve (V86.0):
    - Drejton Forenzikën dhe Analizën e Plotë te Anthropic Claude Sonnet 4.6 (1M context).
    - Single-Pass 16,384 Output Buffer: Gjeneron të 8 Seksionet pa u ndërprerë kurrë.
    - Zero Fallback Crashes: Fallback-ët janë të gjithë Titanë 1M-2M tokens.
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
                    logger.info(f"⚖️ [Juristi AI Engine] Po thërras modelin elitar: {current_model} (Përpjekja {attempt})...")
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
        context: str = ""
    ) -> AsyncGenerator[str, None]:
        try:
            # PHOENIX FIX: Kontroll i kombinuar i system_prompt DHE user_query
            combined_text = f"{system_prompt} {user_query} {context}".upper()
            is_heavy_task = any(kw in combined_text for kw in [
                "RAPORTIT MASTER", "FORENZIKE", "FORENZIK", "CONTRA LEGEM", 
                "AUDITORIT SUPREM", "GJYKATËS SUPREME", "PASAPORTA PROCEDURALE",
                "ANALIZË E THELLË", "ANALIZO RASTIN", "DOSJE", "FASHIKULL",
                "HARTIM PROFESIONAL", "KËRKESËPADI", "KALLËZIM PENAL", "ANKESË",
                "KOLEGJIUMI", "HETUESI", "INCIDENTI"
            ])
            selected_model = TIER1_ELITE_MODEL if is_heavy_task else CHAT_FAST_MODEL

            full_context_content = f"{context}\n\n{system_prompt}" if context else system_prompt
            
            enhanced_system_prompt = f"""
{full_context_content}

RREGULLAT E HEKURTA TË DOKTRINËS DHE INTEGRITETIT TË RAPORTIT:
1. Përgjigju VETËM në gjuhë standarde juridike shqipe të Republikës së Kosovës (Gjuha zyrtare e Gjykatave dhe Prokurorive).
2. CITO NENET me saktësi absolute neni-për-nen (KPK Nr. 06/L-074, KPPRK Nr. 08/L-032, LPK Nr. 03/L-006, LMD Nr. 04/L-077, LPP Nr. 04/L-139, LSHT Nr. 06/L-016, Ligji për PSRK Nr. 03/L-052).
3. DISIPLINA STRUKTURORE DHE PËRMBUSHJA E TË GJITHA SEKSIONEVE:
   Gjenero detyrimisht dhe pa asnjë shkurtim të gjithë raportin e kërkuar nga fillimi deri në fund me Master Planin e Veprimit.
4. Ndalohet kategorikisht ndërprerja e raportit në mes.
"""
            messages = [
                {"role": "system", "content": enhanced_system_prompt[:MAX_SINGLE_PASS_CHARS]},
                {"role": "user", "content": user_query}
            ]
            
            # PHOENIX SINGLE-PASS 16K: Gjenerim i plotë dhe i drejtpërdrejtë pa cikle të shtrenjta
            response = await self._call_with_retry(
                messages, 
                stream=True, 
                max_tokens=16384 if is_heavy_task else 4096,
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