# FILE: backend/app/services/rag/response_generator.py
# PHOENIX PROTOCOL - SEAMLESS SUPREME RESPONSE GENERATOR V55.0 (ZERO CHUNKING LEAKS & UNIFIED REPORT)

import logging
import asyncio
import os
import re
from typing import Optional, List, Dict, Any, AsyncGenerator
from openai import AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Modelet
CHAT_FAST_MODEL = os.getenv("CHAT_FAST_MODEL", "deepseek/deepseek-chat")
CHAT_DEEP_MODEL = os.getenv("CHAT_DEEP_MODEL", "deepseek/deepseek-r1")
TIER1_ELITE_MODEL = os.getenv("LLM_PRIMARY_MODEL", "anthropic/claude-3.5-sonnet")

LLM_TIMEOUT = 120
MAX_RETRIES = 3

# Claude 3.5 Sonnet mban deri në 200,000 tokens (~600,000 karaktere) në 1 thirrje të vetme
MAX_SINGLE_PASS_CHARS = 450_000

OPENROUTER_HEADERS = {
    "HTTP-Referer": "https://juristi.tech",
    "X-Title": "Juristi AI - Kosova Justice Engine"
}

class ResponseGenerator:
    """
    Gjeneruesi Suprem i Përgjigjeve (V55.0):
    - Transmetim i pandërprerë me 1 kalim të vetëm (Zero duplikime Pjesa 1 / Pjesa 2).
    - Pastrim i plotë i mesazheve teknike të panevojshme.
    - Tier-1 Claude 3.5 Sonnet për Forenzikë & Analizë.
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
        model: Optional[str] = None
    ):
        last_error = None
        target_model = model or TIER1_ELITE_MODEL
        models_to_try = [target_model, TIER1_ELITE_MODEL, "openai/gpt-4o", CHAT_FAST_MODEL]
        
        unique_models = []
        for m in models_to_try:
            if m not in unique_models:
                unique_models.append(m)

        for current_model in unique_models:
            for attempt in range(1, MAX_RETRIES + 1):
                try:
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
                        logger.warning(f"⚠️ [Retry {attempt}/{MAX_RETRIES}] në {current_model}: {e}. Po riprovoj...")
                        await asyncio.sleep(attempt * 1.5)
                        continue
                    else:
                        logger.warning(f"⚠️ Dështoi {current_model}: {e}")
                        break
        
        raise last_error if last_error else Exception("Dështoi komunikimi me të gjithë ofruesit e LLM.")

    async def generate_stream(
        self,
        system_prompt: str,
        user_query: str,
        context: str = ""
    ) -> AsyncGenerator[str, None]:
        try:
            # Përcakto modelin: Nëse është Analizë / Forenzikë / Drafting ➔ Tier-1 Claude 3.5 Sonnet
            is_heavy_task = any(kw in system_prompt for kw in [
                "RAPORTIT MASTER", "AUTORITETI DHE MISIONI YT", "FORENZIKE", "CONTRA LEGEM", "AUDITORIT SUPREM"
            ])
            selected_model = TIER1_ELITE_MODEL if is_heavy_task else CHAT_FAST_MODEL

            # E gjithë përmbajtja dërgohet në 1 THIRRJE TË VETME TË PASTËR
            full_context_content = f"{context}\n\n{system_prompt}" if context else system_prompt
            
            enhanced_system_prompt = f"""
{full_context_content}

RREGULLAT E HEKURTA TË GJUHËS DHE DOKTRINËS SË KOSOVËS:
1. Përgjigju VETËM në gjuhë standarde juridike shqipe të Republikës së Kosovës.
2. Gjenero NJË RAPORT TË VETËM, TË PLOTË dhe TË PANDARË NË PJESË.
3. CITO NENET me saktësi absolute neni-për-nen (KPK Nr. 06/L-074, KPPRK Nr. 08/L-032, LPK Nr. 03/L-006, LMD Nr. 04/L-077).
4. Ndalohet kategorikisht përsëritja e titujve apo shfaqja e teksteve teknike të ndarjes në pjesë.
"""
            messages = [
                {"role": "system", "content": enhanced_system_prompt[:MAX_SINGLE_PASS_CHARS]},
                {"role": "user", "content": user_query}
            ]
            
            response = await self._call_with_retry(
                messages, 
                stream=True, 
                max_tokens=8192,
                model=selected_model
            )
            
            async for chunk in response:
                if chunk.choices and len(chunk.choices) > 0 and chunk.choices[0].delta.content:
                    content_piece = chunk.choices[0].delta.content
                    yield content_piece
                    
        except Exception as e:
            logger.error(f"❌ Gjenerimi dështoi pas të gjitha përpjekjeve: {e}")
            yield f"\n\n[Shërbimi AI është përkohësisht i ngarkuar. Ju lutem provoni përsëri: {str(e)}]"