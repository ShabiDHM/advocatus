# FILE: backend/app/services/document_review/quality_metrics.py
# PHOENIX PROTOCOL - QUALITY METRICS V1.1
# V1.1: FIX T2 — Test string-u i zgjatur nga ~161 në ~330 karaktere për të
#       tejkaluar threshold TRUNCATION_MIN_CHARS=200. Logjika e prodhimit
#       NUK u prek, vetëm testi i brendshëm.
# V1.0: Matje automatike e cilësisë. Zero varësi nga LLM.
#
# Përdoret nga service.py dhe verifier.py për të raportuar:
#   - sections_empty, sections_truncated, sections_blocked, sections_error
#   - quality_score (0-100)
#   - cost_estimate_usd
#   - avg/min/max content length

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# KONSTANTE
# ═══════════════════════════════════════════════════════════════════════════

# DeepSeek V4 Flash 0731 — çmimet për 1M tokens (Together AI)
COST_INPUT_PER_M = 0.14
COST_OUTPUT_PER_M = 0.28

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

# Prefiksat e linjës që nuk numërohen si "truncation"
NON_TRUNCATION_PREFIXES = ('#', '*', '-', '•', '>', '▪', '◆', '◎', '○', '⏺')


# ═══════════════════════════════════════════════════════════════════════════
# DETEKTORË
# ═══════════════════════════════════════════════════════════════════════════

def _is_empty(content: str) -> bool:
    """Seksioni ka < MIN_CONTENT_CHARS karaktere."""
    return not content or len(content.strip()) < MIN_CONTENT_CHARS


def _is_truncated(content: str) -> bool:
    """
    Heuristikë: fundi i tekstit nuk mbyllet me shenjë pikësimi.
    Përjashton bullet points, headers, tabela.
    """
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

    # Bullet point / heading / blockquote → jo truncation
    for prefix in NON_TRUNCATION_PREFIXES:
        if last_line.startswith(prefix):
            return False

    # Duhet të ketë ≥4 fjalë për t'u konsideruar "mes fjale"
    words = last_line.split()
    if len(words) < TRUNCATION_MIN_LAST_LINE_WORDS:
        return False

    return True


def _has_error(sec: Dict[str, Any]) -> bool:
    return bool(sec.get("error"))


def _is_blocked(sec: Dict[str, Any]) -> bool:
    return bool(sec.get("_blocked_by_hallucination"))


# ═══════════════════════════════════════════════════════════════════════════
# COST ESTIMATE
# ═══════════════════════════════════════════════════════════════════════════

def _estimate_tokens_from_chars(chars: int) -> int:
    return max(1, int(chars / CHARS_PER_TOKEN))


def _estimate_cost(
    section_stats: Dict[str, Any],
) -> Tuple[float, int, int]:
    """
    Kthen: (cost_usd, input_tokens_est, output_tokens_est)
    """
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
# QUALITY SCORE
# ═══════════════════════════════════════════════════════════════════════════

def _compute_quality_score(
    total: int,
    empty: int,
    truncated: int,
    blocked: int,
    errors: int,
) -> int:
    """
    Score 0-100:
      - 100 = të gjitha seksionet, pa probleme
      - Zbritje: -25 për error, -20 për blocked, -10 për empty, -5 për truncated
    """
    if total == 0:
        return 0

    score = 100
    score -= errors * 25
    score -= blocked * 20
    score -= empty * 10
    score -= truncated * 5

    return max(0, min(100, score))


# ═══════════════════════════════════════════════════════════════════════════
# API KRYESOR
# ═══════════════════════════════════════════════════════════════════════════

def compute_quality_metrics(
    sections: Dict[str, Any],
    section_stats: Optional[Dict[str, Any]] = None,
    hallucination_report: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Kthen dict me metrikat e cilësisë.
    """
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
    """Log i formatuar mirë për lehtësi skanim në Render/terminal."""
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
# SELF-TEST (V1.1: T2 string i zgjatur)
# ═══════════════════════════════════════════════════════════════════════════

def _self_test() -> None:
    """
    T1: false-positive — seksion normal me pikë → JO truncated.
    T2: real — seksion i prerë në mes → truncated (> 200 chars).
    T3: morfologji — fund me diakritika → JO false.
    T4: bullet list → JO truncated.
    T5: metrika baze.
    """
    # T1: Normal
    sec_ok = "Ky është tekst i plotë. Ka disa fjali. Dhe mbaron me pikë."
    assert not _is_truncated(sec_ok), "T1 failed: normal u shënua truncated"

    # T2: Truncated (> 200 chars)
    sec_trunc = (
        "Ky është një paragraf i gjatë që fillon mirë dhe vazhdon "
        "me shumë detaje të rëndësishme për analizën e thelluar "
        "të rastit dhe pastaj papritmas ndërpritet në mes të një "
        "fjalie pa përfunduar mendimin dhe pa vendosur pikë "
        "në fund të tekstit sikurse ndodh shpesh me modelet që "
        "harxhojnë max_tokens dhe mbeten pa hapësirë për output"
    )
    assert _is_truncated(sec_trunc), "T2 failed: truncated nuk u zbulua"

    # T3: Morfologji
    sec_dia = "Analiza e thelluar përfundon me rezultatin përfundimtar."
    assert not _is_truncated(sec_dia), "T3 failed: diakritikat shkaktuan false"

    # T4: Bullet list → jo truncated
    sec_bullet = (
        "- Pika e parë e listës së gjatë me shumë detaje që vazhdon\n"
        "- Pika e dytë me më shumë detaje dhe kontekst të gjerë"
    )
    assert not _is_truncated(sec_bullet), "T4 failed: bullet u shënua truncated"

    # T5: Metrikat baze
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

    logger.info("✅ [QUALITY_METRICS] Të gjitha testet kaluan (T1-T5).")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    _self_test()