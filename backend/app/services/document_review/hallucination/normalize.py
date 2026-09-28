# FILE: backend/app/services/document_review/hallucination/normalize.py
# PHOENIX PROTOCOL - HALLUCINATION NORMALIZE V1.27
# V1.27: FALSE-POSITIVE WHITELIST — Shtuar _load_fp_whitelist(),
#        reload_fp_whitelist(), is_whitelisted_fp(). Lexohet nga
#        data/known_false_positives.json. Zero hardcoding.
# V1.25: Dynamic known laws (JSON).
# V1.20: Normalizime.

import re
import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

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


# ═══════════════════════════════════════════════════════════════════════════
# V1.27: FALSE-POSITIVE WHITELIST
# ═══════════════════════════════════════════════════════════════════════════

_FP_WHITELIST_PATH = Path(__file__).parent.parent / "data" / "known_false_positives.json"


@lru_cache(maxsize=1)
def _load_fp_whitelist() -> Dict[str, Any]:
    """
    Lexon false-positive whitelist nga data/known_false_positives.json.
    Cache-on një herë. Reload me reload_fp_whitelist().
    """
    if not _FP_WHITELIST_PATH.exists():
        logger.info(
            f"ℹ️ [FP WHITELIST V1.27] {_FP_WHITELIST_PATH} nuk ekziston — "
            f"whitelist bosh."
        )
        return {"entries": []}

    try:
        with _FP_WHITELIST_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            logger.warning(
                f"⚠️ [FP WHITELIST V1.27] {_FP_WHITELIST_PATH} nuk përmban objekt JSON."
            )
            return {"entries": []}
        entries_count = len(data.get("entries", []))
        logger.info(
            f"✅ [FP WHITELIST V1.27] U lexua: {_FP_WHITELIST_PATH} "
            f"({entries_count} entries aktive)"
        )
        return data
    except Exception as e:
        logger.warning(f"⚠️ [FP WHITELIST V1.27] Leximi dështoi: {e}")
        return {"entries": []}


def reload_fp_whitelist() -> None:
    """Pastron cache-in — ndryshimet në JSON aplikohen menjëherë."""
    _load_fp_whitelist.cache_clear()
    logger.info("🔄 [FP WHITELIST V1.27] Cache u pastrua — rilexohet me thirrjen tjetër.")


def is_whitelisted_fp(kind: str, value: str, section_content: str) -> bool:
    """
    Kontrollon nëse vlera është false-positive e njohur.

    Argumentet:
        kind: "article" | "law" | "case" | "date" | "abbreviation"
        value: vlera e papërpunuar (p.sh. "5", "06/L-074", "C.nr.385/2024")
        section_content: teksti i plotë i seksionit (për kontekst)

    Kthen: True nëse vlera duhet të filtrohet (whitelisted).
    """
    if not value:
        return False

    content_lower = (section_content or "").lower()
    value_str = str(value).strip()

    for entry in _load_fp_whitelist().get("entries", []):
        if not entry.get("enabled", True):
            continue
        if kind not in entry.get("kinds", []):
            continue

        # 1. Kontrollo value_regex
        regex = entry.get("value_regex")
        if regex:
            try:
                if not re.search(regex, value_str, re.IGNORECASE):
                    continue
            except re.error as re_err:
                logger.warning(
                    f"⚠️ [FP WHITELIST V1.27] Regex e pavlefshme '{regex}': {re_err}"
                )
                continue

        # 2. Kontrollo kontekstin (section_must_contain_any)
        contexts = entry.get("section_must_contain_any", [])
        if contexts:
            if not any(c.lower() in content_lower for c in contexts):
                continue

        # Përputhje e plotë
        return True

    return False