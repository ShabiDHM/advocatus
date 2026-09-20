# FILE: backend/app/services/document_review/precedent_search/helpers.py
# PHOENIX PROTOCOL - PRECEDENT SEARCH HELPERS V2.2
# V2.2: format_result() shton topic_id, topic_label, topic_keywords.

import re
import math
import logging
from typing import List, Dict, Any, Optional

from .config import (
    COVER_PAGE_TOKENS,
    PRECEDENT_MAX_EXCERPT_CHARS,
    PRECEDENT_ENRICH_TOPIC,
)

logger = logging.getLogger(__name__)


# ===========================================================================
# NORMALIZIM
# ===========================================================================

def normalize_for_match(text: str) -> str:
    """Lowercase + heq diakritikat per krahasim."""
    if not text:
        return ""
    import unicodedata
    text = text.lower()
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    return text


# ===========================================================================
# FILTRA
# ===========================================================================

def is_real_case_number(case_number: str) -> bool:
    """Kontrollo nese case_number eshte numer real lende (jo kopertine)."""
    if not case_number:
        return False

    cn_lower = case_number.lower().strip()

    for token in COVER_PAGE_TOKENS:
        if token in cn_lower:
            return False

    if not re.search(r'\d', case_number):
        return False

    if len(case_number.strip()) < 4:
        return False

    return True


# ===========================================================================
# COSINE
# ===========================================================================

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm_a = math.sqrt(sum(a * a for a in vec1))
    norm_b = math.sqrt(sum(b * b for b in vec2))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# ===========================================================================
# FORMATIM
# ===========================================================================

def format_excerpt(
    text: str,
    max_chars: int = PRECEDENT_MAX_EXCERPT_CHARS,
) -> str:
    if not text:
        return ""
    clean = re.sub(r'\s+', ' ', text).strip()
    if len(clean) <= max_chars:
        return clean
    truncated = clean[:max_chars].rsplit(' ', 1)[0]
    return truncated + "..."


def extract_real_page(doc: Dict[str, Any]) -> int:
    p = doc.get("actual_page") or doc.get("page") or 1
    try:
        return int(p)
    except (ValueError, TypeError):
        return 1


def format_result(
    doc: Dict[str, Any],
    cosine_sim: Optional[float] = None,
    rerank_score: Optional[float] = None,
    rrf_score: Optional[float] = None,
    search_source: Optional[str] = None,
) -> Dict[str, Any]:
    """
    V2.2: Formaton rezultatin final + enrichment me topic.

    - similarity = cosine (0-1) NESE ekziston; 0.0 nese ka vetem rerank.
    - rerank_score = score DeepSeek (0-10) NESE ekziston.
    - search_source = "vector" / "text" / "both" / "fallback_cosine".
    - rrf_score = score fusion (brenda 0-0.05).
    - topic_id / topic_label / topic_keywords (V2.2, opsionale).
    """
    result = {
        "case_number": str(
            doc.get("case_number") or doc.get("title") or "?"
        ).strip(),
        "text_excerpt": format_excerpt(doc.get("text") or ""),
        "page": extract_real_page(doc),
        "source": str(doc.get("source") or "?").strip(),
        "similarity": round(float(cosine_sim), 4) if cosine_sim is not None else 0.0,
        "chunk_id": str(doc.get("chunk_id") or doc.get("_id") or "?"),
    }

    if rerank_score is not None:
        result["rerank_score"] = round(float(rerank_score), 2)

    if rrf_score is not None:
        result["rrf_score"] = round(float(rrf_score), 5)

    if search_source:
        result["search_source"] = search_source

    # V2.2: Enrichment me topic
    if PRECEDENT_ENRICH_TOPIC:
        topic_id = doc.get("topic_id")
        topic_label = doc.get("topic_label")
        topic_keywords = doc.get("topic_keywords")

        if topic_label:
            result["topic_id"] = topic_id
            result["topic_label"] = str(topic_label).strip()
            if topic_keywords and isinstance(topic_keywords, list):
                result["topic_keywords"] = topic_keywords

    return result