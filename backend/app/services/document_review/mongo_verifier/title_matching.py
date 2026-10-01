# FILE: backend/app/services/document_review/mongo_verifier/title_matching.py
# PHOENIX PROTOCOL - MONGO VERIFIER / TITLE MATCHING V1.1
#
# V1.1: PRIORITY FIX —
#       - Ndërruar prioritetet e `compound_abbrev_lcs` (97→98) dhe
#         `compound_abbrev_partial` (98→97). Ishin invertuar: partial
#         kishte prioritet më të lartë se lcs. Kontradiktë me hierarkinë
#         e `abbrev_generated_*` (exact > prefix > partial). Rezultati:
#         match-e lcs (më të forta) humbnin ndaj partial (më të dobëta)
#         gjatë `matches.sort()` në articles.py.
#
# V1.0 (V2.12 modular): Ekstraktuar nga mongo_verifier.py V2.11.

import re
from typing import List, Set, Tuple

from ..helpers import normalize_albanian
from .config import (
    LAW_ABBREV_ALIASES,
    KNOWN_ABBREV_KEYWORDS,
    KNOWN_ABBREV_EXCLUDES,
    KEYWORD_MATCH_STOPWORDS,
)
from .abbreviations import (
    _generate_abbreviation_from_title,
    _compound_abbrev_matches,
    _is_compound_abbrev_hint,
)
from .text_utils import _extract_law_number_from_text, _extract_keywords


def _normalize_law_hint_alias(hint: str) -> str:
    if not hint:
        return hint
    h = hint.strip().upper()
    return LAW_ABBREV_ALIASES.get(h, hint)


def _variant_hints(hint: str) -> List[str]:
    if not hint:
        return []
    variants: Set[str] = set()
    variants.add(hint)
    h_upper = hint.strip().upper()
    if h_upper in LAW_ABBREV_ALIASES:
        variants.add(LAW_ABBREV_ALIASES[h_upper])
    return list(variants)


def _known_abbrev_matches(cit_upper: str, db_title: str) -> bool:
    normalized_cit = _normalize_law_hint_alias(cit_upper)

    for candidate in (cit_upper, normalized_cit):
        keywords = KNOWN_ABBREV_KEYWORDS.get(candidate)
        if not keywords:
            continue

        excludes = KNOWN_ABBREV_EXCLUDES.get(candidate, [])

        title_norm = normalize_albanian(db_title)
        title_alt = title_norm.replace("ë", "e").replace("ç", "c")

        exclude_hit = False
        for ex in excludes:
            ex_alt = ex.replace("ë", "e").replace("ç", "c")
            if (ex in title_norm or ex_alt in title_norm
                    or ex in title_alt or ex_alt in title_alt):
                exclude_hit = True
                break
        if exclude_hit:
            continue

        all_matched = True
        for kw in keywords:
            kw_alt = kw.replace("ë", "e").replace("ç", "c")
            if not (kw in title_norm or kw_alt in title_norm
                    or kw in title_alt or kw_alt in title_alt):
                all_matched = False
                break

        if all_matched:
            return True

    return False


def _reason_priority(reason: str) -> int:
    if reason.startswith("international_treaty"):
        return 110
    if reason.startswith("number_match"):
        return 100
    if reason.startswith("compound_abbrev_exact"):
        return 99
    # V1.1: lcs (98) > partial (97) — ishin invertuar në V1.0.
    if reason.startswith("compound_abbrev_lcs"):
        return 98
    if reason.startswith("compound_abbrev_partial"):
        return 97
    if reason.startswith("full_name_match"):
        return 96
    if reason.startswith("abbrev_known"):
        return 95
    if reason.startswith("abbrev_alias"):
        return 94
    if reason.startswith("abbrev_generated_exact"):
        return 90
    if reason.startswith("abbrev_generated_prefix"):
        return 85
    if reason.startswith("abbrev_generated_partial"):
        return 80
    if reason.startswith("abbrev_match"):
        return 70
    if reason.startswith("keyword_match"):
        return 50
    return 0


def _title_matches_citation(db_title: str, citation_law_hint: str) -> Tuple[bool, str]:
    if not db_title or not citation_law_hint:
        return False, "empty"

    db_num = _extract_law_number_from_text(db_title)
    cit_num = _extract_law_number_from_text(citation_law_hint)
    if db_num and cit_num and db_num == cit_num:
        return True, f"number_match:{db_num}"

    cit_upper = citation_law_hint.upper().strip()
    is_abbrev_hint = bool(re.match(r'^[A-ZËÇ]{2,6}$', cit_upper))

    if is_abbrev_hint:
        for variant in _variant_hints(cit_upper):
            if _known_abbrev_matches(variant, db_title):
                tag = "abbrev_known" if variant == cit_upper else f"abbrev_alias:{cit_upper}→{variant}"
                return True, f"{tag}:{variant}"

    if is_abbrev_hint:
        generated = _generate_abbreviation_from_title(db_title)
        if generated:
            if cit_upper == generated:
                return True, f"abbrev_generated_exact:{cit_upper}"
            if len(cit_upper) >= 3 and len(generated) >= 3:
                if abs(len(cit_upper) - len(generated)) <= 1 and generated.startswith(cit_upper):
                    return True, f"abbrev_generated_prefix:{cit_upper}~{generated}"

    if is_abbrev_hint:
        db_upper = db_title.upper()
        for variant in _variant_hints(cit_upper):
            pattern = r'\b' + re.escape(variant) + r'\b'
            if re.search(pattern, db_upper):
                tag = "abbrev_match" if variant == cit_upper else f"abbrev_match_alias:{cit_upper}→{variant}"
                return True, f"{tag}:{variant}"

    if not is_abbrev_hint and len(cit_upper) >= 5:
        db_upper = db_title.upper()
        pattern = r'\b' + re.escape(cit_upper) + r'\b'
        if re.search(pattern, db_upper):
            return True, f"full_name_match:{cit_upper}"

    if _is_compound_abbrev_hint(citation_law_hint):
        matched, reason = _compound_abbrev_matches(citation_law_hint, db_title)
        if matched:
            return True, reason

    db_kw = _extract_keywords(db_title) - KEYWORD_MATCH_STOPWORDS
    cit_kw = _extract_keywords(citation_law_hint) - KEYWORD_MATCH_STOPWORDS

    if cit_kw:
        overlap = db_kw & cit_kw
        min_overlap = 1 if len(cit_kw) <= 1 else 2
        if len(overlap) >= min_overlap:
            return True, f"keyword_match:{sorted(overlap)[:3]}"

    return False, "no_match"