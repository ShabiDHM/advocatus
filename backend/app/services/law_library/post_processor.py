# FILE: backend/app/services/law_library/post_processor.py
# PHOENIX PROTOCOL - POST PROCESSOR V2.1
#
# V2.1: FIX G1 + G3 (auditim i testeve).
#   - G1: _normalize_law_number heq edhe "/" (03/L-182 → 03L182, 2004/32 → 200432)
#   - G3: EXTRA_ARTICLE_THRESHOLD default = 0 (hallucination detection strikt)
#
# V2.0: FIX PP1-PP10 (auditim).
#   - PP1: Numrat normalizohen uniform
#   - PP2: allowed_law_numbers më të gjera (fallback në source_text)
#   - PP3: Whitelist për referenca të njohura
#   - PP4: Regex mbulon Neni/Nenit/Nenin/Neniet/Nenieve
#   - PP5: Word boundary strikt
#   - PP6: Correction note përfshin sugjerim
#   - PP7: Threshold tolerance (configurable)
#   - PP8: Sub-article (5/1) i trajtuar saktë

import re
import logging
import os
from typing import Dict, Any, Set

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# THRESHOLD (G3 fix)
# ═══════════════════════════════════════════════════════════════════════════
# Për sistem juridik, toleranca për NENE = 0 (një nen i shpikur = hallucination).
# Toleranca për NUMRA ligjesh = 1 (LLM mund të përmendë ligj referues në kontekst).
EXTRA_ARTICLE_THRESHOLD = int(os.getenv("POST_PROCESSOR_ARTICLE_THRESHOLD", "0"))
EXTRA_LAW_THRESHOLD = int(os.getenv("POST_PROCESSOR_LAW_THRESHOLD", "1"))


# ═══════════════════════════════════════════════════════════════════════════
# REGEX
# ═══════════════════════════════════════════════════════════════════════════

# PP4: Regex i plotë — Neni, Nenit, Nenin, Neniet, Nenieve
_ARTICLE_RE = re.compile(
    r'\bNen(?:i|it|in|ët|iet|ieve)\s+(\d+(?:[\.\/]\d+)*)',
    re.IGNORECASE | re.UNICODE,
)

# PP1: Ruan kuptim gjatë parse, normalizohet në _normalize_law_number
_LAW_NUMBER_RE = re.compile(
    r'\b('
    r'\d{2}\s*[\/\-_\s]?\s*L\s*[\/\-_\s]?\s*\d{2,4}'   # 03/L-182
    r'|'
    r'\d{4}\s*\/\s*\d{1,4}'                              # 2004/32
    r')\b',
    re.IGNORECASE,
)


# ═══════════════════════════════════════════════════════════════════════════
# NORMALIZIM
# ═══════════════════════════════════════════════════════════════════════════

def _normalize_law_number(num: str) -> str:
    """
    V2.1 (G1 fix): Normalizim që heq TË GJITHË ndarësit (whitespace, -, _, /).

    Shembuj:
    - "03 L 182"   → "03L182"
    - "03/L-182"   → "03L182"
    - "2004/32"    → "200432"
    - "06/L-074"   → "06L074"
    """
    if not num:
        return ""
    # Heq TË GJITHË ndarësit (whitespace, hyphen, underscore, slash)
    result = re.sub(r'[\s\-_/]+', '', num)
    return result.upper()


def _extract_articles(text: str) -> Set[str]:
    """PP8: Nxjerr nenet me sub-article të ruajtur."""
    if not text:
        return set()
    return {m.group(1) for m in _ARTICLE_RE.finditer(text)}


def _extract_law_numbers(text: str) -> Set[str]:
    """Nxjerr numrat e ligjeve të normalizuar."""
    if not text:
        return set()
    return {_normalize_law_number(m.group(1)) for m in _LAW_NUMBER_RE.finditer(text)}


# ═══════════════════════════════════════════════════════════════════════════
# VERIFY EXPLANATION
# ═══════════════════════════════════════════════════════════════════════════

def verify_explanation_output(
    output_text: str,
    source_text: str,
    source_article: str,
    source_law_title: str,
) -> Dict[str, Any]:
    """
    V2.1: Verifikon output LLM.

    PP3: Fusha `source_text` përdoret EDHE për whitelist të numrave të ligjeve —
    nëse neni citon një ligj tjetër brenda tekstit, ai lejohet.
    """
    if not output_text:
        return {
            "is_clean": True,
            "extra_articles": [],
            "extra_law_numbers": [],
            "correction_note": "",
            "metadata": {"reason": "empty_output"},
        }

    # PP2 + PP3: allowed = source_text ∪ source_law_title ∪ source_article
    allowed_articles = _extract_articles(source_text)
    allowed_articles.add(str(source_article))

    allowed_law_numbers = _extract_law_numbers(source_law_title)
    allowed_law_numbers |= _extract_law_numbers(source_text)

    output_articles = _extract_articles(output_text)
    output_law_numbers = _extract_law_numbers(output_text)

    extra_articles = output_articles - allowed_articles
    extra_law_numbers = output_law_numbers - allowed_law_numbers

    # PP7 + G3: Threshold tolerance
    is_clean = (
        len(extra_articles) <= EXTRA_ARTICLE_THRESHOLD
        and len(extra_law_numbers) <= EXTRA_LAW_THRESHOLD
    )

    correction_note = ""
    if not is_clean:
        lines = ["\n\n---\n", "## ⚠️ VËREJTJE AUTOMATIKE\n"]
        if extra_articles:
            lines.append(
                "**Nenet e mëposhtme cituar në shpjegim NUK shfaqen në tekstin origjinal:**\n\n"
            )
            for art in sorted(extra_articles, key=lambda x: (len(x), x)):
                lines.append(f"- ⚠️ Neni {art} — verifiko manualisht\n")
        if extra_law_numbers:
            lines.append(
                "\n**Numrat e ligjeve të mëposhtëm NUK shfaqen në titullin/tekstin origjinal:**\n\n"
            )
            for num in sorted(extra_law_numbers):
                lines.append(f"- ⚠️ {num} — verifiko manualisht\n")
        lines.append("\n*Ky kontroll automatik nuk zëvendëson verifikimin manual.*")
        correction_note = "".join(lines)

        logger.warning(
            f"[POST_PROCESSOR] FAIL: extra_articles={sorted(extra_articles)}, "
            f"extra_laws={sorted(extra_law_numbers)}"
        )
    else:
        logger.info("[POST_PROCESSOR] OK")

    return {
        "is_clean": is_clean,
        "extra_articles": sorted(extra_articles),
        "extra_law_numbers": sorted(extra_law_numbers),
        "correction_note": correction_note,
        "metadata": {
            "threshold_articles": EXTRA_ARTICLE_THRESHOLD,
            "threshold_laws": EXTRA_LAW_THRESHOLD,
        },
    }


__all__ = ["verify_explanation_output"]