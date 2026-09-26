# FILE: backend/app/services/rag/chat_query_extractor.py
# PHOENIX PROTOCOL - CHAT QUERY EXTRACTOR V1.3
# V1.3: FIX — Multi-word pranon edhe Title Case ("Kodi Penal", "Kodi i Procedurës"),
#       jo vetëm ALL CAPS ("KODI PENAL"). Më parë "Kodi Penal" kthehej si "Kodi".
# V1.2: Fallback multi-word (KODI PENAL → "KODI PENAL", jo vetëm "PENAL").
# V1.1: Fallback për emra ligjesh standalone (KUSHTETUTA, KODI PENAL, ...).
# V1.0: Ekstraktim deterministik i query-t për pre-verifikim.

import re
import logging
from typing import Dict, Any, List

from ..document_review.citation_extractor import (
    extract_articles_with_context,
    extract_law_numbers,
    extract_abbreviations,
)

logger = logging.getLogger(__name__)


LEGAL_QUERY_KEYWORDS = {
    "neni", "nenit", "nenin", "nenet", "nenët", "nen",
    "ligji", "ligjit", "ligjin", "ligjet", "ligjeve",
    "kodi", "kodit", "kushtetuta", "kushtetutës",
    "dispozita", "dispozitë", "dispozitave", "paragrafi", "paragrafit",
    "gjykatë", "gjykata", "gjykate", "gjykatës",
    "precedent", "precedentët", "precedentëve", "precedenti",
    "padi", "padia", "ankim", "ankimi", "ankimit",
    "vendim", "vendimi", "vendimit", "aktgjykim", "aktvendim",
    "afat", "afati", "afatit", "procedurë", "procedura", "procedurës",
}

GENERAL_QUERY_KEYWORDS = {
    "precedent", "precedentët", "precedentëve", "precedenti",
    "praktikë", "praktika", "praktikës", "praktike",
    "raste", "rastet", "rasteve", "rasti",
    "të ngjashme", "te ngjashme",
    "si funksionon", "si veprohet", "si procedohet",
    "procedura", "procedurë", "procedurës",
}


_LAW_NAME_BLACKLIST = {
    "kjo", "ky", "ai", "ajo", "nje", "një", "ketij", "këtij", "kesaj", "kësaj",
    "cili", "cila", "cilit", "cilat",
    "dhe", "ose", "por", "nëse", "ndërsa", "ndersa",
}

_LAW_NAME_STOP_CONNECTORS = {
    "dhe", "ose", "por", "nëse", "ndersa", "ndërsa",
    "kur", "ku", "nga", "për", "per", "me",
    "ka", "kanë", "kane", "ishte", "është", "eshte",
}


def _extract_law_name_after_article(query: str) -> str:
    """
    V1.3: Nxjerr emrin e ligjit pas 'Neni X i/të/e ...'.
    Pranon edhe Title Case ("Kodi Penal") edhe ALL CAPS ("KODI PENAL").
    """
    m = re.search(
        r'\bNeni\s+\d+[\w\.\/]*\s+(?:i|të|te|e)\s+([A-Za-zËÇëç]{4,})',
        query,
        re.IGNORECASE,
    )
    if not m:
        return ""

    first_word = m.group(1).strip()
    if first_word.lower() in _LAW_NAME_BLACKLIST:
        return ""

    after_match = query[m.end():].strip()

    m2 = re.match(r'^([A-Za-zËÇëç]{3,})', after_match)
    if m2:
        second_word = m2.group(1).strip()
        if second_word.lower() not in _LAW_NAME_STOP_CONNECTORS:
            # V1.3: Prano Title Case OSE ALL CAPS (të dyja fjalët kapitalizuara)
            first_cap = first_word[:1].isupper()
            second_cap = second_word[:1].isupper()
            if first_cap and second_cap:
                return f"{first_word} {second_word}"

    return first_word


def _is_legal_query(
    query_lower: str,
    articles: List[Dict[str, Any]],
    laws: List[Dict[str, Any]],
    abbrs: List[str],
) -> bool:
    if articles or laws or abbrs:
        return True
    words = set(query_lower.split())
    if words & LEGAL_QUERY_KEYWORDS:
        return True
    return False


def _has_general_query(query_lower: str) -> bool:
    for kw in GENERAL_QUERY_KEYWORDS:
        if kw in query_lower:
            return True
    return False


def extract_legal_query(query: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "articles": [],
        "laws": [],
        "abbreviations": [],
        "is_legal_query": False,
        "has_general_query": False,
        "original_query": query,
    }

    if not query or not query.strip():
        return result

    try:
        articles = extract_articles_with_context(query)
        laws = extract_law_numbers(query)
        abbrs = extract_abbreviations(query)
    except Exception as e:
        logger.warning(f"⚠️ [CHAT_QUERY_EXTRACTOR] Extract error: {e}")
        return result

    if articles:
        standalone_law = _extract_law_name_after_article(query)
        if standalone_law:
            for art in articles:
                current_hint = art.get("law_hint", "").strip()
                should_override = (
                    not current_hint
                    or (
                        standalone_law.upper().endswith(current_hint.upper())
                        and len(standalone_law) > len(current_hint)
                    )
                )
                if should_override:
                    art["law_hint"] = standalone_law
                    logger.info(
                        f"🔧 [CHAT_QUERY_EXTRACTOR V1.3] Override law_hint='{standalone_law}' "
                        f"(ishte '{current_hint}') për Neni {art.get('number')}"
                    )

    result["articles"] = articles
    result["laws"] = laws
    result["abbreviations"] = abbrs

    query_lower = query.lower()
    result["is_legal_query"] = _is_legal_query(query_lower, articles, laws, abbrs)
    result["has_general_query"] = _has_general_query(query_lower)

    logger.info(
        f"🔎 [CHAT_QUERY_EXTRACTOR V1.3] articles={len(articles)} "
        f"laws={len(laws)} abbrs={len(abbrs)} "
        f"is_legal={result['is_legal_query']} "
        f"has_general={result['has_general_query']}"
    )

    return result