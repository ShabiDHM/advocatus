# FILE: backend/app/services/synthesis/streaming.py
# PHOENIX PROTOCOL - STREAMING V1.0
# Ekstraktuar nga synthesis_service.py V3.8 — ZERO ndryshim funksional.

import time
import logging
from typing import Any, Dict, Optional, Callable, Generator

from app.services.llm.llm_client import (
    _call_llm,
    _get_sync_client,
    _prepare_system_prompt,
    _sanitize_and_disambiguate_prompt,
    _get_provider_routing_payload,
    _get_api_key,
    FAST_SEARCH_MODEL,
)

from .constants import STREAM_BATCH_CHARS, STREAM_BATCH_INTERVAL_SEC

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# LOW-LEVEL STREAM
# ═══════════════════════════════════════════════════════════════════════════

def stream_section_sync(
    system_prompt: str,
    user_content: str,
    temperature: float = 0.1,
) -> Generator[str, None, None]:
    if not _get_api_key():
        return
    full_sys = _prepare_system_prompt(system_prompt)
    sanitized = _sanitize_and_disambiguate_prompt(user_content)
    client = _get_sync_client()
    try:
        stream = client.chat.completions.create(
            model=FAST_SEARCH_MODEL,
            messages=[
                {"role": "system", "content": full_sys},
                {"role": "user", "content": sanitized},
            ],
            temperature=temperature,
            max_tokens=8192,
            stream=True,
            extra_body=_get_provider_routing_payload(),
        )
        for chunk in stream:
            if not chunk or not hasattr(chunk, "choices") or not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta and getattr(delta, "content", None):
                yield delta.content
    except Exception as e:
        logger.error(f"❌ [SYNTHESIS] Sync streaming error: {e}")
        raise


# ═══════════════════════════════════════════════════════════════════════════
# SECTION STREAMING (with fallback)
# ═══════════════════════════════════════════════════════════════════════════

def synthesize_section_streaming(
    section_key: str,
    section_cfg: Dict[str, Any],
    digest: str,
    case: Dict[str, Any],
    stream_callback: Optional[Callable[[str, str], None]] = None,
) -> str:
    case_title = case.get("title") or case.get("case_name") or "Lënda"
    client_name = case.get("client_name") or "Klienti"

    system_prompt = f"""Ti je "Juristi AI - Asistenti Ligjor i Kosovës".

LËNDA: {case_title}
KLIENTI: {client_name}

{section_cfg['prompt']}

FORMATIMI:
- Përdor markdown me tituj (##, ###).
- Përfshi referenca specifike.
- Shkruaj në shqip standarde juridike.
- Mos shpik — bazohu VETËM në digest.
"""

    user_content = f"""DIGEST I LËNDËS:

{digest}

───────────────────────────────────────────────────────

DETYRA: Harto seksionin "{section_cfg['title']}"."""

    accumulated = ""
    buffer = ""
    last_emit = time.time()
    stream_succeeded = False

    try:
        for chunk in stream_section_sync(system_prompt, user_content, temperature=0.1):
            stream_succeeded = True
            accumulated += chunk
            buffer += chunk
            now = time.time()
            if len(buffer) >= STREAM_BATCH_CHARS or (now - last_emit) >= STREAM_BATCH_INTERVAL_SEC:
                if stream_callback and buffer:
                    try:
                        stream_callback(section_key, buffer)
                    except Exception:
                        pass
                buffer = ""
                last_emit = now
        if buffer and stream_callback:
            try:
                stream_callback(section_key, buffer)
            except Exception:
                pass
        return accumulated
    except Exception as e:
        logger.warning(f"⚠️ [SYNTHESIS] Streaming failed for {section_key}: {e}")
        if not stream_succeeded and not accumulated:
            try:
                raw = _call_llm(
                    system_prompt=system_prompt,
                    user_content=user_content,
                    json_mode=False,
                    temperature=0.1,
                    model=FAST_SEARCH_MODEL,
                )
                accumulated = raw or ""
                if stream_callback and accumulated:
                    try:
                        stream_callback(section_key, accumulated)
                    except Exception:
                        pass
            except Exception as e2:
                logger.error(f"❌ [SYNTHESIS] Fallback also failed: {e2}")
                raise
        return accumulated