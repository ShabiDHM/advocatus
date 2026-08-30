# FILE: backend/app/services/rag/response_generator.py
# PHOENIX PROTOCOL - RESPONSE GENERATOR V2.0 (BUFFER & FILTER BEFORE YIELD)

import logging
from typing import Optional, List, Dict, Any, AsyncGenerator
from openai import AsyncOpenAI
from app.core.config import settings
from app.services.pillars.hallucination_filter import HallucinationFilter

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat"
LLM_TIMEOUT = 90

HALLUCINATION_WARNING = (
    "\n\n---\n"
    "⚠️ **KUJDES I VEÇANTË:**\n"
    "*Disa precedentë në këtë përgjigje u identifikuan si të paverifikuar në bazën tonë dhe u zëvendësuan me '[Nuk u gjet ky precedent në bazën tonë]'. "
    "Ju lutem verifikoni çdo referencë para përdorimit zyrtar.*"
)

class ResponseGenerator:
    """
    Thërret LLM, mbledh përgjigjen, FILTRON, dhe pastaj yield-on.
    """

    def __init__(self):
        api_key = settings.OPENROUTER_API_KEY or settings.OPENAI_API_KEY
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=OPENROUTER_BASE_URL,
            timeout=LLM_TIMEOUT
        )

    async def generate_stream(
        self,
        system_prompt: str,
        user_query: str
    ) -> AsyncGenerator[str, None]:
        """
        PHOENIX FIX V2.0: Buffer + Filter + Yield.
        Mbledhim të gjithë përgjigjen, filtrojmë, pastaj yield-ojmë të pastruar.
        """
        try:
            response = await self.client.chat.completions.create(
                model=OPENROUTER_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query}
                ],
                temperature=0.1,
                stream=True,
                max_tokens=8192
            )
            
            # 1. Mbledhim të gjithë përgjigjen
            full_text = ""
            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    full_text += chunk.choices[0].delta.content
            
            # 2. Filtrojmë përgjigjen e plotë
            filtered_text = HallucinationFilter.filter_precedents(full_text)
            
            # 3. Yield-ojmë tekstin e pastruar
            yield filtered_text
            
            # 4. Nëse filtri ndryshoi diçka, shto paralajmërim
            if filtered_text != full_text:
                yield HALLUCINATION_WARNING
                
        except Exception as e:
            logger.error(f"❌ Response generation failed: {e}")
            yield f"\n[Gabim Gjatë Gjenerimit: {e}]"