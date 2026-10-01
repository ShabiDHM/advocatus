# FILE: backend/app/services/document_review/mongo_verifier/abbreviations.py
# PHOENIX PROTOCOL - MONGO VERIFIER / ABBREVIATIONS V1.1
#
# V1.1: DRY REFACTOR —
#       - Bashkuar `_generate_abbreviation_from_title` dhe
#         `_generate_full_abbreviation_from_title`: ishin identike përveç
#         limitit `[:6]`. Tani një funksion me `max_words` parametër
#         (default 6, `max_words=0` = pa limit). `_generate_full_...`
#         mbetet si wrapper për backward compat.
#       - Header sinkronizuar me logjikën e kodit (V2.6/V2.7 ishin mbetje
#         historike nga versioni monolitik).
#
# V1.0 (V2.12 modular): Ekstraktuar nga mongo_verifier.py V2.11.

import re
from typing import Tuple

from ..helpers import normalize_albanian
from .config import ABBREV_SKIP_WORDS


def _generate_abbreviation_from_title(title: str, max_words: int = 6) -> str:
    """
    Ekstrakt i akronimit nga titulli.

    max_words:
        6   → default (legacy — 6 fjalë maksimum)
        0   → pa limit (për compound match)
        >0  → limit eksplicit
    """
    if not title:
        return ""
    title_clean = re.sub(
        r'\b(?:Nr\.?|nr\.?)\s*\d+\s*[\/\-_\s]?\s*L\s*[\/\-_\s]?\s*\d+',
        '', title, flags=re.IGNORECASE,
    )
    normalized = normalize_albanian(title_clean)
    words = re.findall(r'\b[a-zëç]+\b', normalized)
    significant = [w for w in words if w not in ABBREV_SKIP_WORDS and len(w) >= 1]
    if len(significant) < 2:
        return ""
    words_to_use = significant if max_words <= 0 else significant[:max_words]
    return "".join(w[0].upper() for w in words_to_use)


def _generate_full_abbreviation_from_title(title: str) -> str:
    """
    V1.1: Wrapper i hollë mbi `_generate_abbreviation_from_title` me
    `max_words=0` — pa limit `[:6]`. Ruajtur si emër i veçantë për
    backward compat (thirret nga `_compound_abbrev_matches`).
    """
    return _generate_abbreviation_from_title(title, max_words=0)


def _extract_uppercase_sequence(s: str) -> str:
    """V2.6: 'LMDhFDhGDhBGj' → 'LMDFDGDBG'."""
    if not s:
        return ""
    return ''.join(c for c in s if c.isupper())


def _is_compound_abbrev_hint(s: str) -> bool:
    """V2.6: Kontroll nëse string-u është kandidat akronimi i përbërë."""
    if not s or len(s) < 8:
        return False
    upper_count = sum(1 for c in s if c.isupper())
    lower_count = sum(1 for c in s if c.islower())
    return upper_count >= 3 and lower_count >= 1


def _lcs_length(a: str, b: str) -> int:
    """
    V2.7: Llogarit gjatësinë e Longest Common Subsequence (LCS).
    Memory-optimized: mban vetëm 2 rreshta (O(min(m,n)) memory).
    """
    if not a or not b:
        return 0
    m, n = len(a), len(b)
    if n > m:
        a, b = b, a
        m, n = n, m

    prev = [0] * (n + 1)
    curr = [0] * (n + 1)
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if a[i - 1] == b[j - 1]:
                curr[j] = prev[j - 1] + 1
            else:
                curr[j] = max(prev[j], curr[j - 1])
        prev, curr = curr, [0] * (n + 1)
    return prev[n]


def _compound_abbrev_matches(cit_hint: str, db_title: str) -> Tuple[bool, str]:
    """
    V2.7: Match DINAMIK për akronime të përbëra (mixed-case, ≥8 chars).
    Përdor LCS midis sekuencës uppercase të hint-it dhe akronimit të plotë
    të gjeneruar nga titulli i DB.
    """
    if not _is_compound_abbrev_hint(cit_hint):
        return False, ""

    cit_seq = _extract_uppercase_sequence(cit_hint)
    if len(cit_seq) < 3:
        return False, ""

    full_generated = _generate_full_abbreviation_from_title(db_title)
    if not full_generated or len(full_generated) < 3:
        return False, ""

    lcs_len = _lcs_length(cit_seq, full_generated)
    min_len = min(len(cit_seq), len(full_generated))

    if min_len == 0:
        return False, ""

    ratio = lcs_len / min_len
    if ratio >= 0.7:
        return True, (
            f"compound_abbrev_lcs:{cit_seq}~{full_generated}"
            f"(lcs={lcs_len},ratio={ratio:.2f})"
        )

    return False, ""