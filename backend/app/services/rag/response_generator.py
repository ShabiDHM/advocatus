# FILE: backend/app/services/rag/response_generator.py
# PHOENIX PROTOCOL - SEAMLESS SUPREME RESPONSE GENERATOR V65.0 (CLAUDE SONNET LATEST • 1M CONTEXT • UNIVERSAL ROUTING)

import logging
import asyncio
import os
import re
from typing import Optional, List, Dict, Any, AsyncGenerator
from openai import AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Modeli Primar Elitar (1 Milion Tokens Context) për Forenzikë dhe Analizë Dosjesh
TIER1_ELITE_MODEL = os.getenv("LLM_PRIMARY_MODEL", "anthropic/claude-sonnet-latest")

# Modelet e Shpejta për Chat dhe Pyetje të Përditshme
CHAT_FAST_MODEL = os.getenv("CHAT_FAST_MODEL", "deepseek/deepseek-chat")
CHAT_DEEP_MODEL = os.getenv("CHAT_DEEP_MODEL", "deepseek/deepseek-r1")

# Hierarkia e Hekurt e Fallback-ut (Të gjitha me 1M - 2M tokens context)
HEAVY_TASK_FALLBACKS = [
    TIER1_ELITE_MODEL,
    "anthropic/claude-sonnet-latest",
    "anthropic/claude-fable-latest",
    "anthropic/claude-3.7-sonnet",
    "anthropic/claude-3.5-sonnet:beta",
    "google/gemini-2.0-flash-001",
    "openai/gpt-4o",
    "deepseek/deepseek-chat"
]

FAST_TASK_FALLBACKS = [
    CHAT_FAST_MODEL,
    "anthropic/claude-haiku-latest",
    "google/gemini-2.0-flash-001",
    "openai/gpt-4o-mini",
    TIER1_ELITE_MODEL
]

LLM_TIMEOUT = 140
MAX_RETRIES = 2

# Dritare masive 1M tokens për analizë dosjesh pa asnjë ndarje artificiale
MAX_SINGLE_PASS_CHARS = 1_200_000

OPENROUTER_HEADERS = {
    "HTTP-Referer": "https://juristi.tech",
    "X-Title": "Juristi AI - Kosova Justice Engine"
}


class ResponseGenerator:
    """
    Gjeneruesi Suprem i Përgjigjeve (V65.0):
    - Drejton Butonin "FORENSIKË" dhe "ANALIZO RASTIN" te Anthropic Claude Sonnet Latest (1M tokens).
    - Mbron sistemin me hierarkinë e fallback-ut (Fable Latest / Gemini 2.0).
    - Garanton gjuhë të pastër gjyqësore shqipe për Republikën e Kosovës pa gabime konteksti.
    """

    def __init__(self):
        api_key = (
            getattr(settings, "OPENROUTER_API_KEY", None)
            or os.getenv("OPENROUTER_API_KEY", "")
            or os.getenv("OPENAI_API_KEY", "")
        )
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=OPENROUTER_BASE_URL,
            timeout=LLM_TIMEOUT,
            default_headers=OPENROUTER_HEADERS
        )

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
        
        unique_models = []
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
                        logger.warning(f"⚠️ [Rate Limit] në {current_model}: {e}. Po pres 2s...")
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
            # Identifikon automatikisht nëse është FORENSIKË apo ANALIZË E DOSJES
            is_heavy_task = any(kw in system_prompt.upper() for kw in [
                "RAPORTIT MASTER", "FORENZIKE", "FORENZIK", "CONTRA LEGEM", 
                "AUDITORIT SUPREM", "GJYKATËS SUPREME", "PASAPORTA PROCEDURALE",
                "ANALIZË E THELLË", "ANALIZO RASTIN", "DOSJE", "FASHIKULL"
            ])
            selected_model = TIER1_ELITE_MODEL if is_heavy_task else CHAT_FAST_MODEL

            full_context_content = f"{context}\n\n{system_prompt}" if context else system_prompt
            
            enhanced_system_prompt = f"""
{full_context_content}

RREGULLAT E HEKURTA TË GJUHËS DHE DOKTRINËS SË KOSOVËS:
1. Përgjigju VETËM në gjuhë standarde juridike shqipe të Republikës së Kosovës (Gjuha zyrtare e Gjykatave dhe Prokurorive).
2. Gjenero NJË RAPORT TË VETËM, TË PLOTË, DHE SHKENCOR ME TË 8 SEKSIONET.
3. CITO NENET me saktësi absolute neni-për-nen (KPK Nr. 06/L-074, KPPRK Nr. 08/L-032, LPK Nr. 03/L-006, LMD Nr. 04/L-077, LPP Nr. 04/L-139).
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