# FILE: backend/app/services/synthesis/citation_extraction.py
# PHOENIX PROTOCOL - CITATION EXTRACTION V1.0
# Ekstraktuar nga synthesis_service.py V3.8 — ZERO ndryshim funksional.

import re
import logging
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import defaultdict
from bson import ObjectId

from .patterns import (
    LAW_NUMBER_PATTERN,
    LAW_ABBREVIATION_PATTERN,
    VERIFIED_ARTICLE_PATTERN,
    CITATION_WITH_LAW_PATTERN,
    LAW_WITH_NUMBER_PATTERN,
    SINGLE_ARTICLE_PATTERN,
    MULTI_ARTICLE_PATTERN,
)
from .constants import MAX_ARTICLE_DESCRIPTIONS, LAW_CONTEXT_WINDOW

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# GUARDRAIL #2b — Verified citations from documents
# ═══════════════════════════════════════════════════════════════════════════

def extract_verified_citations_from_documents(db, case_id: str) -> Dict[str, Any]:
    """
    Ekstraktim deterministik i citimeve (regex-based).

    Returns dict me:
        laws, articles, article_law_pairs, by_document, document_laws,
        total_laws, total_articles, total_pairs
    """
    laws: Set[str] = set()
    articles_by_doc: Dict[str, List[str]] = defaultdict(list)
    document_laws: Dict[str, Set[str]] = defaultdict(set)
    all_articles: List[Dict[str, Any]] = []
    article_law_pairs: Set[Tuple[str, str]] = set()

    try:
        case_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
        query = {
            "$or": [
                {"case_id": case_id},
                {"case_id": case_oid},
                {"case_id": str(case_oid)},
            ],
            "status": {"$ne": "DELETED"},
        }

        cursor = db.documents.find(
            query,
            {"_id": 1, "file_name": 1, "content": 1, "extracted_text": 1, "text": 1},
        )

        for doc in cursor:
            text = (
                doc.get("content")
                or doc.get("extracted_text")
                or doc.get("text")
                or ""
            )
            if not text:
                continue

            doc_id = str(doc["_id"])
            doc_name = doc.get("file_name", "")

            for match in LAW_NUMBER_PATTERN.finditer(text):
                law_num = match.group(1).replace(" ", "")
                laws.add(law_num)
                document_laws[doc_id].add(law_num)

            for match in LAW_ABBREVIATION_PATTERN.finditer(text):
                abbr = match.group(1)
                if abbr.lower() == "kushtetuta":
                    laws.add("Kushtetuta")
                    document_laws[doc_id].add("Kushtetuta")
                else:
                    abbr_up = abbr.upper()
                    laws.add(abbr_up)
                    document_laws[doc_id].add(abbr_up)

            for match in VERIFIED_ARTICLE_PATTERN.finditer(text):
                article_num = match.group(1)
                paragraph = match.group(2)
                all_articles.append({
                    "number": article_num,
                    "paragraph": paragraph,
                    "doc_id": doc_id,
                    "doc_name": doc_name,
                })
                articles_by_doc[doc_id].append(article_num)

            for match in CITATION_WITH_LAW_PATTERN.finditer(text):
                article_num = match.group(1)
                law = match.group(3).upper()
                article_law_pairs.add((article_num, law))

    except Exception as e:
        logger.warning(f"⚠️ [GUARDRAIL #2] extraction failed: {e}")

    # Dedupe nenet
    seen: Set[Tuple[str, Optional[str]]] = set()
    unique_articles: List[Dict[str, Any]] = []
    for art in all_articles:
        key = (art["number"], art["paragraph"])
        if key in seen:
            continue
        seen.add(key)
        unique_articles.append(art)

    return {
        "laws": sorted(laws),
        "articles": unique_articles,
        "article_law_pairs": sorted(article_law_pairs),
        "by_document": dict(articles_by_doc),
        "document_laws": {k: sorted(v) for k, v in document_laws.items()},
        "total_laws": len(laws),
        "total_articles": len(unique_articles),
        "total_pairs": len(article_law_pairs),
    }


