# FILE: backend/app/services/document_review/mongo_verifier/__init__.py
# PHOENIX PROTOCOL - MONGO VERIFIER PACKAGE V1.1 (V2.12 modular)
#
# V1.1: Shtuar `external_registry` — burimet ndërkombëtare nga JSON.
#
# Struktura:
#   config.py             — Konstantet + JSON-loaded defaults
#   external_registry.py  — V1.1: Burimet eksterne (KEDNJ, OKB, Hagë) nga JSON
#   text_utils.py         — TOC detection, keyword extraction, serialize
#   abbreviations.py      — Generation + LCS + compound matching
#   title_matching.py     — Krahasim titulli DB vs citim
#   successor_laws.py     — Successor lookup + resolution
#   articles.py           — Verifikim nenesh + fallback + external
#   laws.py               — Verifikim numrash ligjesh
#   case_numbers.py       — Verifikim numrash lendesh
#   orchestrator.py       — verify_all (pika hyrëse)

from .config import (
    ABBREV_SKIP_WORDS,
    LAW_ABBREV_ALIASES,
    KNOWN_ABBREV_KEYWORDS,
    KNOWN_ABBREV_EXCLUDES,
    KEYWORD_MATCH_STOPWORDS,
    LAW_SUCCESSOR_MAP,
)
from .external_registry import (
    find_external_source,
    get_all_external_sources,
    clear_registry_cache,
)
from .articles import verify_articles, _verify_single_article
from .laws import verify_law_numbers
from .case_numbers import verify_case_numbers
from .orchestrator import verify_all

__version__ = "2.13.0"

__all__ = [
    # Public API
    "verify_all",
    "verify_articles",
    "verify_law_numbers",
    "verify_case_numbers",
    "_verify_single_article",
    # External registry
    "find_external_source",
    "get_all_external_sources",
    "clear_registry_cache",
    # Konstantet (për testime / debug)
    "ABBREV_SKIP_WORDS",
    "LAW_ABBREV_ALIASES",
    "KNOWN_ABBREV_KEYWORDS",
    "KNOWN_ABBREV_EXCLUDES",
    "KEYWORD_MATCH_STOPWORDS",
    "LAW_SUCCESSOR_MAP",
]