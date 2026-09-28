# FILE: backend/app/services/document_review/mongo_verifier/__init__.py
# PHOENIX PROTOCOL - MONGO VERIFIER PACKAGE V1.0 (V2.12 modular)
# Modularizim i mongo_verifier.py V2.11 — zero ndryshim logjike.
#
# Struktura:
#   config.py           — Konstantet + JSON-loaded defaults
#   text_utils.py       — TOC detection, keyword extraction, serialize
#   abbreviations.py    — Generation + LCS + compound matching
#   title_matching.py   — Krahasim titulli DB vs citim
#   successor_laws.py   — Successor lookup + resolution
#   articles.py         — Verifikim nenesh + fallback
#   laws.py             — Verifikim numrash ligjesh
#   case_numbers.py     — Verifikim numrash lendesh
#   orchestrator.py     — verify_all (pika hyrëse)

from .config import (
    ABBREV_SKIP_WORDS,
    LAW_ABBREV_ALIASES,
    KNOWN_ABBREV_KEYWORDS,
    KNOWN_ABBREV_EXCLUDES,
    KEYWORD_MATCH_STOPWORDS,
    INTERNATIONAL_TREATIES,
    LAW_SUCCESSOR_MAP,
)
from .articles import verify_articles, _verify_single_article
from .laws import verify_law_numbers
from .case_numbers import verify_case_numbers
from .orchestrator import verify_all

__version__ = "2.12.0"

__all__ = [
    # Public API
    "verify_all",
    "verify_articles",
    "verify_law_numbers",
    "verify_case_numbers",
    "_verify_single_article",
    # Konstantet (për testime / debug)
    "ABBREV_SKIP_WORDS",
    "LAW_ABBREV_ALIASES",
    "KNOWN_ABBREV_KEYWORDS",
    "KNOWN_ABBREV_EXCLUDES",
    "KEYWORD_MATCH_STOPWORDS",
    "INTERNATIONAL_TREATIES",
    "LAW_SUCCESSOR_MAP",
]