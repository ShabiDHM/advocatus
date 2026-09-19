# FILE: backend/app/services/document_review/helpers.py
# PHOENIX PROTOCOL - HELPERS V2.1
# V2.1: FIX në split_into_sentences — nda vetëm me \n\n ose pikë + hapësirë 
#       + shkronjë e madhe. Kjo parandalon copëtimin e fjalive me "par.1\ndhe 2".

import re
import unicodedata
from datetime import datetime
from typing import Optional

from .constants import (
    ROMAN_NUMERALS,
    ALBANIAN_STOPWORDS,
    LAW_CODE_MIN_LENGTH,
    LAW_CODE_MAX_LENGTH,
)


# ═══════════════════════════════════════════════════════════════════════════
# TEXT NORMALIZATION
# ═══════════════════════════════════════════════════════════════════════════

def normalize_albanian(text: str) -> str:
    """Lowercase + heq diakritikat (ë → e, ç → c)."""
    if not text:
        return ""
    text = text.lower()
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    return text


def normalize_law_number(num: str) -> str:
    """Normalizon numrin e ligjit në format standard 'XX/L-YYY'."""
    if not num:
        return ""
    digits = re.sub(r'\D', '', num)
    if len(digits) < 4:
        return num
    return f"{digits[:2]}/L-{digits[2:]}"


def normalize_case_number(raw: str) -> str:
    """Normalizon numrin e lëndës."""
    if not raw:
        return ""
    raw = re.sub(r'\s+', '', raw)
    raw = raw.replace('..', '.')
    m = re.match(r'^([A-Z]+)\.?nr\.?(.+)$', raw, re.IGNORECASE)
    if m:
        prefix = m.group(1).upper()
        num = m.group(2)
        return f"{prefix}.nr.{num}"
    return raw


# ═══════════════════════════════════════════════════════════════════════════
# ABBREVIATION VALIDATION
# ═══════════════════════════════════════════════════════════════════════════

def is_valid_law_abbrev(abbr: str) -> bool:
    """Kontrollo nëse një akronim duket si kod ligji."""
    if not abbr:
        return False

    abbr_up = abbr.upper()

    if len(abbr_up) < LAW_CODE_MIN_LENGTH or len(abbr_up) > LAW_CODE_MAX_LENGTH:
        return False
    if abbr_up in ROMAN_NUMERALS:
        return False
    if normalize_albanian(abbr) in ALBANIAN_STOPWORDS:
        return False
    if not re.match(r'^[A-ZËÇ]+$', abbr_up):
        return False
    if any(c in abbr_up for c in 'QJXY'):
        return False

    vowels_set = set("AEIOUYË")
    if abbr_up[0] in vowels_set:
        return False

    consonants = sum(1 for c in abbr_up if c not in vowels_set)
    if consonants < 2:
        return False

    vowels = len(abbr_up) - consonants
    if vowels / len(abbr_up) >= 0.5:
        return False

    return True


# ═══════════════════════════════════════════════════════════════════════════
# DATE HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def parse_date(day: str, month: str, year: str) -> Optional[datetime]:
    """Provo të parsojë një datë. Kthen None nëse dështon."""
    try:
        d = int(day)
        m = int(month)
        y = int(year)
        if y < 100:
            y += 2000
        if 1 <= d <= 31 and 1 <= m <= 12 and 1900 <= y <= 2100:
            return datetime(y, m, d)
    except (ValueError, TypeError):
        pass
    return None


ALBANIAN_MONTH_MAP = {
    'janar': 1, 'shkurt': 2, 'mars': 3, 'prill': 4, 'maj': 5, 'qershor': 6,
    'korrik': 7, 'gusht': 8, 'shtator': 9, 'tetor': 10, 'nëntor': 11, 'dhjetor': 12,
}


def month_name_to_number(name: str) -> Optional[int]:
    """Konverto emrin e muajit shqip në numër (1-12)."""
    if not name:
        return None
    return ALBANIAN_MONTH_MAP.get(name.lower())


# ═══════════════════════════════════════════════════════════════════════════
# TEXT EXTRACT
# ═══════════════════════════════════════════════════════════════════════════

def extract_context(text: str, position: int, window: int = 150) -> str:
    """Nxjerr kontekstin rreth një pozicioni në tekst."""
    if not text:
        return ""
    start = max(0, position - window)
    end = min(len(text), position + window)
    ctx = text[start:end].strip()
    return re.sub(r'\s+', ' ', ctx)


def split_into_sentences(text: str) -> list:
    """
    V2.1: Ndan tekstin në fjali.
    Ndan vetëm me:
      - Newline i dyfishtë (\\n\\n)
      - Shenjë pikësimi + hapësirë + shkronjë e madhe [.;!?]\\s+[A-ZËÇ]

    Kjo parandalon copëtimin gabimisht pas:
      - "par.1\\ndhe 2" (d është e vogël)
      - "C.nr.385" (numri pas pikës, jo shkronjë e madhe)
      - "16.02.2024" (numrat)
    """
    if not text:
        return []
    parts = re.split(r'\n{2,}|(?<=[.;!?])\s+(?=[A-ZËÇ])', text)
    return [p.strip() for p in parts if p.strip()]