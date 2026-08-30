# FILE: backend/app/services/rag/response_generator.py
# PHOENIX PROTOCOL - RESPONSE GENERATOR V4.0 (CHUNKED PROCESSING - FULL CONTEXT)

import logging
from typing import Optional, List, Dict, Any, AsyncGenerator
from openai import AsyncOpenAI
from app.core.config import settings
from app.services.pillars.hallucination_filter import HallucinationFilter

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat"
LLM_TIMEOUT = 120

# PHOENIX FIX: Kufiri i sigurt i token-ve
MAX_CHUNK_CHARS = 20_000  # ~5,000 token per chunk

class ResponseGenerator:
    """
    V4.0: Përpunim me chunks — AI i sheh të gjitha dokumentet.
    """

    def __init__(self):
        api_key = settings.OPENROUTER_API_KEY or settings.OPENAI_API_KEY
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=OPENROUTER_BASE_URL,
            timeout=LLM_TIMEOUT
        )

    def _split_context_into_chunks(self, context: str, chunk_size: int = MAX_CHUNK_CHARS) -> List[str]:
        """Ndan kontekstin në chunks të menaxhueshëm."""
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

    async def generate_stream(
        self,
        system_prompt: str,
        user_query: str,
        context: str = ""
    ) -> AsyncGenerator[str, None]:
        """
        V4.0: Përpunon dokumentet në chunks dhe përmbledh në fund.
        """
        try:
            # 1. Ndan kontekstin në chunks
            chunks = self._split_context_into_chunks(context)
            
            if len(chunks) <= 1:
                # Konteksti është mjaft i vogël — përpuno direkt
                response = await self.client.chat.completions.create(
                    model=OPENROUTER_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_query}
                    ],
                    temperature=0.1,
                    stream=False,
                    max_tokens=8192
                )
                
                full_text = response.choices[0].message.content or ""
                filtered_text, replaced = HallucinationFilter.filter_precedents_with_details(full_text)
                yield filtered_text
                
                if replaced:
                    details = "\n".join([f"   • {p}" for p in replaced])
                    yield f"\n\n---\n⚠️ **KUJDES I VEÇANTË:**\nPrecedentët e mëposhtëm u identifikuan si të PAVERIFIKUAR dhe duhet të hiqen:\n\n{details}\n"
                
            else:
                # Konteksti është i madh — përpuno në chunks
                yield "📋 Duke analizuar të gjitha dokumentet e fashikullit...\n\n"
                
                chunk_analyses = []
                
                for i, chunk in enumerate(chunks, 1):
                    chunk_prompt = f"""
                    Analizo Pjesën {i}/{len(chunks)} të dokumenteve.
                    
                    {system_prompt}
                    
                    DOKUMENTET (Pjesa {i}):
                    {chunk}
                    
                    Nxjerr:
                    1. Faktet kryesore
                    2. Shkeljet ligjore
                    3. Provat e rëndësishme
                    4. Aktorët
                    
                    Përgjigju shkurt dhe me pika.
                    """
                    
                    response = await self.client.chat.completions.create(
                        model=OPENROUTER_MODEL,
                        messages=[
                            {"role": "system", "content": chunk_prompt},
                            {"role": "user", "content": user_query}
                        ],
                        temperature=0.1,
                        stream=False,
                        max_tokens=4096
                    )
                    
                    chunk_analysis = response.choices[0].message.content or ""
                    chunk_analyses.append(f"### PJESA {i}:\n{chunk_analysis}")
                    yield f"✅ Pjesa {i}/{len(chunks)} u analizua.\n"
                
                # 2. Përmbledhja finale
                yield "\n🔗 Duke përmbledhur të gjitha analizat...\n"
                
                combined_analyses = "\n\n".join(chunk_analyses)
                
                final_prompt = f"""
                    Ti je Sokrati — Gjyqtari Suprem i Kosovës.
                    
                    Këtu janë analizat e pjesëve të veçanta të fashikullit:
                    
                    {combined_analyses}
                    
                    Përpilo një raport të plotë dhe të strukturuar me të 5 pikat e detyrueshme.
                    Përgjigju në gjuhën shqipe juridike.
                    """
                
                final_response = await self.client.chat.completions.create(
                    model=OPENROUTER_MODEL,
                    messages=[
                        {"role": "system", "content": final_prompt},
                        {"role": "user", "content": user_query}
                    ],
                    temperature=0.1,
                    stream=False,
                    max_tokens=8192
                )
                
                final_text = final_response.choices[0].message.content or ""
                filtered_text, replaced = HallucinationFilter.filter_precedents_with_details(final_text)
                yield filtered_text
                
                if replaced:
                    details = "\n".join([f"   • {p}" for p in replaced])
                    yield f"\n\n---\n⚠️ **KUJDES I VEÇANTË:**\nPrecedentët e mëposhtëm u identifikuan si të PAVERIFIKUAR dhe duhet të hiqen:\n\n{details}\n"
                
        except Exception as e:
            logger.error(f"❌ Response generation failed: {e}")
            yield f"\n[Gabim Gjatë Gjenerimit: {e}]"