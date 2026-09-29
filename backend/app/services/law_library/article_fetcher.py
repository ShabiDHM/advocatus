# FILE: backend/app/services/law_library/article_fetcher.py
# PHOENIX PROTOCOL - ARTICLE FETCHER V1.3
#
# V1.3: FIX F1-F11 (auditim).
#   - F1:  Shtuar mbështetje për indeks (bëhet jashtë)
#   - F2:  Fallback me article-only nëse title nuk gjen
#   - F3:  Sub-article preservation (5/1)
#   - F4:  Akronim pa kllapa (KPK Nr. 06/L-074)
#   - F5:  Order deterministik për akronimet
#   - F6:  Sort me tie-breaker _id
#   - F7:  Page None (jo 1 fake)
#   - F8:  Limit configurable (jo 20 hardcoded)
#   - F9:  Kontroll is_article
#   - F10: Log context i plotë
#   - F11: article_exists = count_documents

import re
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

LEGAL_KB_COLLECTION = "legal_knowledge_base"

# F8: Configurable, jo hardcoded 20
DEFAULT_CHUNK_LIMIT = 100


def _normalize_article(article_number: str) -> str:
    """
    F3: Ruan sub-article (5/1 → "5/1").
    """
    if not article_number:
        return ""
    m = re.search(r'\d+(?:[\.\/]\d+)*', str(article_number))
    return m.group(0) if m else str(article_number).strip()


def _build_title_patterns(law_title: str) -> List[str]:
    """
    Ndërton regex-e për matching të ligjit.
    F4: Akronimi edhe pa kllapa (shfrytëzon "Nr." marker).
    F5: Order deterministik.
    """
    if not law_title:
        return []

    clean = law_title.strip()
    patterns = [re.escape(clean)]

    # Numri i ligjit (03/L-182, 03 L 182)
    m = re.search(
        r'(\d{2})\s*[\/\-_\s]?\s*L\s*[\/\-_\s]?\s*(\d{2,4})',
        clean, re.IGNORECASE,
    )
    if m:
        part1, part2 = m.group(1), m.group(2)
        patterns.append(rf"\b{part1}\s*[\/\-_\s]?\s*L\s*[\/\-_\s]?\s*{part2}\b")
        patterns.append(rf"\b{part1}\s+L\s+{part2}\b")

    # F4: Akronimi — nga kllapa OSE para "Nr."
    acronyms_from_parens = set(re.findall(r'\(([A-Z]{2,6})\b', clean))
    acronyms_from_nr = set(re.findall(r'\b([A-Z]{2,6})\s+(?:Nr|nr)\.?\s', clean))
    all_acronyms = sorted(acronyms_from_parens | acronyms_from_nr)   # F5: deterministic
    for abbrev in all_acronyms:
        patterns.append(rf"\b{re.escape(abbrev)}\b")

    return patterns


