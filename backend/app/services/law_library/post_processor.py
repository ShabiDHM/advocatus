# FILE: backend/app/services/law_library/post_processor.py
# PHOENIX PROTOCOL - POST PROCESSOR V1.2
# V1.2: FIX — _LAW_NUMBER_RE pranon edhe format "2004/32" (vit/law për ligjet
#       e vjetra si Ligji i Familjes Nr. 2004/32). Më parë vetëm "XX/L-NNN".
# V1.1: Normalizim i plotë i numrave të ligjeve (heq të gjithë ndarësit).
# V1.0: Verifikon që output-i i LLM-it nuk ka halluzinim.

import re
import logging
from typing import Dict, Any, List, Set

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# REGEX
# ═══════════════════════════════════════════════════════════════════════════

_ARTICLE_RE = re.compile(
    r'\bNen(?:i|it|in|ët)\s+(\d+(?:[\.\/]\d+)*)',
    re.IGNORECASE | re.UNICODE,
)

# V1.2: Dy formate — "XX/L-NNN" dhe "YYYY/NN"
_LAW_NUMBER_RE = re.compile(
    r'\b('
    r'\d{2}\s*[\/\-_\s]?\s*L\s*[\/\-_\s]?\s*\d{2,4}'
    r'|'
    r'\d{4}\s*\/\s*\d{1,4}'
    r')\b',
    re.IGNORECASE,
)


# ═══════════════════════════════════════════════════════════════════════════
# NORMALIZIM
# ═══════════════════════════════════════════════════════════════════════════

def _normalize_law_number(num: str) -> str:
    """
    Heq TË GJITHË ndarësit dhe normalizon në format uniform.

    Shembuj:
    - "03 L 182"   → "03L182"
    - "03/L-182"   → "03L182"
    - "2004/32"    → "200432"
    """
    if not num:
        return ""
    return re.sub(r'[\s\-_\/]+', '', num).upper()


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
    Kontrollon që output-i i LLM-it:
      1. Nuk citon nene të reja që nuk janë në tekstin origjinal
      2. Nuk shpik numra ligjesh që nuk janë në titullin origjinal

    V1.2: Numrat e ligjeve normalizohen plotësisht para krahasimit.
    """
    if not output_text:
        return {
            "is_clean": True,
            "extra_articles": [],
            "extra_law_numbers": [],
            "correction_note": "",
        }

    allowed_articles: Set[str] = set()
    for m in _ARTICLE_RE.finditer(source_text):
        allowed_articles.add(m.group(1))
    allowed_articles.add(source_article)

    allowed_law_numbers: Set[str] = set()
    for m in _LAW_NUMBER_RE.finditer(source_law_title):
        allowed_law_numbers.add(_normalize_law_number(m.group(1)))

    extra_articles: Set[str] = set()
    for m in _ARTICLE_RE.finditer(output_text):
        art = m.group(1)
        if art not in allowed_articles:
            extra_articles.add(art)

    extra_law_numbers: Set[str] = set()
    for m in _LAW_NUMBER_RE.finditer(output_text):
        num_normalized = _normalize_law_number(m.group(1))
        if num_normalized not in allowed_law_numbers:
            extra_law_numbers.add(num_normalized)

    is_clean = not extra_articles and not extra_law_numbers

    correction_note = ""
    if not is_clean:
        lines = ["\n\n---\n", "## ⚠️ VËREJTJE AUTOMATIKE\n"]
        if extra_articles:
            lines.append(
                "**Nenet e mëposhtme cituar në shpjegim NUK shfaqen në tekstin origjinal të nenit:**\n\n"
            )
            for art in sorted(extra_articles):
                lines.append(f"- ⚠️ Neni {art} — verifiko manualisht\n")
        if extra_law_numbers:
            lines.append(
                "\n**Numrat e ligjeve të mëposhtme NUK shfaqen në titullin e ligjit:**\n\n"
            )
            for num in sorted(extra_law_numbers):
                lines.append(f"- ⚠️ {num} — verifiko manualisht\n")
        lines.append("\n*Ky kontroll automatik nuk zëvendëson verifikimin manual.*")
        correction_note = "".join(lines)

        logger.warning(
            f"⚠️ [POST_PROCESSOR] Extra articles: {sorted(extra_articles)}, "
            f"extra laws: {sorted(extra_law_numbers)}"
        )
    else:
        logger.info("✅ [POST_PROCESSOR] Output is clean")

    return {
        "is_clean": is_clean,
        "extra_articles": sorted(extra_articles),
        "extra_law_numbers": sorted(extra_law_numbers),
        "correction_note": correction_note,
    }