# FILE: backend/app/services/rag/response_generator.py
# PHOENIX PROTOCOL - RESPONSE GENERATOR V6.0 (STREAMING + FILTER + WARNING)

import logging
from typing import Optional, List, Dict, Any, AsyncGenerator
from openai import AsyncOpenAI
from app.core.config import settings
from app.services.pillars.hallucination_filter import HallucinationFilter

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat"
LLM_TIMEOUT = 120

MAX_CHUNK_CHARS = 40_000

class ResponseGenerator:
    """
    V6.0: Streaming me filtër në fund.
    - Përdoruesi sheh përgjigjen duke u gjeneruar
    - Në fund, filtri kontrollon dhe tregon cilat precedentë janë të paverifikuar
    - Paralajmërimi shfaqet me listën e saktë të halucinacioneve
    """

    def __init__(self):
        api_key = settings.OPENROUTER_API_KEY or settings.OPENAI_API_KEY
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=OPENROUTER_BASE_URL,
            timeout=LLM_TIMEOUT
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
        
        logger.info(f"📋 [Chunked] Konteksti u nda në {len(chunks)} pjesë.")
        return chunks

    def _build_short_chunk_prompt(self, chunk: str, chunk_num: int, total_chunks: int) -> str:
        return f"""
LEXO me kujdes këto dokumente (Pjesa {chunk_num}/{total_chunks}) dhe ZBULO VETË:

1. Mospërputhjet në data (a ka prapadatime?)
2. Kontradiktat në fakte (Dokumenti A thotë X, B thotë Y?)
3. Shkeljet procedurale (a u respektuan afatet? a u dëgjuan palët?)
4. Provat e injoruara (a ka prova që u dorëzuan por nuk u vlerësuan?)
5. Veprimet e paligjshme (a ka elemente të veprës penale?)

DOKUMENTET:
{chunk}

NXIRR:
- Faktet kryesore (me datë)
- Shkeljet e gjetura (me referencë në dokument)
- Provat e rëndësishme
- Aktorët dhe rolet e tyre

Përgjigju shkurt, me pika. JO analiza të gjata.
"""

    def _build_final_prompt(self, combined_analyses: str, system_prompt: str, user_query: str) -> str:
        return f"""
Ti je Sokrati — Gjyqtari Suprem i Kosovës.

Këtu janë analizat e pjesëve të veçanta të fashikullit:
{combined_analyses}

{system_prompt}

Tani përpilo raportin e plotë dhe të strukturuar me të 5 pikat e detyrueshme.
BAZOHU VETËM në analizat e mësipërme dhe në dokumentet e fashikullit.
MOS shpik asgjë që nuk është në analiza ose në RAG context.
"""

    def _build_warning(self, replaced_precedents: List[str]) -> str:
        """
        PHOENIX FIX V6.0: Paralajmërimi me listën e saktë.
        """
        if not replaced_precedents:
            return ""
        
        details = "\n".join([f"   • {p}" for p in replaced_precedents])
        return f"""
---
⚠️ **KUJDES I VEÇANTË:** Precedentët e mëposhtëm u identifikuan si të PAVERIFIKUAR dhe duhet të hiqen:

{details}

Ju lutem verifikoni çdo referencë para përdorimit zyrtar.
"""

    async def generate_stream(
        self,
        system_prompt: str,
        user_query: str,
        context: str = ""
    ) -> AsyncGenerator[str, None]:
        try:
            chunks = self._split_context_into_chunks(context)
            
            if len(chunks) <= 1:
                # STREAMING për kontekst të vogël
                full_text = ""
                
                response = await self.client.chat.completions.create(
                    model=OPENROUTER_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt[:10_000]},
                        {"role": "user", "content": user_query}
                    ],
                    temperature=0.1,
                    stream=True,
                    max_tokens=8192
                )
                
                # Yield pjesët e përgjigjes në kohë reale
                async for chunk in response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        content_piece = chunk.choices[0].delta.content
                        full_text += content_piece
                        yield content_piece
                
                # Në fund, filtro dhe trego halucinacionet
                replaced = HallucinationFilter.extract_unverified_precedents(full_text)
                warning = self._build_warning(replaced)
                if warning:
                    yield warning
                
            else:
                # CHUNKED për kontekst të madh
                yield "📋 Duke analizuar të gjitha dokumentet e fashikullit...\n\n"
                
                chunk_analyses = []
                
                for i, chunk in enumerate(chunks, 1):
                    chunk_prompt = self._build_short_chunk_prompt(chunk, i, len(chunks))
                    
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
                
                yield "\n🔗 Duke përmbledhur të gjitha analizat...\n"
                
                combined_analyses = "\n\n".join(chunk_analyses)
                final_prompt = self._build_final_prompt(combined_analyses, system_prompt, user_query)
                
                final_response = await self.client.chat.completions.create(
                    model=OPENROUTER_MODEL,
                    messages=[
                        {"role": "system", "content": final_prompt[:20_000]},
                        {"role": "user", "content": user_query}
                    ],
                    temperature=0.1,
                    stream=True,
                    max_tokens=8192
                )
                
                # Yield përmbledhjen në kohë reale
                final_text = ""
                async for chunk in final_response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        content_piece = chunk.choices[0].delta.content
                        final_text += content_piece
                        yield content_piece
                
                # Në fund, filtro dhe trego halucinacionet
                replaced = HallucinationFilter.extract_unverified_precedents(final_text)
                warning = self._build_warning(replaced)
                if warning:
                    yield warning
                
        except Exception as e:
            logger.error(f"❌ Response generation failed: {e}")
            yield f"\n[Gabim Gjatë Gjenerimit: {e}]"