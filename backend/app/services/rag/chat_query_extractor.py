# FILE: backend/app/services/rag/chat_query_extractor.py
# PHOENIX PROTOCOL - CHAT QUERY EXTRACTOR V1.2
# V1.2: Fallback multi-word (KODI PENAL → "KODI PENAL", jo vetëm "PENAL").
#       Override-on edhe kur citation_extractor ka kapur vetëm fjalën e fundit.
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


# ═══════════════════════════════════════════════════════════════════════════
# FJALË KYÇE
# ═══════════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════════
# V1.2: STANDALONE LAW NAME EXTRACTION (multi-word)
# ═══════════════════════════════════════════════════════════════════════════

_LAW_NAME_BLACKLIST = {
    "kjo", "ky", "ai", "ajo", "nje", "një", "ketij", "këtij", "kesaj", "kësaj",
    "cili", "cila", "cilit", "cilat",
    "dhe", "ose", "por", "nëse", "ndërsa", "ndersa",
}

# Fjalë që NUK duan të lidhen me fjalën para tyre (ndajnë emrin)
_LAW_NAME_STOP_CONNECTORS = {
    "dhe", "ose", "por", "nëse", "ndersa", "ndërsa",
    "kur", "ku", "nga", "për", "per", "me",
}


def _extract_law_name_after_article(query: str) -> str:
    """
    V1.2: Nxjerr emrin e ligjit pas 'Neni X i/të/e ...'.
    Kap edhe emra shumë-fjalësh ('KODI PENAL', 'KODI I PROCEDURËS PENALE').
    Dinamik — pa listë ligjesh.
    """
    # Kap fjalën e parë pas "Neni X i/e/të" — 4+ shkronja
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

    # V1.2: Provo të zgjeroj me fjalën pasardhëse (KODI PENAL, KODI NR)
    after_match = query[m.end():].strip()

    # Nëse fjala tjetër është gjithashtu ALL CAPS ose fjalë e madhe (ligj)
    m2 = re.match(r'^([A-Za-zËÇëç]{3,})', after_match)
    if m2:
        second_word = m2.group(1).strip()
        if second_word.lower() not in _LAW_NAME_STOP_CONNECTORS:
            # Vetëm nëse të dyja fjalët janë kapitalizuar ose ALL CAPS (emër ligji)
            if first_word.isupper() and second_word.isupper():
                return f"{first_word} {second_word}"

    return first_word


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _is_legal_query(
    query_lower: str,
    articles: List[Dict[str, Any]],
    laws: List[Dict[str, Any]],
    abbrs: List[str],
) -> bool:
    """Përcakto nëse query është pyetje ligjore."""
    if articles or laws or abbrs:
        return True
    words = set(query_lower.split())
    if words & LEGAL_QUERY_KEYWORDS:
        return True
    return False


def _has_general_query(query_lower: str) -> bool:
    """Përcakto nëse query ka pjesë të pavarur nga neni specifik."""
    for kw in GENERAL_QUERY_KEYWORDS:
        if kw in query_lower:
            return True
    return False


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def extract_legal_query(query: str) -> Dict[str, Any]:
    """
    Nxjerr informacion ligjor nga një query chat-i.

    Kthen:
        {
            "articles": [{number, paragraph, law_hint, context, sentence}, ...],
            "laws": [{number, name, context}, ...],
            "abbreviations": ["LPK", "LMDHF", ...],
            "is_legal_query": bool,
            "has_general_query": bool,
            "original_query": str,
        }
    """
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

    # ═══════════════════════════════════════════════════════════════════════
    # V1.2: FALLBACK — gjithmonë provo standalone, OVERRIDE nëse më specifik
    # ═══════════════════════════════════════════════════════════════════════
    if articles:
        standalone_law = _extract_law_name_after_article(query)
        if standalone_law:
            for art in articles:
                current_hint = art.get("law_hint", "").strip()
                # V1.2: Override nëse:
                #   - hint bosh, OSE
                #   - hint-i është vetëm 1 fjalë e emrit të plotë (p.sh. "PENAL" ⊂ "KODI PENAL")
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
                        f"🔧 [CHAT_QUERY_EXTRACTOR V1.2] Override law_hint='{standalone_law}' "
                        f"(ishte '{current_hint}') për Neni {art.get('number')}"
                    )

    result["articles"] = articles
    result["laws"] = laws
    result["abbreviations"] = abbrs

    query_lower = query.lower()
    result["is_legal_query"] = _is_legal_query(query_lower, articles, laws, abbrs)
    result["has_general_query"] = _has_general_query(query_lower)

    logger.info(
        f"🔎 [CHAT_QUERY_EXTRACTOR V1.2] articles={len(articles)} "
        f"laws={len(laws)} abbrs={len(abbrs)} "
        f"is_legal={result['is_legal_query']} "
        f"has_general={result['has_general_query']}"
    )

    return result