# FILE: backend/app/services/rag/text_utils.py
# PHOENIX PROTOCOL - RAG TEXT UTILS V1.0
# V1.0: EKSTRAKTUAR nga albanian_rag_service.py V282.25.
#       Përmban:
#       - GLOBAL_SEARCH_TRIGGERS + _user_wants_global_search
#       - Stemming i thjeshtë shqip + _words_match
#       - _MATCH_STOPWORDS + _extract_meaningful_words
#       - _detect_relevant_documents (query-aware doc filtering)
#       Zero varësi nga AlbanianRAGService.

import re
from typing import List, Dict, Any, Tuple


# ═══════════════════════════════════════════════════════════════════════════
# GLOBAL SEARCH TRIGGERS
# ═══════════════════════════════════════════════════════════════════════════

GLOBAL_SEARCH_TRIGGERS = [
    "precedent", "precedente", "precedentë",
    "jurisprudenc",
    "gjykata supreme", "gjykatës supreme",
    "praktikë gjyqësore", "praktike gjyqesore", "praktikën gjyqësore",
    "vendime gjyqësore",
    "aktgjykim supreme",
    "mendim juridik",
    "qëndrim parimor", "qendrim parimor",
]


def _user_wants_global_search(query_lower: str) -> bool:
    return any(trigger in query_lower for trigger in GLOBAL_SEARCH_TRIGGERS)


# ═══════════════════════════════════════════════════════════════════════════
# STEMMING I THJESHTË PËR SHQIP
# ═══════════════════════════════════════════════════════════════════════════

_STEM_SUFFIXES = [
    "imit", "imin", "imi", "im",
    "jen", "jes", "jet", "je",
    "esit", "esin", "esa", "esë", "es", "ës",
    "ave", "ava", "eve", "eva",
    "in", "ën", "un", "it", "ës", "së",
    "ja", "je", "a", "i", "u", "e", "ë",
]


def _stem_albanian(word: str) -> str:
    if not word or len(word) < 4:
        return word.lower()
    w = word.lower()
    for suf in _STEM_SUFFIXES:
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[:-len(suf)]
    return w


def _words_match(w1: str, w2: str) -> bool:
    if not w1 or not w2:
        return False
    s1 = _stem_albanian(w1)
    s2 = _stem_albanian(w2)
    if s1 == s2:
        return True
    if len(s1) >= 4 and len(s2) >= 4:
        if s1 in s2 or s2 in s1:
            return True
        if s1[:4] == s2[:4]:
            return True
    return False


_MATCH_STOPWORDS = {
    "dokument", "dokumente", "dokumentet", "dokumenti", "dokumentin",
    "lenda", "lende", "lenden", "lendja", "fashikull", "fashikulli",
    "shkresa", "shkresat", "shkresen",
    "trego", "thuaj", "thoni", "themi", "flas", "flitet",
    "refuzimi", "refuzim", "ankesa", "ankes", "aktakuza", "aktakuzes",
    "kerkesa", "kerkes", "vendimi", "vendim", "aktvendim",
    "për", "per", "me", "nga", "në", "ne", "të", "te",
    "eshte", "është", "jane", "janë", "ishte", "ishin",
    "cili", "cila", "cilin", "cilat", "kush", "cfare", "çfarë",
    "kam", "kemi", "keni", "kanë", "kane",
    "kjo", "ky", "keta", "keto", "ato", "ata",
    "gjith", "gjithë", "gjithe", "krejt",
    "pse", "si", "ku", "kur",
}


def _extract_meaningful_words(text: str, min_len: int = 5) -> set:
    raw = re.findall(r'\b\w{' + str(min_len) + r',}\b', text.lower())
    return {w for w in raw if w not in _MATCH_STOPWORDS}


def _detect_relevant_documents(
    query: str,
    documents: List[Dict[str, Any]],
    max_match: int = 3,
) -> Tuple[List[Dict[str, Any]], bool]:
    if not documents or not query:
        return documents, False

    query_words = _extract_meaningful_words(query, min_len=5)
    if not query_words:
        return documents, False

    matched = []
    for doc in documents:
        fname = (doc.get("file_name") or doc.get("title") or "").lower()
        fname_clean = re.sub(r'[._\-]+', ' ', fname)
        fname_words = _extract_meaningful_words(fname_clean, min_len=4)

        for qw in query_words:
            if any(_words_match(qw, fw) for fw in fname_words):
                matched.append(doc)
                break

    if 1 <= len(matched) <= max_match:
        return matched, True

    return documents, False