# FILE: backend/app/services/document_review/mongo_verifier/successor_laws.py
# PHOENIX PROTOCOL - MONGO VERIFIER / SUCCESSOR LAWS V1.0 (V2.12 modular)
# Ekstraktuar nga mongo_verifier.py V2.11 (pa ndryshim logjike).

import logging
import re
from typing import Any, Dict, Optional

from ..helpers import normalize_albanian
from .config import (
    LEGAL_KB_COLLECTION,
    KEYWORD_MATCH_STOPWORDS,
    LAW_SUCCESSOR_MAP,
)
from .text_utils import (
    _extract_law_number_from_text,
    _extract_keywords,
    _looks_like_toc,
    _serialize_doc,
)

logger = logging.getLogger(__name__)


def _get_successor_law(law_hint: str) -> Optional[Dict[str, str]]:
    if not law_hint:
        return None
    law_num = _extract_law_number_from_text(law_hint)
    if not law_num:
        return None
    return LAW_SUCCESSOR_MAP.get(law_num)


def _try_successor_law(
    db,
    article_number: str,
    paragraph: Optional[str],
    original_hint: str,
    successor_info: Dict[str, str],
) -> Optional[Dict[str, Any]]:
    successor_num = successor_info.get("successor", "")
    if not successor_num:
        return None
    try:
        collection = db[LEGAL_KB_COLLECTION]
        article_variants = [article_number, f"{article_number}."]
        try:
            article_variants.append(int(article_number))
        except (ValueError, TypeError):
            pass

        query = {
            "is_article": True,
            "article_number": {"$in": article_variants},
            "law_title": {"$regex": re.escape(successor_num).replace("/", r"\s*[\/\-_\s]?\s*"), "$options": "i"},
        }
        candidates = list(collection.find(query, {
            "law_title": 1, "article_number": 1, "source": 1,
            "text": 1, "chunk_index": 1, "page": 1,
        }).limit(10))

        if not candidates:
            # V2.10 (H1): NUK hardcode-ojmë fjalë kyçe specifike domain-i.
            # I nxjerrim DINAMIKISHT nga successor_info["name"].
            law_name = (successor_info.get("name") or "").strip()
            name_kw = _extract_keywords(law_name) - KEYWORD_MATCH_STOPWORDS

            if name_kw:
                alt_query = {
                    "is_article": True,
                    "article_number": {"$in": article_variants},
                }
                alt_candidates = list(collection.find(alt_query, {
                    "law_title": 1, "article_number": 1, "source": 1,
                    "text": 1, "chunk_index": 1, "page": 1,
                }).limit(20))

                MIN_SUCCESSOR_KEYWORD_OVERLAP = 2

                for c in alt_candidates:
                    title_norm = normalize_albanian(c.get("law_title", ""))
                    title_kw = _extract_keywords(title_norm)

                    if not title_kw:
                        continue

                    overlap = name_kw & title_kw
                    if len(overlap) >= MIN_SUCCESSOR_KEYWORD_OVERLAP:
                        candidates.append(c)
                        if len(candidates) >= 10:
                            break

        if not candidates:
            return None

        non_toc = [c for c in candidates if not _looks_like_toc(c.get("text", ""))]
        pool = non_toc if non_toc else candidates
        best_doc = max(pool, key=lambda c: len(c.get("text", "")))

        return {
            "article_number": article_number,
            "paragraph": paragraph,
            "law_hint": original_hint,
            "exists": True,
            "matched_doc": _serialize_doc(best_doc),
            "match_reason": f"found_in_successor_law:{original_hint}→{successor_num}",
            "candidates_checked": len(candidates),
            "toc_filtered": len(candidates) - len(non_toc),
            "suggested_replacement": {
                "old_law": original_hint,
                "new_law": successor_num,
                "new_law_name": successor_info.get("name", ""),
                "note": successor_info.get("note", ""),
            },
        }
    except Exception as e:
        logger.warning(f"⚠️ [_try_successor_law] Error: {e}")
        return None