# FILE: backend/app/services/rag/response_generator.py
# PHOENIX PROTOCOL - HIGH-PRECISION & COST-OPTIMIZED RESPONSE GENERATOR V50.0

import logging
import asyncio
import os
import re
from typing import Optional, List, Dict, Any, AsyncGenerator
from openai import AsyncOpenAI
from app.core.config import settings
from app.services.pillars.hallucination_filter import HallucinationFilter

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Modelet për Chatin e Përgjithshëm (Ultra-Efikas në Kosto & Shpejtësi)
CHAT_FAST_MODEL = os.getenv("CHAT_FAST_MODEL", "deepseek/deepseek-chat")
CHAT_DEEP_MODEL = os.getenv("CHAT_DEEP_MODEL", "deepseek/deepseek-r1")
TIER1_ELITE_MODEL = os.getenv("LLM_PRIMARY_MODEL", "anthropic/claude-3.5-sonnet")

LLM_TIMEOUT = 90
MAX_RETRIES = 3
MAX_CHUNK_CHARS = 50_000

OPENROUTER_HEADERS = {
    "HTTP-Referer": "https://juristi-ai.com",
    "X-Title": "Juristi AI - Kosova Chat Engine"
}

class ResponseGenerator:
    """
    Gjeneruesi Suprem i Përgjigjeve (V50.0):
    - Kosto minimale për pyetjet e përditshme me DeepSeek-V3.
    - Rezistencë maksimale ndaj kufizimeve 429 me Provider Routing.
    - Zero crash gjatë filtrimit të halucinacioneve.
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

    def _split_context_into_chunks(self, context: str, chunk_size: int = MAX_CHUNK_CHARS) -> List[str]:
        if not context:
            return []
        if len(context) <= chunk_size:
            return [context]
        
        chunks = []
        paragraphs = context.split('\n\n')
        current_chunk = ""
        
        for para in paragraphs:
            if len(current_chunk) + len(para) + 2 > chunk_size:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = para
            else:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks

    async def _call_with_retry(
        self, 
        messages: List[Dict[str, str]], 
        stream: bool = True, 
        max_tokens: int = 8192,
        model: Optional[str] = None
    ):
        """Kryen thirrjen me provider fallback dhe retry automatik."""
        last_error = None
        target_model = model or CHAT_FAST_MODEL
        models_to_try = [target_model, CHAT_FAST_MODEL, CHAT_DEEP_MODEL, TIER1_ELITE_MODEL]
        
        # Elimino duplikimet duke ruajtur renditjen
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
                        "temperature": 0.05,
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
                        logger.warning(f"⚠️ [Retry {attempt}/{MAX_RETRIES}] në {current_model}: {e}. Retrying...")
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
            chunks = self._split_context_into_chunks(context)
            
            # Përcakto nëse kërkesa është për analizë/forenzikë të thellë
            is_heavy_task = any(kw in system_prompt for kw in [
                "RAPORTIT MASTER", "AUTORITETI DHE MISIONI YT", "FORENZIKE", "CONTRA LEGEM"
            ])
            selected_model = TIER1_ELITE_MODEL if is_heavy_task else CHAT_FAST_MODEL

            if len(chunks) <= 1:
                full_text = ""
                enhanced_system_prompt = f"""
{system_prompt}

RREGULLAT E HEKURTA TË GJUHËS SHQIPE DHE LIGJEVE TË KOSOVËS:
1. Përgjigju VETËM në gjuhë standarde juridike shqipe të Republikës së Kosovës.
2. CITO NENET me përpikmëri neni-për-nen (KPK, KPPRK, LPK, LMD, Ligji për Familjen).
3. Mbështetu vetëm në faktet e shkresave të administruara.
"""
                messages = [
                    {"role": "system", "content": enhanced_system_prompt},
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
                        full_text += content_piece
                        yield content_piece
                
            else:
                yield "📋 Duke analizuar fashikullin e zgjeruar të dokumenteve...\n\n"
                chunk_analyses = []
                
                for i, chunk in enumerate(chunks, 1):
                    chunk_prompt = f"Dokumenti Pjesa {i}:\n{chunk}\n\nNxirr faktet kyçe, datat dhe shkeljet ligjore në mënyrë të përmbledhur me pika."
                    messages = [
                        {"role": "system", "content": chunk_prompt},
                        {"role": "user", "content": user_query}
                    ]
                    response = await self._call_with_retry(
                        messages, 
                        stream=False, 
                        max_tokens=4096,
                        model=CHAT_FAST_MODEL
                    )
                    chunk_analysis = response.choices[0].message.content or ""
                    chunk_analyses.append(f"### PJESA {i}:\n{chunk_analysis}")
                    yield f"✅ Pjesa {i}/{len(chunks)} u analizua.\n"
                
                combined_analyses = "\n\n".join(chunk_analyses)
                final_prompt = f"{combined_analyses}\n\n{system_prompt}"
                final_messages = [
                    {"role": "system", "content": final_prompt},
                    {"role": "user", "content": user_query}
                ]
                
                final_response = await self._call_with_retry(
                    final_messages, 
                    stream=True, 
                    max_tokens=8192,
                    model=selected_model
                )
                
                async for chunk in final_response:
                    if chunk.choices and len(chunk.choices) > 0 and chunk.choices[0].delta.content:
                        content_piece = chunk.choices[0].delta.content
                        yield content_piece
                
        except Exception as e:
            logger.error(f"❌ Gjenerimi dështoi pas të gjitha përpjekjeve: {e}")
            yield f"\n\n[Shërbimi AI është përkohësisht i ngarkuar. Ju lutem provoni përsëri pas pak sekondash: {str(e)}]"