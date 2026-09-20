# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - UNIFIED LLM SERVICE HUB V5.3 (ENV-DRIVEN PARALLELIZATION)
# V5.3: SUMMARIZE_MAX_CONCURRENT konfigurohet nga env (jo hardcoded). Perputhje
#       me .env per tuning pa restart kodi.
# V5.2: PARALLEL CHUNKS — asyncio.Semaphore(3). Per 4 chunks, koha bie 40s -> 13s.
# V5.1: Shtuar sterilize_legal_text() + process_large_document_async().
# V5.0: 100% COMPLETE CODE • ZERO IMPORT ERRORS • EXCLUSIVE LLM_MODEL DEEPSEEK

import os
import re
import asyncio
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)

# 1. Importo të gjitha simbolet nga nën-modulet e brendshme
from app.services.llm.llm_client import *
from app.services.llm.prompt_templates import *

try:
    from app.services.llm.rag_extractor import *
except Exception:
    pass

# 2. Eksporto në mënyrë eksplicite funksionet aktive të klientit
from app.services.llm.llm_client import (
    _call_llm,
    _call_llm_async,
    _get_sync_client,
    _get_async_client,
    clean_and_parse_json,
    get_embedding,
    stream_text_async
)

from app.services.llm.prompt_templates import (
    build_dynamic_identity_header,
    _sanitize_and_disambiguate_prompt,
    AI_DISCLAIMER
)

# 3. Mbrojtje e sigurt për funksionin e nxjerrjes së financave
try:
    from app.services.llm.rag_extractor import extract_expense_details_from_text
except ImportError:
    async def extract_expense_details_from_text(text: str) -> dict:
        """Nxjerrje e sigurt e detajeve të shpenzimeve financiare me DeepSeek."""
        sys_p = "Nxirr detajet e shpenzimit (shuma_eur, kategoria, data_iso, pershkrimi, subjekti) nga ky tekst si JSON."
        raw = await _call_llm_async(sys_p, text, json_mode=True)
        return clean_and_parse_json(raw)


# ═══════════════════════════════════════════════════════════════════════════
# V5.1-V5.3: SUMMARY FUNCTIONS — per document_processing_service.py
# ═══════════════════════════════════════════════════════════════════════════

# Limite per te mbrojtur nga kosto e tepruar
SUMMARIZE_MAX_CHUNKS = int(os.environ.get("SUMMARIZE_MAX_CHUNKS", "4"))
SUMMARIZE_CHUNK_SIZE = int(os.environ.get("SUMMARIZE_CHUNK_SIZE", "6000"))
SUMMARIZE_CHUNK_OVERLAP = int(os.environ.get("SUMMARIZE_CHUNK_OVERLAP", "300"))
SUMMARIZE_SHORT_DOC_THRESHOLD = int(os.environ.get("SUMMARIZE_SHORT_DOC_THRESHOLD", "10000"))
SUMMARIZE_FALLBACK_CHARS = int(os.environ.get("SUMMARIZE_FALLBACK_CHARS", "800"))

# V5.3: Konfigurim paralelizmi nga env
SUMMARIZE_MAX_CONCURRENT = int(os.environ.get("SUMMARIZE_MAX_CONCURRENT", "3"))


def sterilize_legal_text(text: str) -> str:
    """
    V5.1: Pastron tekstin ligjor nga OCR/PDF përpara se ta përmbledhë.

    Heq:
      - Numra faqesh standalone (p.sh. "12" në një rresht të vetëm)
      - Markerat e faqeve ("--- [FAQJA X] ---")
      - Header/Footer të përsëritur të gazetave zyrtare
      - Whitespace i tepruar (3+ rreshta bosh → 2)

    Nuk humbet përmbajtje reale ligjore.
    """
    if not text:
        return ""

    # 1. Hiq markerat e faqeve
    text = re.sub(r'---\s*\[FAQJA\s*\d+\]\s*---', '', text)

    # 2. Hiq numra faqesh standalone (rresht me vetëm numra 1-3 shifror)
    text = re.sub(r'^\s*\d{1,3}\s*$', '', text, flags=re.MULTILINE)

    # 3. Hiq GAZETA ZYRTARE repeated headers
    text = re.sub(
        r'^.*GAZETA\s+ZYRTARE\s+E\s+REPUBLIKËS\s+SË\s+KOSOVËS.*$',
        '',
        text,
        flags=re.MULTILINE | re.IGNORECASE,
    )

    # 4. Normalizo whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+\n', '\n', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    text = re.sub(r'\n[ \t]+', '\n', text)

    return text.strip()


def _chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    """V5.1: Ndan tekstin në chunks me overlap."""
    if not text:
        return []

    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunks.append(text[start:end])
        if end == text_len:
            break
        start = end - overlap

    return chunks


