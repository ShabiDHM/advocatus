# FILE: backend/app/services/document_review/quality_metrics.py
# PHOENIX PROTOCOL - QUALITY METRICS V1.3
# V1.3: ARTICLE REGEX — Zgjeruar `_ANCHOR_ARTICLE_RE` për të pranuar rasat
#       gramatikore të shqipes (Neni, Nenit, Nenin, Nenët, Nenet, Nene, Nen).
#       Pa këtë, "Nenit 145" nuk nxirej si anchor → grounding detection
#       dështonte në T6 (response përdor "Nenit", jo "Neni").
# V1.2: CHAT METRICS — Shtuar compute_chat_metrics() dhe log_chat_metrics()
#       për të matur chat-in RAG. Zero ekstra kosto LLM.
#       Metrika: response_chars, empty, truncated, duration, ttft,
#       grounding_hits/score (burimet e përmendura), cost_estimate, quality.
# V1.1: FIX T2.
# V1.0: Versioni fillestar.

import logging
import re

from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# KONSTANTE
# ═══════════════════════════════════════════════════════════════════════════

# DeepSeek V4 Flash 0731 — çmimet për 1M tokens (Together AI)
COST_INPUT_PER_M = 0.14
COST_OUTPUT_PER_M = 0.28

# GPT-4o mini (për chat FAST_SEARCH)
COST_GPT4O_MINI_INPUT_PER_M = 0.15
COST_GPT4O_MINI_OUTPUT_PER_M = 0.60

# Shqip: ~2.5 karaktere për token (mesatare empirike)
CHARS_PER_TOKEN = 2.5

# Pragje
MIN_CONTENT_CHARS = 100
TRUNCATION_MIN_CHARS = 200
TRUNCATION_MIN_LAST_LINE_WORDS = 4

# Karaktere që tregojnë fund të saktë
PROPER_ENDINGS = {
    '.', '!', '?', ')', ']', '"', '»', '”', ':', '—',
    ';', ',', '>', '-', '\n',
}

NON_TRUNCATION_PREFIXES = ('#', '*', '-', '•', '>', '▪', '◆', '◎', '○', '⏺')


# ═══════════════════════════════════════════════════════════════════════════
# DETEKTORË (të përbashkët)
# ═══════════════════════════════════════════════════════════════════════════

def _is_empty(content: str) -> bool:
    return not content or len(content.strip()) < MIN_CONTENT_CHARS


def _is_truncated(content: str) -> bool:
    if not content or len(content.strip()) < TRUNCATION_MIN_CHARS:
        return False

    stripped = content.rstrip()
    if not stripped:
        return False

    last_char = stripped[-1]
    if last_char in PROPER_ENDINGS:
        return False

    last_line = stripped.split('\n')[-1].strip()
    if not last_line:
        return False

    for prefix in NON_TRUNCATION_PREFIXES:
        if last_line.startswith(prefix):
            return False

    words = last_line.split()
    if len(words) < TRUNCATION_MIN_LAST_LINE_WORDS:
        return False

    return True


def _has_error(sec: Dict[str, Any]) -> bool:
    return bool(sec.get("error"))


def _is_blocked(sec: Dict[str, Any]) -> bool:
    return bool(sec.get("_blocked_by_hallucination"))


# ═══════════════════════════════════════════════════════════════════════════
# COST ESTIMATE (për raportet)
# ═══════════════════════════════════════════════════════════════════════════

def _estimate_tokens_from_chars(chars: int) -> int:
    return max(1, int(chars / CHARS_PER_TOKEN))


def _estimate_cost(
    section_stats: Dict[str, Any],
) -> Tuple[float, int, int]:
    total_input_chars = 0
    total_output_chars = 0

    for stat in section_stats.values():
        if not isinstance(stat, dict):
            continue
        total_input_chars += int(stat.get("context_chars", 0) or 0)
        total_output_chars += int(stat.get("content_length", 0) or 0)

    in_tokens = _estimate_tokens_from_chars(total_input_chars)
    out_tokens = _estimate_tokens_from_chars(total_output_chars)

    cost = (
        (in_tokens / 1_000_000) * COST_INPUT_PER_M
        + (out_tokens / 1_000_000) * COST_OUTPUT_PER_M
    )

    return round(cost, 4), in_tokens, out_tokens