# ═══════════════════════════════════════════════════════════════════════════
# ARTICLES BY LAW
# ═══════════════════════════════════════════════════════════════════════════

def extract_articles_by_law(db, case_id: str) -> Dict[str, Dict[str, str]]:
    articles_by_law: Dict[str, Dict[str, str]] = defaultdict(dict)
    try:
        case_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
        query = {
            "$or": [
                {"case_id": case_id},
                {"case_id": case_oid},
                {"case_id": str(case_oid)},
            ],
            "status": {"$ne": "DELETED"},
        }

        cursor = db.documents.find(
            query,
            {"_id": 1, "content": 1, "extracted_text": 1, "text": 1},
        )

        for doc in cursor:
            text = (
                doc.get("content")
                or doc.get("extracted_text")
                or doc.get("text")
                or ""
            )
            if not text:
                continue
            _process_document_articles(text, articles_by_law)

        return dict(articles_by_law)
    except Exception as e:
        logger.warning(f"⚠️ [SYNTHESIS] Could not extract articles: {e}")
        return {}


def _normalize_law_name(raw: str) -> str:
    raw = raw.strip()
    raw = re.sub(r'\bKPPK\b', 'KPPRK', raw, flags=re.IGNORECASE)
    return raw


def _find_nearest_law(
    law_positions: List[Tuple[int, str]],
    article_pos: int,
) -> Optional[str]:
    if not law_positions:
        return None
    best_law = None
    best_distance = float("inf")
    for law_pos, law_name in law_positions:
        if law_pos < article_pos:
            distance = article_pos - law_pos
            if distance < best_distance and distance <= LAW_CONTEXT_WINDOW:
                best_distance = distance
                best_law = law_name
    return best_law


def _process_document_articles(
    text: str,
    articles_by_law: Dict[str, Dict[str, str]],
) -> None:
    law_positions = []
    for match in LAW_WITH_NUMBER_PATTERN.finditer(text):
        law_name = _normalize_law_name(match.group(1))
        law_positions.append((match.start(), law_name))

    all_articles = []

    for match in MULTI_ARTICLE_PATTERN.finditer(text):
        nums_group = (match.group(1) or "") + (match.group(2) or "") + (match.group(3) or "")
        numbers = re.findall(r'\d+(?:[\.\/]\d+)*', nums_group)

        description = match.group(4)
        if description:
            description = re.sub(r'\s+', ' ', description).strip(" .,;:")
            if len(description) > 200:
                description = description[:200].rstrip() + "..."
        else:
            description = None

        for num in numbers:
            all_articles.append((match.start(), f"Neni {num}", description))

    for match in SINGLE_ARTICLE_PATTERN.finditer(text):
        article_num = match.group(1).strip()
        law_hint = (match.group(3) or "").strip()
        if law_hint:
            law_hint = re.sub(
                r'^\s*(?:i|të|te|e|së)\s+',
                '',
                law_hint,
                flags=re.IGNORECASE,
            ).strip()

        description = match.group(4)
        if description:
            description = re.sub(r'\s+', ' ', description).strip(" .,;:")
            if len(description) > 200:
                description = description[:200].rstrip() + "..."
        else:
            description = None

        all_articles.append((match.start(), f"Neni {article_num}", description))

    for article_pos, article_key, description in all_articles:
        attributed_law = _find_nearest_law(law_positions, article_pos)
        if not attributed_law:
            attributed_law = "Ligji i Paidentifikuar"

        if article_key not in articles_by_law[attributed_law]:
            articles_by_law[attributed_law][article_key] = description or ""

        if sum(len(v) for v in articles_by_law.values()) >= MAX_ARTICLE_DESCRIPTIONS:
            return