def fetch_article_from_db(
    db,
    law_title: str,
    article_number: str,
    chunk_limit: int = DEFAULT_CHUNK_LIMIT,
) -> Optional[Dict[str, Any]]:
    """
    Kthen tekstin e saktë të nenit nga MongoDB.
    F2: Fallback nëse title-pattern nuk gjen, provo article-only.
    """
    if db is None:
        logger.warning("[ARTICLE_FETCHER] db is None")
        return None

    article_key = _normalize_article(article_number)
    if not article_key:
        logger.warning("[ARTICLE_FETCHER] Empty article number")
        return None

    collection = db[LEGAL_KB_COLLECTION]

    # F3: Variants me sub-article
    article_variants: List[Any] = [article_key, f"{article_key}."]
    if "/" in article_key or "." in article_key:
        base = re.split(r'[/.]', article_key)[0]
        article_variants.extend([base, f"{base}."])
    try:
        article_variants.append(int(article_key))
    except (ValueError, TypeError):
        pass

    # Dedupe
    seen = set()
    unique_variants: List[Any] = []
    for v in article_variants:
        k = (type(v).__name__, str(v))
        if k not in seen:
            seen.add(k)
            unique_variants.append(v)

    projection = {
        "law_title": 1, "article_number": 1, "source": 1,
        "text": 1, "page": 1, "page_number": 1, "actual_page": 1,
        "is_article": 1,
    }

    title_patterns = _build_title_patterns(law_title)

    # F1: Query optimizuar — provon patterns njëherë
    for pattern in title_patterns:
        try:
            docs = list(
                collection.find(
                    {
                        "is_article": True,       # F9
                        "article_number": {"$in": unique_variants},
                        "law_title": {"$regex": pattern, "$options": "i"},
                    },
                    projection,
                )
                .sort([("chunk_index", 1), ("_id", 1)])   # F6
                .limit(chunk_limit)                        # F8
            )
        except Exception as e:
            logger.error(f"[ARTICLE_FETCHER] Query failed for pattern '{pattern}': {e}")
            continue

        result = _build_article_result(docs, article_key, law_title)
        if result:
            return result

    # F2: Fallback — article-only (pa filter titulli)
    try:
        docs = list(
            collection.find(
                {
                    "is_article": True,
                    "article_number": {"$in": unique_variants},
                },
                projection,
            )
            .sort([("chunk_index", 1), ("_id", 1)])
            .limit(chunk_limit)
        )
    except Exception as e:
        logger.error(f"[ARTICLE_FETCHER] Fallback query failed: {e}")
        docs = []

    # Vetëm nëse të gjitha docs i përkasin NJË ligji të vetëm — shmang ambiguity
    if docs:
        titles = {d.get("law_title") for d in docs if d.get("law_title")}
        if len(titles) == 1:
            result = _build_article_result(docs, article_key, law_title)
            if result:
                logger.info(
                    f"[ARTICLE_FETCHER] Fallback article-only: "
                    f"Neni {article_key} në '{list(titles)[0]}'"
                )
                return result
        else:
            logger.warning(
                f"[ARTICLE_FETCHER] Ambiguous: Neni {article_key} "
                f"gjendet në {len(titles)} ligje të ndryshme. Skip fallback."
            )

    logger.info(
        f"[ARTICLE_FETCHER] Neni {article_key} i '{law_title}' NUK u gjet "
        f"(provuan {len(title_patterns)} pattern-e)"
    )
    return None


def _build_article_result(
    docs: List[dict],
    article_key: str,
    fallback_title: str,
) -> Optional[Dict[str, Any]]:
    """Helper: ndërton result dict nga docs."""
    if not docs:
        return None

    full_text = "\n\n".join(
        d.get("text", "") for d in docs if d.get("text")
    ).strip()

    if not full_text:
        return None

    first = docs[0]

    # F7: Page None (jo fallback 1 fake)
    raw_page = (
        first.get("actual_page")
        or first.get("page")
        or first.get("page_number")
    )
    try:
        page: Optional[int] = int(raw_page) if raw_page is not None else None
    except (ValueError, TypeError):
        page = None

    logger.info(
        f"[ARTICLE_FETCHER] Found: {first.get('law_title')} — "
        f"Neni {article_key}, {len(full_text)} chars, {len(docs)} chunks"
    )

    return {
        "law_title": first.get("law_title", fallback_title),
        "article_number": article_key,
        "source": first.get("source", ""),
        "text": full_text,
        "page": page,
        "chunks_count": len(docs),
    }


def article_exists(db, law_title: str, article_number: str) -> bool:
    """F11: Ekzistencë e shpejtë (count_documents, jo full fetch)."""
    if db is None:
        return False
    article_key = _normalize_article(article_number)
    if not article_key:
        return False

    collection = db[LEGAL_KB_COLLECTION]
    try:
        count = collection.count_documents(
            {
                "is_article": True,
                "article_number": {"$in": [article_key, f"{article_key}."]},
            },
            limit=1,
        )
        return count > 0
    except Exception as e:
        logger.error(f"[ARTICLE_FETCHER] count failed: {e}")
        return False


__all__ = [
    "fetch_article_from_db",
    "article_exists",
]