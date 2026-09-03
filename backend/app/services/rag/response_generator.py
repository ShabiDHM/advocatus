# FILE: backend/app/services/rag/response_generator.py
# PHOENIX PROTOCOL - UNIFIED SUPREME RESPONSE GENERATOR V66.0 (CLAUDE SONNET LATEST • 1M CONTEXT • UNIVERSAL ROUTING)

import logging
import asyncio
import os
import re
from typing import Optional, List, Dict, Any, AsyncGenerator
from openai import AsyncOpenAI
from app.core.config import settings

# Importimi nga Porta Qendrore e LLM
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

# Modelet e Unifikuara nga llm_client
TIER1_ELITE_MODEL = DEEP_MODEL
CHAT_FAST_MODEL = FAST_MODEL

# Hierarkia e Sigurt e Fallback-ut (Modele 100% aktive në OpenRouter me dritare 128K deri 1M tokens)
HEAVY_TASK_FALLBACKS = [
    TIER1_ELITE_MODEL,
    "anthropic/claude-sonnet-latest",
    "anthropic/claude-3.7-sonnet",
    "openai/gpt-4o",
    "deepseek/deepseek-chat",
    "openai/gpt-4o-mini"
]

FAST_TASK_FALLBACKS = [
    CHAT_FAST_MODEL,
    "openai/gpt-4o-mini",
    "deepseek/deepseek-chat",
    "anthropic/claude-haiku-latest",
    TIER1_ELITE_MODEL
]

LLM_TIMEOUT = 140
MAX_RETRIES = 2

# Dritare masive 1M tokens për analizë dosjesh
MAX_SINGLE_PASS_CHARS = 1_200_000

OPENROUTER_HEADERS = {
    "HTTP-Referer": "https://juristi.tech",
    "X-Title": "Juristi AI - Kosova Justice Engine"
}


class ResponseGenerator:
    """
    Gjeneruesi Suprem i Përgjigjeve (V66.0):
    - Drejton Detyrat e Rënda (Forenzikë, Analizë Dosjeje, Hartim Aktesh) te Anthropic Claude Sonnet Latest (1M tokens).
    - Mbron sistemin me hierarkinë e fallback-ut të pathyeshëm (GPT-4o / DeepSeek).
    - Zbaton gjuhë të pastër gjyqësore shqipe për Republikën e Kosovës pa deformuar kërkesën e përdoruesit.
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
                    logger.info(f"⚖️ [Juristi AI Engine] Po thërras modelin: {current_model} (Përpjekja {attempt})...")
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
            # Identifikon automatikisht nëse është detyrë e rëndë që kërkon Claude Sonnet
            is_heavy_task = any(kw in system_prompt.upper() for kw in [
                "RAPORTIT MASTER", "FORENZIKE", "FORENZIK", "CONTRA LEGEM", 
                "AUDITORIT SUPREM", "GJYKATËS SUPREME", "PASAPORTA PROCEDURALE",
                "ANALIZË E THELLË", "ANALIZO RASTIN", "DOSJE", "FASHIKULL",
                "HARTIM PROFESIONAL", "KËRKESËPADI", "KALLËZIM PENAL", "ANKESË"
            ])
            selected_model = TIER1_ELITE_MODEL if is_heavy_task else CHAT_FAST_MODEL

            full_context_content = f"{context}\n\n{system_prompt}" if context else system_prompt
            
            # PHOENIX FIX: Rregulla të pastra gjuhësore dhe statutore pa imponuar me dhunë 8 seksione kur kërkohet hartim akti
            enhanced_system_prompt = f"""
{full_context_content}

RREGULLAT E HEKURTA TË GJUHËS DHE DOKTRINËS SË KOSOVËS:
1. Përgjigju VETËM në gjuhë standarde juridike shqipe të Republikës së Kosovës (Gjuha zyrtare e Gjykatave dhe Prokurorive).
2. CITO NENET me saktësi absolute neni-për-nen (KPK Nr. 06/L-074, KPPRK Nr. 08/L-032, LPK Nr. 03/L-006, LMD Nr. 04/L-077, LPP Nr. 04/L-139, LSHT Nr. 06/L-016).
3. Zbato me rigorozitet formatin, strukturën dhe misionin e përcaktuar në udhëzimet e mësipërme.
4. Ndalohet kategorikisht përgjigja me refuzim kur teksti përmban shkresa gjyqësore, prova materiale apo pretendime procedurale të palëve.
"""
            messages = [
                {"role": "system", "content": enhanced_system_prompt[:MAX_SINGLE_PASS_CHARS]},
                {"role": "user", "content": user_query}
            ]
            
            response = await self._call_with_retry(
                messages, 
                stream=True, 
                max_tokens=8192,
                model=selected_model,
                is_heavy_task=is_heavy_task
            )
            
            async for chunk in response:
                if chunk.choices and len(chunk.choices) > 0 and chunk.choices[0].delta.content:
                    content_piece = chunk.choices[0].delta.content
                    yield content_piece
                    
        except Exception as e:
            logger.error(f"❌ Gjenerimi dështoi pas të gjitha përpjekjeve: {e}")
            yield f"\n\n[Shërbimi AI është përkohësisht i ngarkuar. Ju lutem provoni përsëri: {str(e)}]"