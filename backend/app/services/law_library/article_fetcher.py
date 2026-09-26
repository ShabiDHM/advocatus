# FILE: backend/app/services/law_library/article_fetcher.py
# PHOENIX PROTOCOL - ARTICLE FETCHER V1.1
# V1.1: FIX — Akronimi nxirret VETËM nga kllapa "(KPK)" ose "(LMD)".
#       Më parë `re.sub(r'[^A-Z]', '', clean.upper())` krijonte pattern-e
#       false-positive si "LNL", "KPKNRL" nga tituj normalë me numra.
# V1.0: Gjen tekstin e saktë të një neni nga MongoDB.

import re
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

LEGAL_KB_COLLECTION = "legal_knowledge_base"


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _normalize_article(article_number: str) -> str:
    """Nxjerr vetëm numrat nga artikulli (p.sh. 'Neni 5' → '5')."""
    if not article_number:
        return ""
    m = re.search(r'\d+(?:[\.\/]\d+)*', str(article_number))
    return m.group(0) if m else str(article_number).strip()


def _build_title_patterns(law_title: str) -> List[str]:
    """
    Ndërton disa regex-e për të gjetur ligjin në DB,
    pavarësisht formatimit (spaces, slash, dash).
    """
    if not law_title:
        return []

    clean = law_title.strip()
    patterns = [re.escape(clean)]

    # Provo të nxjerrësh numrin e ligjit: "03/L-182", "03 L 182", etj.
    m = re.search(r'(\d{2})\s*[\/\-_\s]?\s*L\s*[\/\-_\s]?\s*(\d{2,4})', clean, re.IGNORECASE)
    if m:
        part1, part2 = m.group(1), m.group(2)
        patterns.append(rf"\b{part1}\s*[\/\-_\s]?\s*L\s*[\/\-_\s]?\s*{part2}\b")
        patterns.append(rf"\b{part1}\s+L\s+{part2}\b")

    # V1.1: Akronimi VETËM nga kllapa — p.sh. "(KPK)", "(LMD)"
    # Nuk përdorim më re.sub(r'[^A-Z]', '', ...) sepse krijonte false-positive.
    for abbrev in set(re.findall(r'\(([A-Z]{2,6})\)', clean)):
        patterns.append(rf"\b{re.escape(abbrev)}\b")

    return patterns


# ═══════════════════════════════════════════════════════════════════════════
# FETCH ARTICLE
# ═══════════════════════════════════════════════════════════════════════════

def fetch_article_from_db(
    db,
    law_title: str,
    article_number: str,
) -> Optional[Dict[str, Any]]:
    """
    Kthen tekstin e saktë të nenit nga MongoDB.

    Returns:
        {
            "law_title": "...",
            "article_number": "5",
            "source": "...",
            "text": "...",
            "page": 12,
        }
        ose None nëse nuk u gjet.
    """
    if db is None:
        logger.warning("⚠️ [ARTICLE_FETCHER] db is None")
        return None

    article_key = _normalize_article(article_number)
    if not article_key:
        logger.warning("⚠️ [ARTICLE_FETCHER] Empty article number")
        return None

    collection = db[LEGAL_KB_COLLECTION]

    # Variants: string + int + me pikë
    article_variants = [article_key, f"{article_key}."]
    try:
        article_variants.append(int(article_key))
    except (ValueError, TypeError):
        pass

    title_patterns = _build_title_patterns(law_title)

    for pattern in title_patterns:
        query = {
            "is_article": True,
            "article_number": {"$in": article_variants},
            "law_title": {"$regex": pattern, "$options": "i"},
        }

        docs = list(collection.find(query, {
            "law_title": 1,
            "article_number": 1,
            "source": 1,
            "text": 1,
            "page": 1,
            "page_number": 1,
            "actual_page": 1,
        }).sort("chunk_index", 1).limit(20))

        if docs:
            full_text = "\n\n".join(
                d.get("text", "") for d in docs if d.get("text")
            ).strip()

            if full_text:
                first = docs[0]
                page = (
                    first.get("actual_page")
                    or first.get("page")
                    or first.get("page_number")
                    or 1
                )
                try:
                    page = int(page)
                except (ValueError, TypeError):
                    page = 1

                logger.info(
                    f"✅ [ARTICLE_FETCHER] Found: {first.get('law_title')} — "
                    f"Neni {article_key}, {len(full_text)} chars, {len(docs)} chunks"
                )

                return {
                    "law_title": first.get("law_title", law_title),
                    "article_number": article_key,
                    "source": first.get("source", ""),
                    "text": full_text,
                    "page": page,
                    "chunks_count": len(docs),
                }

    logger.info(
        f"❌ [ARTICLE_FETCHER] Neni {article_key} i '{law_title}' "
        f"NUK u gjet në DB (provuan {len(title_patterns)} pattern-e)"
    )
    return None


def article_exists(db, law_title: str, article_number: str) -> bool:
    """Kontroll i shpejtë ekzistence."""
    return fetch_article_from_db(db, law_title, article_number) is not None