# ═══════════════════════════════════════════════════════════════════════════
# QUALITY SCORE (për raportet)
# ═══════════════════════════════════════════════════════════════════════════

def _compute_quality_score(
    total: int,
    empty: int,
    truncated: int,
    blocked: int,
    errors: int,
) -> int:
    if total == 0:
        return 0

    score = 100
    score -= errors * 25
    score -= blocked * 20
    score -= empty * 10
    score -= truncated * 5

    return max(0, min(100, score))


# ═══════════════════════════════════════════════════════════════════════════
# API KRYESOR — RAPORTET
# ═══════════════════════════════════════════════════════════════════════════

def compute_quality_metrics(
    sections: Dict[str, Any],
    section_stats: Optional[Dict[str, Any]] = None,
    hallucination_report: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    section_stats = section_stats or {}

    total = 0
    empty = 0
    truncated = 0
    blocked = 0
    errors = 0

    empty_list: List[str] = []
    truncated_list: List[str] = []
    blocked_list: List[str] = []
    error_list: List[str] = []
    content_lengths: List[int] = []

    for key, sec in sections.items():
        total += 1
        if not isinstance(sec, dict):
            errors += 1
            error_list.append(key)
            continue

        content = sec.get("content") or ""
        content_len = len(content)
        content_lengths.append(content_len)

        if _has_error(sec):
            errors += 1
            error_list.append(key)
            continue

        if _is_blocked(sec):
            blocked += 1
            blocked_list.append(key)
            continue

        if _is_empty(content):
            empty += 1
            empty_list.append(key)
            continue

        if _is_truncated(content):
            truncated += 1
            truncated_list.append(key)

    avg_chars = int(sum(content_lengths) / len(content_lengths)) if content_lengths else 0
    min_chars = min(content_lengths) if content_lengths else 0
    max_chars = max(content_lengths) if content_lengths else 0

    quality_score = _compute_quality_score(
        total=total,
        empty=empty,
        truncated=truncated,
        blocked=blocked,
        errors=errors,
    )

    cost_usd, in_tokens, out_tokens = _estimate_cost(section_stats)

    return {
        "sections_total": total,
        "sections_with_content": total - empty - blocked - errors,
        "sections_empty": empty,
        "sections_truncated": truncated,
        "sections_blocked": blocked,
        "sections_error": errors,
        "avg_content_chars": avg_chars,
        "min_content_chars": min_chars,
        "max_content_chars": max_chars,
        "empty_sections": empty_list,
        "truncated_sections": truncated_list,
        "blocked_sections": blocked_list,
        "error_sections": error_list,
        "quality_score": quality_score,
        "cost_estimate_usd": cost_usd,
        "input_tokens_est": in_tokens,
        "output_tokens_est": out_tokens,
        "total_content_chars": sum(content_lengths),
    }


def log_quality_metrics(metrics: Dict[str, Any]) -> None:
    logger.info("=" * 70)
    logger.info("📊 [QUALITY METRICS]")
    logger.info("=" * 70)
    logger.info(f"   sections_total:        {metrics['sections_total']}")
    logger.info(
        f"   sections_with_content: {metrics['sections_with_content']}"
        f" ({_pct(metrics['sections_with_content'], metrics['sections_total'])})"
    )
    logger.info(f"   sections_empty:        {metrics['sections_empty']}")
    logger.info(f"   sections_truncated:    {metrics['sections_truncated']}")
    logger.info(f"   sections_blocked:      {metrics['sections_blocked']}")
    logger.info(f"   sections_error:        {metrics['sections_error']}")
    logger.info(f"   avg_content_chars:     {metrics['avg_content_chars']}")
    logger.info(
        f"   min/max chars:         {metrics['min_content_chars']}/{metrics['max_content_chars']}"
    )
    logger.info(f"   total_content_chars:   {metrics['total_content_chars']}")
    logger.info(f"   quality_score:         {metrics['quality_score']}/100")
    logger.info(
        f"   cost_estimate:         ${metrics['cost_estimate_usd']} "
        f"(in={metrics['input_tokens_est']}t, out={metrics['output_tokens_est']}t)"
    )

    if metrics["empty_sections"]:
        logger.info(f"   ⚠️ empty:     {metrics['empty_sections']}")
    if metrics["truncated_sections"]:
        logger.info(f"   ⚠️ truncated: {metrics['truncated_sections']}")
    if metrics["blocked_sections"]:
        logger.info(f"   🛡️ blocked:   {metrics['blocked_sections']}")
    if metrics["error_sections"]:
        logger.info(f"   ❌ error:     {metrics['error_sections']}")

    logger.info("=" * 70)


def _pct(part: int, total: int) -> str:
    if total == 0:
        return "0%"
    return f"{int(round(100 * part / total))}%"


# ═══════════════════════════════════════════════════════════════════════════
# V1.2: CHAT METRICS
# ═══════════════════════════════════════════════════════════════════════════

# Regex lokalë (nuk varen nga patterns.py) — për grounding detection
_ANCHOR_CASE_RE = re.compile(
    r'\b([A-Z]{1,6})\.?\s*[Nn]r\.?\s*(\d+[\w\/\.\-]*)',
    re.UNICODE,
)
_ANCHOR_LAW_RE = re.compile(
    r'\b(\d{2,4})\s*[\/\-]\s*L\s*[\-–]?\s*(\d{1,4})\b',
    re.IGNORECASE,
)
_ANCHOR_LEGACY_LAW_RE = re.compile(r'\b(\d{4})\s*[\/\-]\s*(\d{1,4})\b')

# V1.3: rasat gramatikore të shqipes (Neni, Nenit, Nenin, Nenët, Nenet, Nene, Nen)
_ANCHOR_ARTICLE_RE = re.compile(
    r'\bNen(?:i|it|in|ët|et|e)?\s+(\d+(?:[\.\/]\d+)*)',
    re.IGNORECASE | re.UNICODE,
)


def _extract_anchors(text: str) -> Set[str]:
    """
    Nxjerr 'anchor'-a (numra lënde, ligje, nene) nga teksti.
    Kthen set me prefikse të tipit: 'case:C.nr.385/2024', 'law:06/L-074', 'art:145'
    """
    if not text:
        return set()

    anchors: Set[str] = set()

    # Case numbers
    for m in _ANCHOR_CASE_RE.finditer(text):
        prefix = m.group(1).upper()
        num = m.group(2).rstrip(".,;: ")
        if num:
            anchors.add(f"case:{prefix}.nr.{num}")

    # Law numbers format XX/L-YYY
    for m in _ANCHOR_LAW_RE.finditer(text):
        p1, p2 = m.group(1), m.group(2)
        anchors.add(f"law:{p1}/L-{p2}")

    # Legacy law numbers (2004/32, etj.)
    for m in _ANCHOR_LEGACY_LAW_RE.finditer(text):
        p1, p2 = m.group(1), m.group(2)
        if len(p1) == 4 and int(p1) < 2100 and int(p1) > 1900:
            anchors.add(f"law:{p1}/{p2}")

    # Article numbers
    for m in _ANCHOR_ARTICLE_RE.finditer(text):
        anchors.add(f"art:{m.group(1)}")

    return anchors


def compute_chat_metrics(
    response_text: str,
    context: str = "",
    duration_sec: float = 0.0,
    ttft_sec: Optional[float] = None,
    model: str = "",
    input_chars: Optional[int] = None,
    output_chars: Optional[int] = None,
) -> Dict[str, Any]:
    """
    V1.2: Matjet për një përgjigje chat-i.

    Argumentet:
        response_text:  Përgjigjja e plotë e LLM.
        context:        Konteksti RAG (për grounding detection).
        duration_sec:   Koha totale e gjenerimit.
        ttft_sec:       Time to first token (sekonda).
        model:          Emri i modelit (për kosto).
        input_chars:    Sa karaktere u dërguan në LLM (nëse dihet).
        output_chars:   Sa karaktere u kthyen (default: len(response_text)).

    Kthen: dict me metrika.
    """
    if output_chars is None:
        output_chars = len(response_text or "")
    if input_chars is None:
        input_chars = len(context or "")

    is_empty = not response_text or len(response_text.strip()) < 20
    is_truncated = _is_truncated(response_text or "")

    # Grounding detection
    context_anchors = _extract_anchors(context)
    response_anchors = _extract_anchors(response_text or "")
    grounding_hits_set = context_anchors & response_anchors
    grounding_hits = len(grounding_hits_set)
    total_anchors = len(context_anchors)

    if total_anchors > 0:
        grounding_score = round(grounding_hits / total_anchors, 3)
    else:
        grounding_score = None

    # Kosto
    in_tokens = _estimate_tokens_from_chars(input_chars)
    out_tokens = _estimate_tokens_from_chars(output_chars)

    is_gpt4o_mini = "gpt-4o-mini" in (model or "").lower()
    if is_gpt4o_mini:
        cost = (
            (in_tokens / 1_000_000) * COST_GPT4O_MINI_INPUT_PER_M
            + (out_tokens / 1_000_000) * COST_GPT4O_MINI_OUTPUT_PER_M
        )
    else:
        cost = (
            (in_tokens / 1_000_000) * COST_INPUT_PER_M
            + (out_tokens / 1_000_000) * COST_OUTPUT_PER_M
        )
    cost = round(cost, 5)

    # Quality score (0-100)
    quality_score = 100
    if is_empty:
        quality_score -= 60
    if is_truncated:
        quality_score -= 15
    if grounding_score is not None and grounding_score < 0.1 and total_anchors >= 3:
        quality_score -= 10
    quality_score = max(0, min(100, quality_score))

    return {
        "response_chars": len(response_text or ""),
        "response_empty": is_empty,
        "response_truncated": is_truncated,
        "duration_sec": round(duration_sec, 2),
        "ttft_sec": round(ttft_sec, 3) if ttft_sec is not None else None,
        "model": model or "(default)",
        "input_chars": input_chars,
        "output_chars": output_chars,
        "input_tokens_est": in_tokens,
        "output_tokens_est": out_tokens,
        "cost_estimate_usd": cost,
        "context_anchors_total": total_anchors,
        "grounding_hits": grounding_hits,
        "grounding_score": grounding_score,
        "grounding_anchors": sorted(grounding_hits_set)[:10],
        "quality_score": quality_score,
    }


def log_chat_metrics(metrics: Dict[str, Any]) -> None:
    """Log i formatuar për chat metrics."""
    logger.info("=" * 70)
    logger.info("💬 [CHAT METRICS]")
    logger.info("=" * 70)
    logger.info(f"   model:                 {metrics['model']}")
    logger.info(f"   response_chars:        {metrics['response_chars']}")
    logger.info(f"   response_empty:        {metrics['response_empty']}")
    logger.info(f"   response_truncated:    {metrics['response_truncated']}")
    logger.info(f"   duration_sec:          {metrics['duration_sec']}s")

    if metrics.get("ttft_sec") is not None:
        logger.info(f"   ttft_sec:              {metrics['ttft_sec']}s")

    logger.info(
        f"   tokens:                "
        f"in={metrics['input_tokens_est']}t / out={metrics['output_tokens_est']}t"
    )
    logger.info(f"   cost_estimate:         ${metrics['cost_estimate_usd']}")

    gs = metrics.get("grounding_score")
    if gs is not None:
        logger.info(
            f"   grounding:             {metrics['grounding_hits']}/"
            f"{metrics['context_anchors_total']} "
            f"(score={gs})"
        )
    else:
        logger.info(
            f"   grounding:             (kontekst bosh — nuk llogaritet)"
        )

    logger.info(f"   quality_score:         {metrics['quality_score']}/100")

    if metrics.get("grounding_anchors"):
        logger.info(f"   anchors përmendur:     {metrics['grounding_anchors']}")

    logger.info("=" * 70)


# ═══════════════════════════════════════════════════════════════════════════
# SELF-TEST
# ═══════════════════════════════════════════════════════════════════════════

def _self_test() -> None:
    """T1-T5: report metrics. T6-T10: chat metrics."""
    # T1: Normal
    sec_ok = "Ky është tekst i plotë. Ka disa fjali. Dhe mbaron me pikë."
    assert not _is_truncated(sec_ok), "T1 failed"

    # T2: Truncated (> 200 chars)
    sec_trunc = (
        "Ky është një paragraf i gjatë që fillon mirë dhe vazhdon "
        "me shumë detaje të rëndësishme për analizën e thelluar "
        "të rastit dhe pastaj papritmas ndërpritet në mes të një "
        "fjalie pa përfunduar mendimin dhe pa vendosur pikë "
        "në fund të tekstit sikurse ndodh shpesh me modelet që "
        "harxhojnë max_tokens dhe mbeten pa hapësirë për output"
    )
    assert _is_truncated(sec_trunc), "T2 failed"

    # T3: Morfologji
    sec_dia = "Analiza e thelluar përfundon me rezultatin përfundimtar."
    assert not _is_truncated(sec_dia), "T3 failed"

    # T4: Bullet list
    sec_bullet = (
        "- Pika e parë e listës së gjatë me shumë detaje që vazhdon\n"
        "- Pika e dytë me më shumë detaje dhe kontekst të gjerë"
    )
    assert not _is_truncated(sec_bullet), "T4 failed"

    # T5: Report metrics
    test_sections = {
        "ok": {"content": "A" * 500 + ". Fund i saktë."},
        "empty": {"content": ""},
        "trunc": {"content": "B" * 300 + " fund pa pike"},
        "blocked": {"content": "X", "_blocked_by_hallucination": True},
        "error": {"content": "", "error": "test"},
    }
    test_stats = {
        "ok": {"context_chars": 1000, "content_length": 500},
        "empty": {"context_chars": 500, "content_length": 0},
    }
    metrics = compute_quality_metrics(test_sections, test_stats)
    assert metrics["sections_total"] == 5
    assert metrics["sections_empty"] == 1
    assert metrics["sections_blocked"] == 1
    assert metrics["sections_error"] == 1
    assert metrics["sections_truncated"] == 1
    assert metrics["quality_score"] < 100

    # T6: Chat - baze
    cm = compute_chat_metrics(
        response_text="Sipas Nenit 145 të LPK-së, dispozitivi duhet të jetë i qartë.",
        context="Neni 145 i LPK-së përcakton ... C.nr.385/2024 ... Ligji 06/L-074",
        duration_sec=2.5,
        ttft_sec=0.8,
        model="deepseek/deepseek-v4-flash-0731",
    )
    assert cm["response_chars"] > 0
    assert not cm["response_empty"]
    assert cm["grounding_hits"] >= 1  # art:145 duhet të mbivendoset
    assert cm["quality_score"] >= 80

    # T7: Chat - bosh
    cm_empty = compute_chat_metrics(response_text="", context="diqka")
    assert cm_empty["response_empty"]
    assert cm_empty["quality_score"] <= 40

    # T8: Chat - kontekst bosh
    cm_nocontext = compute_chat_metrics(response_text="Diçka.", context="")
    assert cm_nocontext["grounding_score"] is None
    assert cm_nocontext["context_anchors_total"] == 0

    # T9: Grounding detection
    anchors = _extract_anchors("C.nr.385/2024 dhe Neni 145 i LPK-së, Ligji 06/L-074")
    assert "case:C.nr.385/2024" in anchors
    assert "art:145" in anchors
    assert "law:06/L-074" in anchors

    # T10: Chat - kostot
    cm_cost = compute_chat_metrics(
        response_text="A" * 500,
        context="B" * 1000,
        model="openai/gpt-4o-mini",
    )
    assert cm_cost["cost_estimate_usd"] > 0

    logger.info("✅ [QUALITY_METRICS V1.3] Të gjitha testet kaluan (T1-T10).")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    _self_test()