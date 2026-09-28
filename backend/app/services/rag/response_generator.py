# FILE: backend/app/services/rag/response_generator.py
# PHOENIX PROTOCOL - UNIFIED SUPREME RESPONSE GENERATOR V98.4
# V98.4: CHAT METRICS — Integrim i compute_chat_metrics() dhe
#        log_chat_metrics(). generate_stream() tani grumbullon output-in
#        dhe nxjerr metrika automatike pas përfundimit:
#        - response_chars, empty, truncated
#        - duration_sec, ttft_sec (time to first token)
#        - grounding (burimet e RAG-ut të përmendura në përgjigje)
#        - cost_estimate_usd, quality_score
#        Zero kosto ekstra LLM. Vetëm statistika në Python.
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

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
MAX_SINGLE_PASS_CHARS = 1_500_000


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


class ResponseGenerator:
    """
    Gjeneruesi Qendror i Përgjigjeve (V98.4):
    - Motor i vetëm me parametër opsional `model`:
        * Chat-i i klientit → FAST_SEARCH_MODEL (gpt-4o-mini)
        * Law Audit / other → default DEEP_ANALYSIS_MODEL (deepseek v4 flash)
    - Mbrojtje e plotë nga mbingarkesat (429 Auto-Retry me 3 tentativa).
    - Matje automatike e cilësisë së përgjigjes (V98.4).
    """

    def __init__(self):
        self.client = _get_async_client()

    async def _call_with_retry(
        self,
        messages: List[Dict[str, str]],
        stream: bool = True,
        max_tokens: int = 8192,
        model: Optional[str] = None,
    ):
        last_error = None
        target_model = model if model else _get_target_model()

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
    ) -> AsyncGenerator[str, None]:
        """
        V98.4: Grumbullon output-in, mat metrikat, i logon pas përfundimit.
        model: Nëse None → përdor _get_target_model() (DeepSeek V4 Flash 0731).
               Nëse jepet → përdor atë model (p.sh. FAST_SEARCH_MODEL për chat).
        """
        target_model = model if model else _get_target_model()

        # ═══════════════════════════════════════════════════════════════
        # V98.4: ACCUMULATOR PËR METRIKA
        # ═══════════════════════════════════════════════════════════════
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

            if history and isinstance(history, list):
                for h in history[-8:]:
                    r = "assistant" if h.get("role") in ["ai", "assistant"] else "user"
                    c = h.get("content") or h.get("text") or ""
                    if c and not c.startswith("[Gabim Teknik"):
                        messages.append({"role": r, "content": c})

            messages.append({"role": "user", "content": user_query})

            response = await self._call_with_retry(
                messages,
                stream=True,
                max_tokens=8192,
                model=model,
            )

            async for chunk in response:
                if chunk.choices and len(chunk.choices) > 0:
                    choice = chunk.choices[0]
                    if choice.delta and choice.delta.content:
                        delta_text = choice.delta.content

                        # V98.4: Gjurmim TTFT
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
            # ═══════════════════════════════════════════════════════════
            # V98.4: METRICS LOGGING (gjithmonë, edhe në gabim)
            # ═══════════════════════════════════════════════════════════
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
                    input_chars=len(context or "") + len(user_query) + len(system_prompt),
                    output_chars=len(full_response),
                )
                metrics["completed_normally"] = completed_normally
                if stream_error:
                    metrics["stream_error"] = stream_error[:200]
                log_chat_metrics(metrics)
            except Exception as me:
                logger.warning(f"⚠️ [CHAT METRICS] Nxjerrja e metrikave dështoi: {me}")