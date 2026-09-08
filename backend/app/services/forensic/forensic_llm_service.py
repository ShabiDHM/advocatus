# FILE: backend/app/services/forensic/forensic_llm_service.py
# PHOENIX PROTOCOL - FORENSIC DEDICATED LLM ENGINE V1.0 (STRICT CLAUDE SONNET 4.6 • ZERO DOWNGRADE)

import os
import time
import asyncio
import logging
from typing import Dict, Any, AsyncGenerator, Optional
from openai import OpenAI, AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1"
FORENSIC_SYSTEM_IDENTITY = """[REPUBLIKA E KOSOVËS • ZYRA FORENZIKE HETIMORE GJYQËSORE]
JU JENI: Eksperti Suprem Forenzik Ligjor dhe Kriminalistik i Juristi AI.
MANDATI JUAJ:
1. Përdorni vetëm standarde të larta hetimore dhe forenzike shkencore.
2. Citoni me saktësi kirurgjikale ligjet e aplikueshme në Republikën e Kosovës (Kodi Penal, Kodi i Procedurës Penale, Ligji për Marrëdhëniet e Detyrimeve, Ligji mbi Pronësinë).
3. Çdo provë analizohet sipas 'Chain of Custody' dhe parimit 'In Dubio Pro Reo'.
4. GJUHA E DETYRUESHME: Shqipe standarde zyrtare administrative-juridike.
5. Asnjëherë mos hamendësoni fakte apo nene që nuk ekzistojnë."""

class ForensicLLMError(Exception):
    """Përjashtim i dedikuar kur motori forenzik dështon pa u komprometuar."""
    pass

def _get_openrouter_key() -> str:
    key = getattr(settings, "OPENROUTER_API_KEY", None) or os.getenv("OPENROUTER_API_KEY", "")
    if not key:
        raise ForensicLLMError("OPENROUTER_API_KEY nuk është konfiguruar në server për Zyrën Forenzike.")
    return key

def _get_forensic_model() -> str:
    return getattr(settings, "FORENSIC_LLM_MODEL", "anthropic/claude-sonnet-4.6")

def _get_sync_client() -> OpenAI:
    return OpenAI(
        api_key=_get_openrouter_key(),
        base_url=OPENROUTER_URL,
        timeout=300.0,
        default_headers={
            "HTTP-Referer": "https://juristi.tech",
            "X-Title": "Juristi AI - Forensic High-Precision Engine"
        }
    )

def _get_async_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=_get_openrouter_key(),
        base_url=OPENROUTER_URL,
        timeout=300.0,
        default_headers={
            "HTTP-Referer": "https://juristi.tech",
            "X-Title": "Juristi AI - Forensic High-Precision Engine"
        }
    )

def call_forensic_llm(
    system_prompt: str,
    user_content: str,
    json_mode: bool = False,
    temperature: float = 0.0,
    max_tokens: int = 16384
) -> str:
    """
    Ekzekuton thirrjen te Claude Sonnet 4.6 në mënyrë sinkrone.
    PA ASNJË FALLBACK TE MODELE TË LIRA.
    """
    client = _get_sync_client()
    target_model = _get_forensic_model()

    full_system = f"{FORENSIC_SYSTEM_IDENTITY}\n\n{system_prompt}"
    
    kwargs: Dict[str, Any] = {
        "model": target_model,
        "messages": [
            {"role": "system", "content": full_system},
            {"role": "user", "content": user_content}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    retries = 3
    last_error: Optional[Exception] = None

    for attempt in range(retries):
        try:
            logger.info(f"🔬 [Forensic LLM] Ekzekutim në {target_model} (Tentativa {attempt + 1}/{retries})...")
            res = client.chat.completions.create(**kwargs)
            if res and res.choices and len(res.choices) > 0:
                content = getattr(res.choices[0].message, "content", "") or ""
                if content.strip():
                    return content
        except Exception as e:
            last_error = e
            logger.warning(f"⚠️ [Forensic LLM Attempt {attempt + 1}] Vonesë/Gabim nga {target_model}: {e}")
            if attempt < retries - 1:
                time.sleep(2.0 * (attempt + 1))
                continue

    raise ForensicLLMError(f"Motori Forenzik ({target_model}) dështoi pas {retries} tentativave: {last_error}")

async def call_forensic_llm_async(
    system_prompt: str,
    user_content: str,
    json_mode: bool = False,
    temperature: float = 0.0,
    max_tokens: int = 16384
) -> str:
    """
    Ekzekuton thirrjen te Claude Sonnet 4.6 në mënyrë asinkrone.
    PA ASNJË FALLBACK TE MODELE TË LIRA.
    """
    client = _get_async_client()
    target_model = _get_forensic_model()

    full_system = f"{FORENSIC_SYSTEM_IDENTITY}\n\n{system_prompt}"

    kwargs: Dict[str, Any] = {
        "model": target_model,
        "messages": [
            {"role": "system", "content": full_system},
            {"role": "user", "content": user_content}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    retries = 3
    last_error: Optional[Exception] = None

    for attempt in range(retries):
        try:
            res = await client.chat.completions.create(**kwargs)
            if res and res.choices and len(res.choices) > 0:
                content = getattr(res.choices[0].message, "content", "") or ""
                if content.strip():
                    return content
        except Exception as e:
            last_error = e
            logger.warning(f"⚠️ [Forensic LLM Async Attempt {attempt + 1}] Gabim nga {target_model}: {e}")
            if attempt < retries - 1:
                await asyncio.sleep(2.0 * (attempt + 1))
                continue

    raise ForensicLLMError(f"Motori Forenzik Asinkron ({target_model}) nuk u përgjigj: {last_error}")

async def stream_forensic_llm_async(
    system_prompt: str,
    user_content: str,
    temperature: float = 0.0,
    max_tokens: int = 16384
) -> AsyncGenerator[str, None]:
    """
    Transmeton (stream) përgjigjen e Claude Sonnet 4.6 për Terminalin Forenzik.
    """
    client = _get_async_client()
    target_model = _get_forensic_model()

    full_system = f"{FORENSIC_SYSTEM_IDENTITY}\n\n{system_prompt}"

    try:
        stream = await client.chat.completions.create(
            model=target_model,
            messages=[
                {"role": "system", "content": full_system},
                {"role": "user", "content": user_content}
            ],
            temperature=temperature,
            stream=True,
            max_tokens=max_tokens
        )
        async for chunk in stream:
            if chunk.choices and len(chunk.choices) > 0 and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    except Exception as e:
        logger.error(f"❌ [Forensic LLM Stream] Gabim kritik: {e}")
        yield f"\n\n[GABIM FORENZIK KRITIK: Lidhja me {target_model} u ndërpre: {str(e)}]"