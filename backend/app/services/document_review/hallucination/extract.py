# FILE: backend/app/services/document_review/hallucination/extract.py
# PHOENIX PROTOCOL - HALLUCINATION EXTRACT V1.26
# V1.26: DEAD CODE REMOVAL —
#        - `has_real_citation_context` kishte `found_any` të panevojshëm:
#          të dyja rrugët e fundit kthenin False. Tani thjesht `return False`
#          pas ciklit. Logjika e saktë (return True vetëm kur gjendet match
#          jashtë kontekstit të sugjerimit) mbetet identike.
# V1.25: Shtuar alias `_extract_dates_iso` për backward compat.

import re
from typing import Set

from ..patterns import (
    DATE_PATTERN,
    DATE_ALBANIAN_PATTERN,
    ARTICLE_PATTERN,
    LAW_NUMBER_PATTERN,
    LAW_NUMBER_LEGACY_PATTERN,
    LAW_NUMBER_WITH_NAME_PATTERN,
    CASE_NUMBER_PATTERN,
    ABBREV_PATTERN,
)
from ..helpers import (
    parse_date,
    month_name_to_number,
    normalize_law_number,
    normalize_case_number,
    is_valid_law_abbrev,
)
from ..citation_extractor import _normalize_article_number
from .constants import (
    CASE_NUMBER_PREFIXES,
    COMMON_ALBANIAN_UPPERCASE_WORDS,
    COMMON_HEADING_WORDS,
    SUGGESTION_CONTEXT_KEYWORDS,
)
from .normalize import is_valid_law_output, split_article_numbers


# ═══════════════════════════════════════════════════════════════════════════
# TEXT EXTRACTORS
# ═══════════════════════════════════════════════════════════════════════════

def extract_dates_iso(text: str) -> Set[str]:
    found: Set[str] = set()
    if not text:
        return found

    for m in DATE_PATTERN.finditer(text):
        dt = parse_date(m.group(1), m.group(2), m.group(3))
        if dt:
            found.add(dt.isoformat()[:10])

    for m in DATE_ALBANIAN_PATTERN.finditer(text):
        month_num = month_name_to_number(m.group(2))
        if not month_num:
            continue
        dt = parse_date(m.group(1), str(month_num), m.group(3))
        if dt:
            found.add(dt.isoformat()[:10])

    return found


def extract_articles(text: str) -> Set[str]:
    found: Set[str] = set()
    if not text:
        return found

    for m in ARTICLE_PATTERN.finditer(text):
        art_raw = m.group(1)
        par_raw = m.group(2)
        parts = split_article_numbers(art_raw)
        for part in parts:
            if not part:
                continue
            art, _ = _normalize_article_number(part, par_raw)
            if art:
                found.add(art)

    return found


def extract_laws(text: str) -> Set[str]:
    found: Set[str] = set()
    if not text:
        return found

    for m in LAW_NUMBER_WITH_NAME_PATTERN.finditer(text):
        n = normalize_law_number(m.group(1))
        if n and is_valid_law_output(n):
            found.add(n)

    for m in LAW_NUMBER_PATTERN.finditer(text):
        n = normalize_law_number(m.group(0))
        if n and is_valid_law_output(n):
            found.add(n)

    for m in LAW_NUMBER_LEGACY_PATTERN.finditer(text):
        candidate = f"{m.group(1)}/{m.group(2)}"
        if is_valid_law_output(candidate):
            found.add(candidate)

    return found


def extract_cases(text: str) -> Set[str]:
    found: Set[str] = set()
    if not text:
        return found

    for m in CASE_NUMBER_PATTERN.finditer(text):
        prefix = m.group(1).upper()
        num_part = m.group(2).rstrip(".,;:")
        if not num_part:
            continue
        raw = f"{prefix}.nr.{num_part}"
        n = normalize_case_number(raw)
        if n:
            found.add(n)

    return found


