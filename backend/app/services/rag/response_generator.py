# FILE: backend/app/services/rag/response_generator.py
# PHOENIX PROTOCOL - UNIFIED SUPREME RESPONSE GENERATOR V98.6
# V98.6: PII REDACTION (GDPR) — INTEGRIM text_sterilization_service
#        - `_call_with_retry` aplikon redaktim PII në `messages` PARA
#          dërgimit në OpenRouter (bypass-i i llm_client u mbyll).
#        - Strategji selektive për të shmangur kosto:
#            * system  → regex-only (kontekst i madh)
#            * user    → mesazhi i fundit: full NER; historiku: regex-only
#            * assistant → pa ndryshim
#        - Parametër i ri `redact_pii: bool = True` (default ON).
# V98.5: HARDENING —
#        - `MAX_SINGLE_PASS_CHARS` 1_500_000 → 300_000. Vlera e vjetër
#          (≈600k tokens) ishte mbi context window e çdo modeli aktual
#          → 400 Invalid Request në API. 300k chars ≈ 120k tokens — brenda
#          limitit të DeepSeek V4 Flash (~128k) me margin të sigurt.
#        - Guard për `user_query` bosh/jo-string → skip API call, yield
#          mesazh kuptimplotë (përpara: 400 i fshehur).
#        - Guard për `history` me entries jo-dict → AttributeError i
#          parandaluar.
# V98.4: CHAT METRICS — compute_chat_metrics() + log_chat_metrics().
# V98.3: MODEL MIGRATION.
# V98.2: Hequr 4 dead items.
# V98.1: CLAUDE OVERRIDE REMOVED.
# V98.0: Shtuar parametër opsional `model`.

import logging
import asyncio
import os
import time
from typing import Optional, List, Dict, Any, AsyncGenerator

from app.core.config import settings

from app.services.llm.llm_client import (
    _get_async_client
)
from app.services.document_review.quality_metrics import (
    compute_chat_metrics,
    log_chat_metrics,
)
from app.services.text_sterilization_service import sterilize_text_for_llm

logger = logging.getLogger(__name__)

MAX_RETRIES = 3

# V98.5: 1.5M → 300k (≈120k tokens). Mbi këtë, API hedh 400.
MAX_SINGLE_PASS_CHARS = 300_000

# V98.6: Default i redaktimit PII për chat RAG.
DEFAULT_REDACT_PII = True


def _get_target_model() -> str:
    """
    V98.3: Lexon VETËM modelin e vetëm të unifikuar nga settings.LLM_MODEL.
    """
    model = (
        getattr(settings, "LLM_MODEL", None)
        or os.getenv("LLM_MODEL", "")
        or "deepseek/deepseek-v4-flash-0731"
    )
    return model


def _get_provider_routing_payload() -> Dict[str, Any]:
    """Lejon të gjithë ofruesit zyrtarë me failover automatik."""
    return {
        "provider": {
            "allow_fallbacks": True
        }
    }


def _redact_messages_for_llm(
    messages: List[Dict[str, str]]
) -> List[Dict[str, str]]:
    """
    V98.6: Redakton PII në `messages` përpara dërgimit te LLM.

    Strategji (minimizon koston e NER):
    - system    → regex-only (kontekst i madh; NER do ishte i kushtueshëm)
    - user      → mesazhi i fundit: full NER; historiku: regex-only
    - assistant → pa ndryshim (output i mëparshëm AI, tashmë i pastër)

    Fail-safe: në çdo exception, kthen tekstin origjinal (pa redaktim) —
    nuk bllokon chat-in, vetëm regjistron.
    """
    if not messages:
        return messages

    # Gjej indeksin e user-it të fundit (=pyetja aktuale)
    last_user_idx = -1
    for i, m in enumerate(messages):
        if isinstance(m, dict) and m.get("role") == "user":
            last_user_idx = i

    redacted: List[Dict[str, str]] = []
    redacted_count = 0

    for i, m in enumerate(messages):
        if not isinstance(m, dict):
            redacted.append(m)
            continue

        role = m.get("role", "")
        content = m.get("content", "")

        if not isinstance(content, str) or not content:
            redacted.append(m)
            continue

        try:
            if role == "system":
                new_content = sterilize_text_for_llm(
                    content, redact_names=False
                )
            elif role == "user":
                # Vetëm mesazhi i fundit i user-it merr NER të plotë
                use_ner = (i == last_user_idx)
                new_content = sterilize_text_for_llm(
                    content, redact_names=use_ner
                )
            else:
                new_content = content
        except Exception as e:
            logger.warning(
                f"⚠️ [PII Redaction V98.6] Dështoi për rolin '{role}' "
                f"(indeksi {i}): {e}"
            )
            new_content = content

        if new_content != content:
            redacted_count += 1
            redacted.append({**m, "content": new_content})
        else:
            redacted.append(m)

    if redacted_count > 0:
        logger.info(
            f"🔒 [PII Redaction V98.6] {redacted_count}/{len(messages)} "
            f"mesazhe u redaktuan."
        )

    return redacted


