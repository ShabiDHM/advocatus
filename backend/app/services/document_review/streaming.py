# FILE: backend/app/services/document_review/streaming.py
# PHOENIX PROTOCOL - STREAMING V1.3
# V1.3: ROLE CONFLICT FIX — Hequr identiteti global "Auditues Ligjor i
#       Gjykatës Supreme" dhe blloku "ROLI YT" nga wrapper-i. Identiteti
#       tani vjen EKSKLUZIVISHT nga section_cfg['prompt'] (secila section
#       ka rolin e vet: Partner, Verifikues, Analist, Revizor, Strateg).
#       Zgjidh konfliktin e dyfishtë ku LLM merrte dy role kontradiktore.
#       Gjithashtu heq "NUK justifikon" që binte ndesh me "Arsyetimi"
#       në seksionin "readiness".
# V1.2: System prompt i ri "Auditues Ligjor i Gjykatës Supreme" (jo "Revizor").
#       Udhëzime eksplicite: "MOS përmbledh — AUDITO".
# V1.1: max_tokens dinamik (jo 8192 hardcoded).
# V1.0: Ekstraktuar nga document_review_service.py V4.2.

import time
import logging
from typing import Dict, Any, Optional, Callable, Generator

from app.services.llm.llm_client import (
    _call_llm,
    _get_sync_client,
    _prepare_system_prompt,
    _sanitize_and_disambiguate_prompt,
    _get_provider_routing_payload,
    _get_api_key,
    DEEP_ANALYSIS_MODEL,
)

from .constants import STREAM_BATCH_CHARS, STREAM_BATCH_INTERVAL_SEC

logger = logging.getLogger(__name__)

# Fallback nëse section_cfg nuk ka max_tokens të përcaktuar
DEFAULT_MAX_TOKENS = 3000


# ═══════════════════════════════════════════════════════════════════════════
# LOW-LEVEL STREAM
# ═══════════════════════════════════════════════════════════════════════════

def stream_section_sync(
    system_prompt: str,
    user_content: str,
    temperature: float = 0.1,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> Generator[str, None, None]:
    """Streaming sinkron për një section."""
    if not _get_api_key():
        return
    full_sys = _prepare_system_prompt(system_prompt)
    sanitized = _sanitize_and_disambiguate_prompt(user_content)
    client = _get_sync_client()
    try:
        stream = client.chat.completions.create(
            model=DEEP_ANALYSIS_MODEL,
            messages=[
                {"role": "system", "content": full_sys},
                {"role": "user", "content": sanitized},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
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
        logger.error(f"❌ [DOC_REVIEW] Streaming error: {e}")
        raise


# ═══════════════════════════════════════════════════════════════════════════
# SECTION STREAMING — V1.3 (identitet per-section)
# ═══════════════════════════════════════════════════════════════════════════

def synthesize_section_streaming(
    section_key: str,
    section_cfg: Dict[str, Any],
    verified_context: str,
    file_name: str,
    document_type: str,
    stream_callback: Optional[Callable[[str, str], None]] = None,
) -> str:
    """
    V1.3: Streaming i një section.

    Wrapper-i jep VETËM kontekstin e dokumentit + formatimin.
    Identiteti dhe rregullat specifike vijnë nga section_cfg['prompt'].
    """
    section_max_tokens = section_cfg.get("max_tokens", DEFAULT_MAX_TOKENS)
    section_title = section_cfg.get("title", section_key)

    system_prompt = f"""DOKUMENTI NË AUDITIM: {file_name}
LLOJI I DOKUMENTIT: {document_type}

{section_cfg['prompt']}

FORMATIMI:
- Përdor markdown me tituj.
- Referenca specifike (neni, ligji, data, ICD).
- Shkruaj në shqip juridike standarde.
- Citate direkte me thonjëza.
- Lista të numërtuara për pika.
"""

    user_content = f"""FAKTET E VERIFIKUARA TË DOKUMENTIT:

{verified_context}

───────────────────────────────────────────────────────
DETYRA JOTE: Harto seksionin "{section_title}".

MOS përsërit faktet — INTERPRETOJI dhe NXIRR përfundime.
MOS përmbledh dokumentin — AUDITOJE atë.
"""

    logger.info(
        f"🎬 [STREAM {section_key}] max_tokens={section_max_tokens}, "
        f"sys={len(system_prompt)} chars, user={len(user_content)} chars"
    )

    accumulated = ""
    buffer = ""
    last_emit = time.time()
    stream_succeeded = False
    section_start = time.time()

    try:
        for chunk in stream_section_sync(
            system_prompt,
            user_content,
            temperature=0.1,
            max_tokens=section_max_tokens,
        ):
            stream_succeeded = True
            accumulated += chunk
            buffer += chunk
            now = time.time()
            if (
                len(buffer) >= STREAM_BATCH_CHARS
                or (now - last_emit) >= STREAM_BATCH_INTERVAL_SEC
            ):
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

        elapsed = round(time.time() - section_start, 2)
        logger.info(
            f"✅ [STREAM {section_key}] {elapsed}s, "
            f"{len(accumulated)} chars, max_tokens={section_max_tokens}"
        )
        return accumulated

    except Exception as e:
        logger.warning(f"⚠️ Streaming failed for {section_key}: {e}")
        if not stream_succeeded and not accumulated:
            try:
                logger.info(f"🔄 [STREAM {section_key}] Fallback në non-streaming")
                raw = _call_llm(
                    system_prompt=system_prompt,
                    user_content=user_content,
                    json_mode=False,
                    temperature=0.1,
                    model=DEEP_ANALYSIS_MODEL,
                )
                accumulated = raw or ""
                if stream_callback and accumulated:
                    try:
                        stream_callback(section_key, accumulated)
                    except Exception:
                        pass
                elapsed = round(time.time() - section_start, 2)
                logger.info(
                    f"✅ [STREAM {section_key}] (fallback) {elapsed}s, "
                    f"{len(accumulated)} chars"
                )
            except Exception as e2:
                logger.error(f"❌ Fallback failed: {e2}")
                raise
        return accumulated