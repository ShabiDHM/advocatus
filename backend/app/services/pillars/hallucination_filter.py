# FILE: backend/app/services/rag/response_generator.py
# PHOENIX PROTOCOL - RESPONSE GENERATOR V3.1 (UPDATED WARNING TEXT)

import logging
from typing import Optional, List, Dict, Any, AsyncGenerator
from openai import AsyncOpenAI
from app.core.config import settings
from app.services.pillars.hallucination_filter import HallucinationFilter

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat"
LLM_TIMEOUT = 90

class ResponseGenerator:
    """
    Thërret LLM, mbledh përgjigjen, FILTRON, dhe pastaj yield-on.
    Gjithashtu tregon saktësisht cilët precedentë duhet të hiqen.
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
        PHOENIX FIX V3.1: Buffer + Filter + Yield + Paralajmërim i përditësuar.
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
            
            # 2. Filtrojmë dhe marrim listën e halucinacioneve
            filtered_text, replaced_precedents = HallucinationFilter.filter_precedents_with_details(full_text)
            
            # 3. Yield-ojmë tekstin e pastruar
            yield filtered_text
            
            # 4. Nëse ka halucinacione, tregojmë saktësisht cilat DUHET TË HIQEN
            if replaced_precedents:
                details = "\n".join([f"   • {p}" for p in replaced_precedents])
                warning = f"""
---
⚠️ **KUJDES I VEÇANTË:**
Precedentët e mëposhtëm u identifikuan si të PAVERIFIKUAR dhe duhet të hiqen:

{details}

Ju lutem verifikoni çdo referencë para përdorimit zyrtar.
"""
                yield warning
                
        except Exception as e:
            logger.error(f"❌ Response generation failed: {e}")
            yield f"\n[Gabim Gjatë Gjenerimit: {e}]"