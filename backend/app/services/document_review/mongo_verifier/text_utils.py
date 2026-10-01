# FILE: backend/app/services/document_review/mongo_verifier/text_utils.py
# PHOENIX PROTOCOL - MONGO VERIFIER / TEXT UTILS V1.0 (V2.12 modular)
# Ekstraktuar nga mongo_verifier.py V2.11 (pa ndryshim logjike).

import re
from typing import Any, Dict, Optional, Set

from ..helpers import normalize_albanian
from .config import ALBANIAN_STOPWORDS


MAX_TEXT_EXCERPT_CHARS = 3000


def _extract_law_number_from_text(text: str) -> Optional[str]:
    if not text:
        return None
    m = re.search(
        r'(\d{2})\s*[\/\-_\s]?\s*L\s*[\/\-_\s]?\s*(\d{2,4})',
        text, re.IGNORECASE,
    )
    if m:
        return f"{m.group(1)}/L-{m.group(2)}"
    m = re.search(r'\b(\d{4})\s*[\/\-]\s*(\d{1,3})\b', text)
    if m:
        return f"{m.group(1)}/{m.group(2)}"
    return None


def _extract_keywords(text: str, min_length: int = 4) -> Set[str]:
    if not text:
        return set()
    normalized = normalize_albanian(text)
    words = re.findall(rf'\b[a-z]{{{min_length},}}\b', normalized)
    return set(w for w in words if w not in ALBANIAN_STOPWORDS)


def _looks_like_toc(text: str) -> bool:
    if not text:
        return False
    stripped = text.strip()
    if len(stripped) < 20:
        return False
    dotted_matches = re.findall(r'\.{5,}', stripped)
    if len(dotted_matches) >= 1 and len(stripped) < 400:
        return True
    toc_lines = re.findall(r'\.{3,}\s*\d+\s*$', stripped, re.MULTILINE)
    if len(toc_lines) >= 2:
        return True
    lines = [l for l in stripped.split("\n") if l.strip()]
    if len(lines) >= 3:
        dotted_ending = sum(1 for l in lines if re.search(r'\.{3,}\s*\d+\s*$', l))
        if dotted_ending / len(lines) > 0.4:
            return True
    return False


def _serialize_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    if not doc:
        return {}
    full_text = doc.get("text") or ""
    return {
        "law_title": doc.get("law_title", ""),
        "article_number": str(doc.get("article_number", "")),
        "source": doc.get("source", ""),
        "text_excerpt": full_text[:MAX_TEXT_EXCERPT_CHARS],
        "text_truncated": len(full_text) > MAX_TEXT_EXCERPT_CHARS,
        "text_full_length": len(full_text),
        "page": doc.get("page"),
    }