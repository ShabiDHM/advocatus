# FILE: backend/app/services/document_review/mongo_verifier/config.py
# PHOENIX PROTOCOL - MONGO VERIFIER / CONFIG V1.0 (V2.12 modular)
# Ekstraktuar nga mongo_verifier.py V2.11 (pa ndryshim logjike).

from typing import Dict, List, Set

from ..constants import (
    LEGAL_KB_COLLECTION,
    CASE_LAW_COLLECTION,
    ALBANIAN_STOPWORDS,
)
from ..dynamic_config import (
    get_law_successors,
    get_known_abbrev_keywords,
    get_known_abbrev_excludes,
)


# ═══════════════════════════════════════════════════════════════════════════
# ABBREV_SKIP_WORDS
# ═══════════════════════════════════════════════════════════════════════════

ABBREV_SKIP_WORDS: Set[str] = {
    "për", "per", "dhe", "ose", "me", "në", "ne", "nga", "ndaj",
    "të", "te", "e", "i", "së", "se", "si", "ka",
    "nr", "numri", "numrit", "numër", "numer",
    "republikës", "republike", "republikë",
    "kosovës", "kosove", "kosovë",
    "këtij", "ketij", "kësaj", "kesaj",
    "gjykata", "gjykatës", "gjykate", "gjykatë",
    "vendimi", "vendimit", "vendim",
    "aktgjykim", "aktgjykimi",
    "aktvendim", "aktvendimi",
    "lënda", "lenda", "lëndës", "lendes",
    "rasti", "rastit", "rast",
    "pala", "palë", "pales", "palës", "palët", "palet",
    "apelit", "apeli", "themelore", "supreme",
}


# ═══════════════════════════════════════════════════════════════════════════
# LAW_ABBREV_ALIASES
# ═══════════════════════════════════════════════════════════════════════════

LAW_ABBREV_ALIASES: Dict[str, str] = {
    "KPPRK": "KPK",
    "KPPK":  "KPK",
    "KPK":   "KPK",
    "KPRK":  "KPRK",
    "KPRKS": "KPRK",
}


# ═══════════════════════════════════════════════════════════════════════════
# KNOWN_ABBREV_KEYWORDS — JSON-loaded (H4)
# ═══════════════════════════════════════════════════════════════════════════

_DEFAULT_KNOWN_ABBREV_KEYWORDS: Dict[str, List[str]] = {
    "LMDHF": ["ligj", "mbrojtj", "dhun", "familj"],
    "LMD":   ["ligj", "marrëdhënie", "detyrim"],
    "LPK":   ["ligj", "procedur", "kontestim"],
    "KPRK":  ["kodi", "penal"],
    "KPK":   ["kodi", "procedur", "penal"],
    "KPPRK": ["kodi", "procedur", "penal"],
    "LFK":   ["ligj", "familj"],
    "LSHT":  ["ligj", "shoqëri", "tregtar"],
    "KRK":   ["kushtetut"],
}

KNOWN_ABBREV_KEYWORDS: Dict[str, List[str]] = get_known_abbrev_keywords(
    _DEFAULT_KNOWN_ABBREV_KEYWORDS
)


# ═══════════════════════════════════════════════════════════════════════════
# KNOWN_ABBREV_EXCLUDES — JSON-loaded (H5)
# ═══════════════════════════════════════════════════════════════════════════

_DEFAULT_KNOWN_ABBREV_EXCLUDES: Dict[str, List[str]] = {
    "KPRK":  ["procedur"],
    "KPRKS": ["procedur"],
    "KPK":   [],
    "KPPRK": [],
    "LMDHF": [],
    "LMD":   [],
    "LPK":   [],
    "LFK":   [],
    "LSHT":  [],
    "KRK":   [],
}

KNOWN_ABBREV_EXCLUDES: Dict[str, List[str]] = get_known_abbrev_excludes(
    _DEFAULT_KNOWN_ABBREV_EXCLUDES
)


# ═══════════════════════════════════════════════════════════════════════════
# KEYWORD_MATCH_STOPWORDS
# ═══════════════════════════════════════════════════════════════════════════

KEYWORD_MATCH_STOPWORDS: Set[str] = {
    "republikes", "republike", "republika", "republik",
    "kosoves", "kosove", "kosova", "kosov",
    "shtetit", "shteti", "shtet",
    "kodi", "kodit", "kodet", "kod",
    "ligji", "ligjit", "ligje", "ligjet", "ligj",
    "neni", "nenit", "nenet", "nenin", "nen",
    "kushtetuta", "kushtetutes", "kushtetute",
    "konventa", "konventes", "konvente",
    "numri", "numrit", "numer",
}


# ═══════════════════════════════════════════════════════════════════════════
# INTERNATIONAL TREATIES
# ═══════════════════════════════════════════════════════════════════════════

INTERNATIONAL_TREATIES: Dict[str, Dict[str, str]] = {
    "KEDNJ": {
        "canonical_name": "Konventa Evropiane për të Drejtat e Njeriut (KEDNJ)",
        "constitutional_basis": "Neni 22 i Kushtetutës së Republikës së Kosovës",
        "note": (
            "Konventa është pjesë e rendit kushtetues të Kosovës, "
            "me prioritet mbi ligjet vendore (Neni 22 i Kushtetutës)."
        ),
    },
    "OKB_FEMIJES": {
        "canonical_name": "Konventa e OKB-së për të Drejtat e Fëmijës",
        "constitutional_basis": "Neni 22 i Kushtetutës së Republikës së Kosovës",
        "note": (
            "Konventa është pjesë e rendit kushtetues të Kosovës, "
            "me prioritet mbi ligjet vendore (Neni 22 i Kushtetutës)."
        ),
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# LAW_SUCCESSOR_MAP — JSON-loaded (H2)
# ═══════════════════════════════════════════════════════════════════════════

_DEFAULT_LAW_SUCCESSOR_MAP: Dict[str, Dict[str, str]] = {
    "03/L-182": {
        "successor": "08/L-185",
        "name": "Ligji për Parandalimin dhe Mbrojtjen nga Dhuna në Familje, Dhuna Ndaj Grave dhe Dhuna në Bazë Gjinore",
        "note": "LMDHF u zëvendësua në vitin 2023 me versionin e ri 08/L-185",
    },
    "2004/32": {
        "successor": "2004/32",
        "name": "Ligji për Familjen i Kosovës",
        "note": "Ligji Nr. 2004/32 — version i konsoliduar",
    },
}

LAW_SUCCESSOR_MAP: Dict[str, Dict[str, str]] = get_law_successors(
    _DEFAULT_LAW_SUCCESSOR_MAP
)


# Re-export për komoditet
__all__ = [
    "LEGAL_KB_COLLECTION",
    "CASE_LAW_COLLECTION",
    "ALBANIAN_STOPWORDS",
    "ABBREV_SKIP_WORDS",
    "LAW_ABBREV_ALIASES",
    "KNOWN_ABBREV_KEYWORDS",
    "KNOWN_ABBREV_EXCLUDES",
    "KEYWORD_MATCH_STOPWORDS",
    "INTERNATIONAL_TREATIES",
    "LAW_SUCCESSOR_MAP",
]