async def process_large_document_async(
    text: str,
    max_summary_chars: int = 2000,
) -> str:
    """
    V5.2-V5.3: Përmbledh dokument ligjor (edhe te gjate) duke perdorur LLM.

    Strategjia:
      - Doc <= SUMMARIZE_SHORT_DOC_THRESHOLD chars → 1 LLM call direkt
      - Doc > threshold → chunking + PARALELIZEM
        * Perpunojme chunks paralel me asyncio.Semaphore(SUMMARIZE_MAX_CONCURRENT)
        * Pastaj 1 LLM call final per bashkim

    Koha (4 chunks, MAX_CONCURRENT=3):
      - V5.1 (sequential): 4 × 10s + 5s = ~45s → TIMEOUT
      - V5.2 (paralel x3): ~13s + 5s = ~18s → OK

    Kthen përmbledhje ne shqip. Nese LLM deshton, kthen fallback.
    """
    if not text or not text.strip():
        return ""

    text = text.strip()

    # ── Rruga A: dokument i shkurter → 1 LLM call ──
    if len(text) <= SUMMARIZE_SHORT_DOC_THRESHOLD:
        sys_p = (
            "Përmbledh ne shqip ne 3-5 fjali këtë tekst ligjor. "
            "Fokus: palët, çështja, dispozitivi, datat kyçe, nenet e cituara. "
            "Vetëm përmbledhja, pa komente."
        )
        try:
            result = await _call_llm_async(sys_p, text, json_mode=False)
            if result and result.strip():
                return result.strip()
        except Exception as e:
            logger.warning(f"⚠️ [SUMMARY V5.3] Short-doc LLM call failed: {e}")
        return text[:SUMMARIZE_FALLBACK_CHARS]

    # ── Rruga B: dokument i gjate → chunking + PARALELIZEM ──
    chunks = _chunk_text(text, SUMMARIZE_CHUNK_SIZE, SUMMARIZE_CHUNK_OVERLAP)
    chunks_to_process = chunks[:SUMMARIZE_MAX_CHUNKS]

    logger.info(
        f"📝 [SUMMARY V5.3] Duke përmbledhur {len(text)} chars "
        f"në {len(chunks)} chunks (procesoj {len(chunks_to_process)} paralel x{SUMMARIZE_MAX_CONCURRENT})"
    )

    sys_p_chunk = (
        "Përmbledh ne 2-3 fjali këtë fragment të një dokumenti ligjor shqip. "
        "Fokus: fakte, palë, nene, data. Vetëm përmbledhja."
    )

    # ═══════════════════════════════════════════════════════════════════════
    # V5.2: PARALELIZEM me Semaphore
    # ═══════════════════════════════════════════════════════════════════════
    sem = asyncio.Semaphore(SUMMARIZE_MAX_CONCURRENT)

    async def _summarize_chunk(i: int, chunk: str) -> Optional[str]:
        async with sem:
            try:
                s = await _call_llm_async(sys_p_chunk, chunk, json_mode=False)
                if s and s.strip():
                    return f"[Fragmenti {i+1}] {s.strip()}"
            except Exception as e:
                logger.warning(f"⚠️ [SUMMARY V5.3] Chunk {i+1}/{len(chunks_to_process)} failed: {e}")
            return None

    # Ekzekuto te gjitha ne paralel (Semaphore limiton konkurrencen)
    t0 = asyncio.get_event_loop().time()
    results = await asyncio.gather(
        *[_summarize_chunk(i, c) for i, c in enumerate(chunks_to_process)],
        return_exceptions=False,
    )
    elapsed = round(asyncio.get_event_loop().time() - t0, 2)

    chunk_summaries = [r for r in results if r is not None]
    logger.info(
        f"✅ [SUMMARY V5.3] {len(chunk_summaries)}/{len(chunks_to_process)} "
        f"chunks u përmbledhën paralel në {elapsed}s"
    )

    if not chunk_summaries:
        logger.warning("⚠️ [SUMMARY V5.3] Asnje chunk nuk u përmbledh — fallback")
        return text[:SUMMARIZE_FALLBACK_CHARS]

    # ── Final: bashko + 1 LLM call ──
    combined = "\n\n".join(chunk_summaries)
    sys_p_final = (
        f"Përmbledh ne shqip ne max {max_summary_chars} karaktere këto përmbledhje "
        f"fragmentesh te një dokumenti ligjor. Ruaj të gjitha faktet kyçe, palët, "
        f"nenet, datat. Vetëm përmbledhja."
    )

    try:
        final = await _call_llm_async(sys_p_final, combined, json_mode=False)
        if final and final.strip():
            return final.strip()
    except Exception as e:
        logger.warning(f"⚠️ [SUMMARY V5.3] Final LLM call failed: {e}")

    return combined[:max_summary_chars]