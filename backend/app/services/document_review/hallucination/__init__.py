# FILE: backend/app/services/document_review/hallucination/__init__.py
# PHOENIX PROTOCOL - HALLUCINATION PACKAGE V1.25
# Public API re-exports — TË GJITHA funksionet që ekzistonin në
# hallucination_checker.py V1.24 mbeten të aksesueshme.
# Importuesit mund të përdorin:
#   from app.services.document_review.hallucination import check_all_sections
# ose (backward compat):
#   from app.services.document_review.hallucination_checker import check_all_sections

from .checker import HallucinationChecker, check_all_sections

from .constants import (
    CASE_NUMBER_PREFIXES,
    COMMON_ALBANIAN_UPPERCASE_WORDS,
    COMMON_HEADING_WORDS,
    ROLE_AWARE_SECTIONS,
    AMBIGUOUS_LAW_ABBREVS,
    ALBANIAN_CASE_NORMALIZATIONS,
    SUGGESTION_CONTEXT_KEYWORDS,
)

from .regexes import (
    LAW_NAME_WITH_NUMBER_RE,
    ABBREV_REPLACEMENT_RE,
    ABBREV_WITH_LAW_NUMBER_RE,
    STRICT_LAW_OUTPUT_PATTERN,
)

from .normalize import (
    normalize_law_name as _normalize_law_name,
    normalize_law_num as _normalize_law_num,
    is_valid_law_output as _is_valid_law_output,
    safe_normalize_law as _safe_normalize_law,
    normalize_precedent_case as _normalize_precedent_case,
    split_article_numbers as _split_article_numbers,
    get_globally_allowed_laws as _get_globally_allowed_laws,
    KNOWN_LAW_NAME_NUMBER_MAP,
    NORMALIZED_KNOWN_LAW_MAP as _NORMALIZED_KNOWN_LAW_MAP,
)

from .extract import (
    extract_dates_iso,
    extract_articles,
    extract_laws,
    extract_cases,
    extract_abbrevs,
    extract_law_numbers_from_title_strict as _extract_law_numbers_from_title_strict,
    has_real_citation_context as _has_real_citation_context,
    has_real_article_context as _has_real_article_context,
    find_snippet as _find_snippet,
    iso_to_albanian_date as _iso_to_albanian_date,
    # Backward-compat aliases me underscore:
    _extract_dates_iso,
)

from .successors import (
    scan_dict_for_laws as _scan_dict_for_laws,
    collect_successor_laws as _collect_successor_laws,
)


# ═══════════════════════════════════════════════════════════════════════════
# BACKWARD-COMPAT ALIASES (me underscore si versioni i vjetër)
# ═══════════════════════════════════════════════════════════════════════════

_extract_articles = extract_articles
_extract_laws = extract_laws
_extract_cases = extract_cases
_extract_abbrevs = extract_abbrevs


__all__ = [
    # Klasa + API kryesore
    "HallucinationChecker",
    "check_all_sections",
    # Constants
    "CASE_NUMBER_PREFIXES",
    "COMMON_ALBANIAN_UPPERCASE_WORDS",
    "COMMON_HEADING_WORDS",
    "ROLE_AWARE_SECTIONS",
    "AMBIGUOUS_LAW_ABBREVS",
    "ALBANIAN_CASE_NORMALIZATIONS",
    "SUGGESTION_CONTEXT_KEYWORDS",
    # Regexes
    "LAW_NAME_WITH_NUMBER_RE",
    "ABBREV_REPLACEMENT_RE",
    "ABBREV_WITH_LAW_NUMBER_RE",
    "STRICT_LAW_OUTPUT_PATTERN",
    # Normalize
    "_normalize_law_name",
    "_normalize_law_num",
    "_is_valid_law_output",
    "_safe_normalize_law",
    "_normalize_precedent_case",
    "_split_article_numbers",
    "_get_globally_allowed_laws",
    "KNOWN_LAW_NAME_NUMBER_MAP",
    "_NORMALIZED_KNOWN_LAW_MAP",
    # Extract
    "extract_dates_iso",
    "extract_articles",
    "extract_laws",
    "extract_cases",
    "extract_abbrevs",
    "_extract_dates_iso",
    "_extract_articles",
    "_extract_laws",
    "_extract_cases",
    "_extract_abbrevs",
    "_extract_law_numbers_from_title_strict",
    "_has_real_citation_context",
    "_has_real_article_context",
    "_find_snippet",
    "_iso_to_albanian_date",
    # Successors
    "_scan_dict_for_laws",
    "_collect_successor_laws",
]