def extract_abbrevs(text: str) -> Set[str]:
    found: Set[str] = set()
    if not text:
        return found

    for m in ABBREV_PATTERN.finditer(text):
        abbr = m.group(1)
        abbr_up = abbr.upper()
        if abbr_up in CASE_NUMBER_PREFIXES:
            continue
        if abbr_up in COMMON_ALBANIAN_UPPERCASE_WORDS:
            continue
        if abbr_up in COMMON_HEADING_WORDS:
            continue
        if is_valid_law_abbrev(abbr):
            found.add(abbr_up)

    return found


def extract_law_numbers_from_title_strict(title: str) -> Set[str]:
    """Nxjerr numra ligjesh nga një titull (strict, me kontekst 'ligj'/'kodi')."""
    found: Set[str] = set()
    if not title:
        return found

    s = str(title)

    for m in LAW_NUMBER_PATTERN.finditer(s):
        n = normalize_law_number(m.group(0))
        if n and is_valid_law_output(n):
            found.add(n)

    lower = s.lower()
    for m in LAW_NUMBER_LEGACY_PATTERN.finditer(s):
        start = max(0, m.start() - 100)
        ctx = lower[start:m.start() + 10]
        if any(k in ctx for k in ("ligj", "kodi")):
            candidate = f"{m.group(1)}/{m.group(2)}"
            if is_valid_law_output(candidate):
                found.add(candidate)

    return found


# ═══════════════════════════════════════════════════════════════════════════
# CONTEXT HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def has_real_citation_context(
    text: str,
    value: str,
    window: int = 200,
    prefixes: tuple = ("",),
) -> bool:
    """
    Kthen True nëse vlera shfaqet në tekst PA fjalë sugjerimi përreth.
    Kthen False nëse çdo dukuri është në kontekst sugjerimi ose vlera mungon.

    V1.26: Hequr `found_any` i panevojshëm (ishte dead — të dyja rrugët
    kthenin False).
    """
    if not text or not value:
        return False

    for prefix in prefixes:
        pat = f"{prefix} {value}".strip() if prefix else value
        if not pat:
            continue
        idx = text.find(pat)
        while idx != -1:
            start = max(0, idx - window)
            end = min(len(text), idx + len(pat) + window)
            ctx = text[start:end].lower()

            if not any(kw in ctx for kw in SUGGESTION_CONTEXT_KEYWORDS):
                return True

            idx = text.find(pat, idx + 1)

    return False


def has_real_article_context(text: str, article_number: str, window: int = 200) -> bool:
    return has_real_citation_context(
        text, article_number, window=window,
        prefixes=("Neni", "Nenit", "neni", "nenit", "NENI", "NENIT"),
    )


def find_snippet(text: str, value: str, window: int = 80) -> str:
    if not text or not value:
        return ""
    idx = text.find(value)
    if idx == -1:
        return ""
    start = max(0, idx - window)
    end = min(len(text), idx + len(value) + window)
    snippet = text[start:end].replace("\n", " ").strip()
    return f"...{snippet}..."


# ═══════════════════════════════════════════════════════════════════════════
# DATE FORMAT (ISO → DD.MM.YYYY)
# ═══════════════════════════════════════════════════════════════════════════

def iso_to_albanian_date(iso_str: str) -> str:
    if not iso_str:
        return iso_str
    s = str(iso_str).strip()
    m = re.match(r'^(\d{4})-(\d{2})-(\d{2})(.*)$', s)
    if m:
        return f"{m.group(3)}.{m.group(2)}.{m.group(1)}{m.group(4)}"
    return iso_str


# ═══════════════════════════════════════════════════════════════════════════
# V1.25: BACKWARD-COMPAT ALIASES
# ═══════════════════════════════════════════════════════════════════════════
# service.py dhe verifier.py importojnë emrat e vjetër me underscore.
# Këto alias mbajnë kompatibilitetin pas modularizimit.

_extract_dates_iso = extract_dates_iso