# FILE: backend/app/services/document_review/hallucination/normalize.py
# PHOENIX PROTOCOL - HALLUCINATION NORMALIZE V1.25
# Normalizim i emrave/numrave të ligjeve, precedentëve, neneve.
# Plus: known laws (dinamik nga JSON) + globally allowed laws.

import re
import logging
from typing import Dict, List, Optional, Set

from ..patterns import (
    LAW_NUMBER_PATTERN,
    LAW_NUMBER_LEGACY_PATTERN,
    CASE_NUMBER_PATTERN,
)
from ..helpers import (
    normalize_law_number,
    normalize_case_number,
)
from ..dynamic_config import get_known_laws
from .constants import ALBANIAN_CASE_NORMALIZATIONS
from .regexes import STRICT_LAW_OUTPUT_PATTERN

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# LAW NAME NORMALIZATION
# ═══════════════════════════════════════════════════════════════════════════

def normalize_law_name(name: str) -> str:
    """Normalizon emrin e ligjit: lowercase, pa diakritika, case-folded."""
    if not name:
        return ""
    n = name.strip().lower()
    n = n.replace("ë", "e").replace("ç", "c")
    for pattern, replacement in ALBANIAN_CASE_NORMALIZATIONS:
        n = re.sub(pattern, replacement, n)
    n = re.sub(r'\s+', ' ', n).strip()
    return n


def normalize_law_num(num: str) -> str:
    """Normalizon numrin e ligjit: heq hapësira, uniform – → -, upper."""
    if not num:
        return ""
    return re.sub(r'[\s]+', '', num).upper().replace('–', '-')


# ═══════════════════════════════════════════════════════════════════════════
# LAW OUTPUT VALIDATION
# ═══════════════════════════════════════════════════════════════════════════

def is_valid_law_output(s: str) -> bool:
    if not s:
        return False
    return bool(STRICT_LAW_OUTPUT_PATTERN.match(s.strip()))


def safe_normalize_law(raw_value: str) -> Optional[str]:
    """
    Nxjerr numrin e ligjit nga çdo string (edhe me prefiks 'Ligji Nr. ...').
    Kthen None nëse nuk gjen numër të vlefshëm.
    """
    if not raw_value:
        return None
    s = str(raw_value).strip()
    if not s:
        return None

    n = normalize_law_number(s)
    if n and is_valid_law_output(n):
        return n

    m = LAW_NUMBER_PATTERN.search(s)
    if m:
        n2 = normalize_law_number(m.group(0))
        if n2 and is_valid_law_output(n2):
            return n2

    stripped = re.sub(
        r'^(ligj(?:it|i|ji)?|kodi)\s*(?:nr\.?\s*)?', '',
        s, flags=re.IGNORECASE,
    ).strip()
    m = LAW_NUMBER_LEGACY_PATTERN.match(stripped)
    if m:
        candidate = f"{m.group(1)}/{m.group(2)}"
        if is_valid_law_output(candidate):
            return candidate

    return None


# ═══════════════════════════════════════════════════════════════════════════
# CASE NUMBER NORMALIZATION
# ═══════════════════════════════════════════════════════════════════════════

def normalize_precedent_case(case_number: str) -> Optional[str]:
    if not case_number:
        return None
    m = CASE_NUMBER_PATTERN.search(case_number)
    if m:
        prefix = m.group(1).upper()
        num_part = m.group(2).rstrip(".,;:")
        if not num_part:
            return None
        raw = f"{prefix}.nr.{num_part}"
        return normalize_case_number(raw)
    return normalize_case_number(case_number) or case_number.upper().strip()


# ═══════════════════════════════════════════════════════════════════════════
# ARTICLE LIST SPLITTER
# ═══════════════════════════════════════════════════════════════════════════

def split_article_numbers(raw: str) -> List[str]:
    if not raw:
        return []
    parts = re.split(r'\s*[,;]\s*|\s+dhe\s+', raw.strip())
    return [p.strip() for p in parts if p.strip()]


# ═══════════════════════════════════════════════════════════════════════════
# KNOWN LAWS — dynamic nga data/dynamic_config.json
# ═══════════════════════════════════════════════════════════════════════════

# Fallback minimal — nëse JSON mungon, këto mbeten.
_DEFAULT_KNOWN_LAWS: Dict[str, List[str]] = {
    "kodi penal": ["06/L-074"],
    "kodi i procedures penale": ["08/L-032"],
    "ligji per proceduren kontestimore": ["03/L-006"],
    "ligji per familjen": ["2004/32"],
    "ligji per mbrojtjen nga dhuna ne familje": ["03/L-182", "08/L-185"],
}


KNOWN_LAW_NAME_NUMBER_MAP: Dict[str, List[str]] = get_known_laws(
    _DEFAULT_KNOWN_LAWS
)


NORMALIZED_KNOWN_LAW_MAP: Dict[str, List[str]] = {
    normalize_law_name(k): v for k, v in KNOWN_LAW_NAME_NUMBER_MAP.items()
}


def get_globally_allowed_laws() -> Set[str]:
    """
    Kthen numrat e ligjeve të njohura (nga KNOWN_LAW_NAME_NUMBER_MAP).
    Zero hardcoding — lexohet nga JSON.
    """
    allowed: Set[str] = set()
    for numbers in KNOWN_LAW_NAME_NUMBER_MAP.values():
        for n in numbers:
            normalized = safe_normalize_law(n)
            if normalized:
                allowed.add(normalized)
    return allowed