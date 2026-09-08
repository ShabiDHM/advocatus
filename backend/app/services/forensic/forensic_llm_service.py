# FILE: backend/app/services/forensic/forensic_llm_service.py
# PHOENIX PROTOCOL - FORENSIC DEDICATED LLM ENGINE V2.0 (MULTI-TURN CHAT MEMORY • CLAUDE SONNET 4.6)

import os
import time
import asyncio
import logging
from typing import Dict, Any, List, AsyncGenerator, Optional
from openai import OpenAI, AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1"
FORENSIC_SYSTEM_IDENTITY = """[REPUBLIKA E KOSOVËS • ZYRA FORENZIKE HETIMORE GJYQËSORE]
JU JENI: Eksperti Suprem Forenzik Ligjor dhe Kriminalistik i Juristi AI.
MANDATI JUAJ DHE KUJTESA HETIMORE:
1. Përdorni vetëm standarde të larta hetimore dhe forenzike shkencore.
2. KUJTONI me saktësi çdo provë, deklaratë, faturë, datë dhe emër të diskutuar më herët në këtë bisedë.
3. Nëse pyetja e re lidhet me një fakt të mëparshëm, ndërlidhni menjëherë faktet dhe nxirrni kontradiktat.
4. Citoni me saktësi kirurgjikale legjislacionin e Kosovës (KPK, KPPRK, LMD, LPK).
5. GJUHA E DETYRUESHME: Shqipe standarde zyrtare administrative-juridike.
6. Asnjëherë mos hamendësoni fakte apo nene që nuk ekzistojnë."""

class ForensicLLMError(Exception):
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
    """Thirrje e thjeshtë një-hapëshe te Claude Sonnet 4.6."""
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
            res = client.chat.completions.create(**kwargs)
            if res and res.choices and len(res.choices) > 0:
                content = getattr(res.choices[0].message, "content", "") or ""
                if content.strip():
                    return content
        except Exception as e:
            last_error = e
            if attempt < retries - 1:
                time.sleep(2.0 * (attempt + 1))
                continue

    raise ForensicLLMError(f"Motori Forenzik ({target_model}) dështoi: {last_error}")

def call_forensic_llm_chat(
    conversation_turns: List[Dict[str, str]],
    system_prompt: str = "",
    temperature: float = 0.0,
    max_tokens: int = 16384
) -> str:
    """
    THIRRJE ME KUJTESË TË PLOTË DHE TË ZGJUAR (MULTI-TURN CONVERSATION MEMORY):
    I dërgon Claude Sonnet 4.6 historikun e vërtetë strukturor të pyetjeve dhe përgjigjeve,
    duke mbajtur mend çdo detaj të diskutuar më parë.
    """
    client = _get_sync_client()
    target_model = _get_forensic_model()
    full_system = f"{FORENSIC_SYSTEM_IDENTITY}\n\n{system_prompt}"

    # Përgatit listën e integruar të mesazheve me rolet përkatëse
    formatted_messages: List[Dict[str, str]] = [
        {"role": "system", "content": full_system}
    ]

    for turn in conversation_turns:
        role = turn.get("role", "user")
        # Normalizo rolet për standardin OpenAI/Claude API
        standard_role = "assistant" if role in ["assistant", "ai"] else "user"
        content = turn.get("content", "").strip()
        if content:
            formatted_messages.append({"role": standard_role, "content": content})

    kwargs: Dict[str, Any] = {
        "model": target_model,
        "messages": formatted_messages,
        "temperature": temperature,
        "max_tokens": max_tokens
    }

    retries = 3
    last_error: Optional[Exception] = None

    for attempt in range(retries):
        try:
            logger.info(f"🧠 [Forensic Memory] Dërgim i {len(formatted_messages)} kthesave bisede te {target_model}...")
            res = client.chat.completions.create(**kwargs)
            if res and res.choices and len(res.choices) > 0:
                content = getattr(res.choices[0].message, "content", "") or ""
                if content.strip():
                    return content
        except Exception as e:
            last_error = e
            logger.warning(f"⚠️ [Forensic Memory Retry {attempt + 1}] {e}")
            if attempt < retries - 1:
                time.sleep(2.0 * (attempt + 1))
                continue

    raise ForensicLLMError(f"Motori me kujtesë ({target_model}) nuk u përgjigj: {last_error}")

async def stream_forensic_llm_async(
    system_prompt: str,
    user_content: str,
    temperature: float = 0.0,
    max_tokens: int = 16384
) -> AsyncGenerator[str, None]:
    """Transmetim asinkron për streaming."""
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
        logger.error(f"❌ [Forensic LLM Stream] Gabim: {e}")
        yield f"\n\n[GABIM: Lidhja me {target_model} u ndërpre: {str(e)}]"