class ResponseGenerator:
    """
    Gjeneruesi Qendror i Përgjigjeve (V98.6):
    - Motor i vetëm me parametër opsional `model`:
        * Chat-i i klientit → FAST_SEARCH_MODEL (gpt-4o-mini)
        * Law Audit / other → default DEEP_ANALYSIS_MODEL (deepseek v4 flash)
    - Mbrojtje e plotë nga mbingarkesat (429 Auto-Retry me 3 tentativa).
    - Matje automatike e cilësisë së përgjigjes (V98.4).
    - Guard-e për input bosh / malformed (V98.5).
    - PII redaction (GDPR) në LLM boundary (V98.6).
    """

    def __init__(self):
        self.client = _get_async_client()

    async def _call_with_retry(
        self,
        messages: List[Dict[str, str]],
        stream: bool = True,
        max_tokens: int = 8192,
        model: Optional[str] = None,
        redact_pii: bool = DEFAULT_REDACT_PII,
    ):
        last_error = None
        target_model = model if model else _get_target_model()

        # V98.6: PII REDACTION — hapi i fundit para dërgimit në OpenRouter
        if redact_pii:
            messages = _redact_messages_for_llm(messages)

        kwargs: Dict[str, Any] = {
            "model": target_model,
            "messages": messages,
            "temperature": 0.0,
            "stream": stream,
            "max_tokens": max_tokens,
            "extra_body": _get_provider_routing_payload()
        }

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"⚖️ [ResponseGenerator] Ekzekutim në {target_model} (Përpjekja {attempt})...")
                response = await self.client.chat.completions.create(**kwargs)
                return response
            except Exception as e:
                last_error = e
                err_str = str(e).lower()
                if "429" in err_str or "rate limit" in err_str:
                    logger.warning(f"⚠️ [Rate Limit 429] në {target_model}. Po pres {2 * attempt}s...")
                    await asyncio.sleep(2.0 * attempt)
                    continue
                logger.warning(f"⚠️ Dështoi përpjekja {attempt} në {target_model}: {e}")
                await asyncio.sleep(1.5)

        raise last_error if last_error else Exception("Shërbimi është përkohësisht i ngarkuar nga fluksi.")

    async def generate_stream(
        self,
        system_prompt: str,
        user_query: str,
        context: str = "",
        history: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None,
        redact_pii: bool = DEFAULT_REDACT_PII,
    ) -> AsyncGenerator[str, None]:
        """
        V98.6: Redaktim PII para streaming-ut. Grumbullon output-in, mat
        metrikat, i logon pas përfundimit.
        Guard-e për input bosh / malformed.
        """
        target_model = model if model else _get_target_model()

        # ═══════════════════════════════════════════════════════════════
        # V98.5: GUARD — user_query bosh → skip API call
        # ═══════════════════════════════════════════════════════════════
        if not user_query or not isinstance(user_query, str) or not user_query.strip():
            logger.warning("⚠️ [ResponseGenerator V98.5] user_query bosh ose jo-string — skip API call.")
            error_msg = "[Gabim: Pyetja është bosh ose e pavlefshme.]"
            yield error_msg
            return

        accumulated_chunks: List[str] = []
        start_time = time.time()
        first_token_time: Optional[float] = None
        stream_error: Optional[str] = None
        completed_normally = False

        try:
            full_context_content = f"{context}\n\n{system_prompt}" if context else system_prompt

            enhanced_system_prompt = f"""
{full_context_content}

RREGULLAT E KONSULENCËS DHE DOKTRINËS SË KOSOVËS:
1. Përgjigju VETËM në gjuhë standarde juridike shqipe të Republikës së Kosovës.
2. Dëgjoni me kujdes dhe bashkëpunoni natyrshëm me përdoruesin pa shabllone artificiale.
3. Bazo çdo zgjidhje në ligjet pozitive dhe shkresat reale të fashikullit.
"""
            messages = [{"role": "system", "content": enhanced_system_prompt[:MAX_SINGLE_PASS_CHARS]}]

            # V98.5: Guard për history entries jo-dict
            if history and isinstance(history, list):
                for h in history[-8:]:
                    if not isinstance(h, dict):
                        continue
                    r = "assistant" if h.get("role") in ["ai", "assistant"] else "user"
                    c = h.get("content") or h.get("text") or ""
                    if c and not c.startswith("[Gabim Teknik"):
                        messages.append({"role": r, "content": c})

            messages.append({"role": "user", "content": user_query})

            # V98.6: redact_pii kalon në _call_with_retry
            response = await self._call_with_retry(
                messages,
                stream=True,
                max_tokens=8192,
                model=model,
                redact_pii=redact_pii,
            )

            async for chunk in response:
                if chunk.choices and len(chunk.choices) > 0:
                    choice = chunk.choices[0]
                    if choice.delta and choice.delta.content:
                        delta_text = choice.delta.content

                        if first_token_time is None:
                            first_token_time = time.time()

                        accumulated_chunks.append(delta_text)
                        yield delta_text

            completed_normally = True

        except Exception as e:
            stream_error = str(e)
            logger.error(f"❌ Gjenerimi dështoi pas të gjitha përpjekjeve në {target_model}: {e}")
            error_msg = "\n\n[Shërbimi është përkohësisht i ngarkuar nga fluksi i lartë. Ju lutem provoni përsëri pas pak sekondash.]"
            accumulated_chunks.append(error_msg)
            yield error_msg

        finally:
            duration = time.time() - start_time
            ttft = (first_token_time - start_time) if first_token_time else None
            full_response = "".join(accumulated_chunks)

            try:
                metrics = compute_chat_metrics(
                    response_text=full_response,
                    context=context or "",
                    duration_sec=duration,
                    ttft_sec=ttft,
                    model=target_model,
                    input_chars=len(context or "") + len(user_query or "") + len(system_prompt or ""),
                    output_chars=len(full_response),
                )
                metrics["completed_normally"] = completed_normally
                if stream_error:
                    metrics["stream_error"] = stream_error[:200]
                log_chat_metrics(metrics)
            except Exception as me:
                logger.warning(f"⚠️ [CHAT METRICS] Nxjerrja e metrikave dështoi: {me}")