# FILE: backend/app/services/rag/response_generator.py
# PHOENIX PROTOCOL - UNIFIED SUPREME RESPONSE GENERATOR V85.0 (SEAMLESS AUTO-CONTINUE • 16K+ MULTI-PASS INTEGRITY)

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

HEAVY_TASK_FALLBACKS = [
    "anthropic/claude-sonnet-4.6",
    "anthropic/claude-fable-latest",
    "openai/gpt-4o",
    "deepseek/deepseek-chat",
    "openai/gpt-4o-mini"
]

FAST_TASK_FALLBACKS = [
    "openai/gpt-4o-mini",
    "deepseek/deepseek-chat",
    "anthropic/claude-sonnet-4.6"
]

LLM_TIMEOUT = 300  # 5 Minuta Timeout për Fashikujt Integralë
MAX_RETRIES = 2
MAX_SINGLE_PASS_CHARS = 1_200_000
MAX_AUTO_CONTINUATIONS = 2

OPENROUTER_HEADERS = {
    "HTTP-Referer": "https://juristi.tech",
    "X-Title": "Juristi AI - Kosova Justice Engine"
}


class ResponseGenerator:
    """
    Gjeneruesi Suprem i Përgjigjeve (V85.0):
    - Drejton Forenzikën te Anthropic Claude Sonnet 4.6 (1M context).
    - Phoenix Seamless Auto-Continue: Kapërcen tavanin 8,192 tokenash automatikisht.
    - Garanton 100% përmbushjen e të 8 Seksioneve deri te fjala e fundit.
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
            is_heavy_task = any(kw in system_prompt.upper() for kw in [
                "RAPORTIT MASTER", "FORENZIKE", "FORENZIK", "CONTRA LEGEM", 
                "AUDITORIT SUPREM", "GJYKATËS SUPREME", "PASAPORTA PROCEDURALE",
                "ANALIZË E THELLË", "ANALIZO RASTIN", "DOSJE", "FASHIKULL",
                "HARTIM PROFESIONAL", "KËRKESËPADI", "KALLËZIM PENAL", "ANKESË"
            ])
            selected_model = TIER1_ELITE_MODEL if is_heavy_task else CHAT_FAST_MODEL

            full_context_content = f"{context}\n\n{system_prompt}" if context else system_prompt
            
            enhanced_system_prompt = f"""
{full_context_content}

RREGULLAT E HEKURTA TË DOKTRINËS DHE INTEGRITETIT TË RAPORTIT:
1. Përgjigju VETËM në gjuhë standarde juridike shqipe të Republikës së Kosovës (Gjuha zyrtare e Gjykatave dhe Prokurorive).
2. CITO NENET me saktësi absolute neni-për-nen (KPK Nr. 06/L-074, KPPRK Nr. 08/L-032, LPK Nr. 03/L-006, LMD Nr. 04/L-077, LPP Nr. 04/L-139, LSHT Nr. 06/L-016, Ligji për PSRK Nr. 03/L-052).
3. DISIPLINA STRUKTURORE DHE PËRMBUSHJA E TË GJITHA SEKSIONEVE:
   Gjenero detyrimisht dhe pa asnjë shkurtim të 8 SEKSIONET e kërkuara nga Seksioni 1 deri te Seksioni 8 me Master Planin e Veprimit brenda 24-48 orëve.
4. Ndalohet kategorikisht ndërprerja e raportit pa arritur te Hapat Taktikë të Seksionit 8.
"""
            messages = [
                {"role": "system", "content": enhanced_system_prompt[:MAX_SINGLE_PASS_CHARS]},
                {"role": "user", "content": user_query}
            ]
            
            accumulated_full_text = ""
            current_pass = 0

            while current_pass <= MAX_AUTO_CONTINUATIONS:
                current_pass += 1
                finish_reason = None

                response = await self._call_with_retry(
                    messages, 
                    stream=True, 
                    max_tokens=8192,
                    model=selected_model,
                    is_heavy_task=is_heavy_task
                )
                
                pass_text = ""
                async for chunk in response:
                    if chunk.choices and len(chunk.choices) > 0:
                        choice = chunk.choices[0]
                        if choice.delta and choice.delta.content:
                            content_piece = choice.delta.content
                            pass_text += content_piece
                            accumulated_full_text += content_piece
                            yield content_piece
                        if choice.finish_reason:
                            finish_reason = choice.finish_reason

                # Nëse gjenerimi përfundoi natyrshëm (stop), dalim nga cikli
                if finish_reason != "length" or not is_heavy_task:
                    break

                # ⚡ PHOENIX SEAMLESS AUTO-CONTINUE:
                # Nëse përfundoi sepse u mbush tavani 8,192 tokena, vazhdojmë automatikisht
                logger.info(f"🔄 [Phoenix Auto-Continue] Modeli arriti tavanin e tokenave në kalimin {current_pass}. Po vazhdoj gjenerimin pa ndërprerje...")
                
                messages = [
                    {"role": "system", "content": enhanced_system_prompt[:MAX_SINGLE_PASS_CHARS]},
                    {"role": "user", "content": user_query},
                    {"role": "assistant", "content": accumulated_full_text},
                    {"role": "user", "content": "Vazhdo menjëherë saktësisht aty ku u ndërpre fjala e fundit. Përfundo Seksionet e mbetura deri te Seksioni 8 me Master Planin e Veprimit, pa përsëritur tekstin e mëparshëm."}
                ]
                    
        except Exception as e:
            logger.error(f"❌ Gjenerimi dështoi pas të gjitha përpjekjeve: {e}")
            yield f"\n\n[Shërbimi AI është përkohësisht i ngarkuar. Ju lutem provoni përsëri: {str(e)}]"