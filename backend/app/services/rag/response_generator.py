# FILE: backend/app/services/rag/response_generator.py
# PHOENIX PROTOCOL - RESILIENT DEEPSEEK RESPONSE GENERATOR WITH PROVIDER ROUTING & AUTO-RETRY

import logging
import asyncio
from typing import Optional, List, Dict, Any, AsyncGenerator
from openai import AsyncOpenAI
from app.core.config import settings
from app.services.pillars.hallucination_filter import HallucinationFilter

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
PRIMARY_DEEPSEEK_MODEL = "deepseek/deepseek-chat"
FALLBACK_DEEPSEEK_MODEL = "deepseek/deepseek-r1"
LLM_TIMEOUT = 120
MAX_RETRIES = 3

MAX_CHUNK_CHARS = 40_000

class ResponseGenerator:
    """
    V8.0: Resilient DeepSeek Streaming me Provider Routing dhe Mbrojtje ndaj 429.
    """

    def __init__(self):
        api_key = settings.OPENROUTER_API_KEY or settings.OPENAI_API_KEY
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=OPENROUTER_BASE_URL,
            timeout=LLM_TIMEOUT,
            default_headers={
                "HTTP-Referer": "https://juristi.tech",
                "X-Title": "Juristi AI Platform",
            }
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

    async def _call_with_retry(self, messages: List[Dict[str, str]], stream: bool = True, max_tokens: int = 8192):
        """Kryen thirrjen me provider fallback për DeepSeek dhe retry automatik."""
        last_error = None
        models_to_try = [PRIMARY_DEEPSEEK_MODEL, FALLBACK_DEEPSEEK_MODEL]

        for model_name in models_to_try:
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    response = await self.client.chat.completions.create(
                        model=model_name,
                        messages=messages,
                        temperature=0.1,
                        stream=stream,
                        max_tokens=max_tokens,
                        extra_body={
                            "provider": {
                                "order": ["DeepSeek", "Fireworks", "Together", "Nebius", "DeepInfra"],
                                "allow_fallbacks": True
                            }
                        }
                    )
                    return response
                except Exception as e:
                    last_error = e
                    err_str = str(e).lower()
                    if "429" in err_str or "rate limit" in err_str or "temporarily" in err_str:
                        logger.warning(f"⚠️ [DeepSeek Retry {attempt}/{MAX_RETRIES}] on {model_name}: {e}. Retrying in {attempt}s...")
                        await asyncio.sleep(attempt * 1.5)
                        continue
                    else:
                        break
        
        raise last_error if last_error else Exception("Dështoi komunikimi me të gjithë ofruesit e DeepSeek.")

    async def generate_stream(
        self,
        system_prompt: str,
        user_query: str,
        context: str = ""
    ) -> AsyncGenerator[str, None]:
        try:
            chunks = self._split_context_into_chunks(context)
            
            if len(chunks) <= 1:
                full_text = ""
                enhanced_system_prompt = f"""
{system_prompt}

RREGULLAT E HEKURTA PËR GJUHËN SHQIPE DHE LIGJET:
1. Përgjigju VETËM në gjuhë të pastër shqipe standarde.
2. CITO NENET VETËM NËSE i sheh në kontekst ose i di me siguri absolute sipas ligjeve të Kosovës.
3. MOS vendos linqe URL. Përdor strukturë me pika dhe theksime të qarta.
"""
                messages = [
                    {"role": "system", "content": enhanced_system_prompt[:15_000]},
                    {"role": "user", "content": user_query}
                ]
                
                response = await self._call_with_retry(messages, stream=True, max_tokens=8192)
                
                async for chunk in response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        content_piece = chunk.choices[0].delta.content
                        full_text += content_piece
                        yield content_piece
                
                replaced = HallucinationFilter.extract_unverified_precedents(full_text)
                if replaced:
                    details = "\n".join([f"   • {p}" for p in replaced])
                    yield f"\n\n---\n⚠️ **Kujdes:** Referencat e mëposhtme duhet të verifikohen me tekstin zyrtar:\n{details}"
                
            else:
                yield "📋 Duke analizuar kontekstin e zgjeruar me DeepSeek...\n\n"
                chunk_analyses = []
                
                for i, chunk in enumerate(chunks, 1):
                    chunk_prompt = f"Dokumenti Pjesa {i}:\n{chunk}\n\nNxirr faktet kryesore dhe shkeljet ligjore në shqip me pika."
                    messages = [
                        {"role": "system", "content": chunk_prompt},
                        {"role": "user", "content": user_query}
                    ]
                    response = await self._call_with_retry(messages, stream=False, max_tokens=4096)
                    chunk_analysis = response.choices[0].message.content or ""
                    chunk_analyses.append(f"### PJESA {i}:\n{chunk_analysis}")
                    yield f"✅ Pjesa {i}/{len(chunks)} u analizua.\n"
                
                combined_analyses = "\n\n".join(chunk_analyses)
                final_prompt = f"{combined_analyses}\n\n{system_prompt}"
                final_messages = [
                    {"role": "system", "content": final_prompt[:20_000]},
                    {"role": "user", "content": user_query}
                ]
                
                final_response = await self._call_with_retry(final_messages, stream=True, max_tokens=8192)
                final_text = ""
                async for chunk in final_response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        content_piece = chunk.choices[0].delta.content
                        final_text += content_piece
                        yield content_piece
                
        except Exception as e:
            logger.error(f"❌ DeepSeek generation failed after retries: {e}")
            yield f"\n[Shërbimi AI i DeepSeek është përkohësisht i mbingarkuar. Ju lutem klikoni butonin 'Rianalizo' pas pak sekondash.]"