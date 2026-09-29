# FILE: backend/app/api/endpoints/laws_pkg/laws_search_service.py
# PHOENIX PROTOCOL - GROUND-TRUTH LAWS SERVICE V23.1
#
# V23.1: FIX pymongo bool bug.
#   - `if not db` → `if db is None` (pymongo Database nuk implementon __bool__)
#   - Kjo bllokonte /by-title me 500 në V23.0
#
# V23.0: FIX P1-P25 (auditim sesioni i Bibliotekës Ligjore).

import re
import os
import time
import logging
from typing import List, Optional, Tuple, Dict, Any

from app.api.endpoints.laws_pkg.laws_dictionary import (
    _is_case_law,
    _normalize_hallucinated_title,
    _strip_alpha,
    _normalize_diacritics,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# KONSTANTE
# ═══════════════════════════════════════════════════════════════════════════

MAX_STATUTE_ARTICLES = 200
MAX_CANDIDATE_DOCS = 50
MAX_PDF_CANDIDATES = 100
MAX_PDF_INDEX_SIZE = 5000

STOP_WORDS = frozenset({
    "ligji", "ligjin", "ligjit", "kodi", "kodin", "kodit",
    "per", "për", "dhe", "ose", "nga", "me", "ne", "në",
    "te", "të", "se", "së", "nr",
    "republika", "republikës", "republikes",
    "kosove", "kosovës", "kosoves",
    "web", "pdf", "i", "e",
})

_NON_STATUTE_PATTERN = r'\b(?:Case_Law|PRAKTIK|AKTGJYKMET|VENDIM(?:ET)?)\b'
_CASE_LAW_FALLBACK_PATTERN = r'\b(?:Case_Law|PRAKTIK|Gjykata\s+Supreme)\b'


# ═══════════════════════════════════════════════════════════════════════════
# PDF INDEX
# ═══════════════════════════════════════════════════════════════════════════

_PDF_INDEX: Dict[str, str] = {}
_PDF_INDEX_BUILT = False


def _get_search_dirs() -> List[str]:
    current_file = os.path.abspath(__file__)
    endpoints_dir = os.path.dirname(current_file)
    laws_pkg_dir = os.path.dirname(endpoints_dir)
    api_dir = os.path.dirname(laws_pkg_dir)
    app_dir = os.path.dirname(api_dir)
    backend_dir = os.path.dirname(app_dir)
    project_root = os.path.dirname(backend_dir)

    return [
        os.path.join(project_root, "data", "laws", "ks"),
        os.path.join(backend_dir, "data", "laws", "ks"),
        os.path.join(project_root, "data", "laws"),
        os.path.join(backend_dir, "data", "laws"),
        "data/laws/ks",
        "data/laws",
    ]


def _build_pdf_index() -> None:
    global _PDF_INDEX_BUILT
    if _PDF_INDEX_BUILT:
        return

    t0 = time.time()
    for search_dir in _get_search_dirs():
        if not os.path.exists(search_dir):
            continue
        for root, _, files in os.walk(search_dir):
            for f in files:
                if not f.lower().endswith('.pdf'):
                    continue
                key = _strip_alpha(f)
                if not key:
                    continue
                if key not in _PDF_INDEX:
                    _PDF_INDEX[key] = os.path.join(root, f)
                if len(_PDF_INDEX) >= MAX_PDF_INDEX_SIZE:
                    break

    _PDF_INDEX_BUILT = True
    logger.info(
        f"[PDF_INDEX] Built: {len(_PDF_INDEX)} PDFs in "
        f"{int((time.time() - t0) * 1000)}ms"
    )


def clear_pdf_index() -> None:
    global _PDF_INDEX_BUILT
    _PDF_INDEX.clear()
    _PDF_INDEX_BUILT = False


def find_pdf_by_number_pair(requested_name: str) -> Optional[str]:
    if not requested_name:
        return None

    _build_pdf_index()
    target_clean = _strip_alpha(requested_name)
    if not target_clean:
        return None

    result = _PDF_INDEX.get(target_clean)
    if result:
        logger.debug(f"[PDF_LOOKUP] Hit: '{requested_name}' → {result}")
    else:
        logger.debug(f"[PDF_LOOKUP] Miss: '{requested_name}' ({target_clean})")
    return result


# ═══════════════════════════════════════════════════════════════════════════
# TITLE TOKENIZATION + SCORING
# ═══════════════════════════════════════════════════════════════════════════

def _tokenize_title(title: str) -> Tuple[List[str], List[str]]:
    if not title:
        return [], []

    raw_words = re.findall(r'\w+', title)
    escaped_words = [
        re.escape(w) for w in raw_words
        if len(w) >= 3 and _normalize_diacritics(w.lower()) not in STOP_WORDS
    ]

    raw_digits = re.findall(r'\b\d+\b', title)
    digits = [d for d in raw_digits if len(d) >= 2]

    return escaped_words, digits


def _score_candidate(requested_title: str, doc_law_title: str) -> int:
    if not doc_law_title:
        return 0

    t = _normalize_diacritics(requested_title.lower().strip())
    d = _normalize_diacritics(doc_law_title.lower().strip())

    if not t or not d:
        return 0

    if t == d:
        return 10000

    score = 0

    if t in d:
        score += 5000
    elif d in t:
        score += 3000

    t_words = {w for w in re.findall(r'\w+', t) if w not in STOP_WORDS and len(w) >= 3}
    d_words = {w for w in re.findall(r'\w+', d) if w not in STOP_WORDS and len(w) >= 3}
    common = t_words & d_words
    score += len(common) * 100

    t_codes = set(re.findall(r'\d{2,4}[/\-]\w+\d{1,4}|\d{4}/\d{1,4}', t))
    d_codes = set(re.findall(r'\d{2,4}[/\-]\w+\d{1,4}|\d{4}/\d{1,4}', d))
    if t_codes & d_codes:
        score += 2000

    return score


# ═══════════════════════════════════════════════════════════════════════════
# FIND DOCUMENTS BY TITLE  ← V23.1 FIX pymongo bool
# ═══════════════════════════════════════════════════════════════════════════

def find_documents_by_title(
    db,
    raw_title: str,
    fields: Optional[dict] = None,
) -> List[dict]:
    """
    V23.1: FIX `if not db` → `if db is None`.
    pymongo Database nuk implementon __bool__.
    """
    # ═══ FIX: pymongo bool bug ═══
    if db is None or not raw_title or not raw_title.strip():
        return []

    title = raw_title.strip()
    t0 = time.time()

    projection = fields if fields is not None else {
        "law_title": 1, "source": 1, "article_number": 1,
        "page": 1, "page_number": 1, "actual_page": 1,
        "chunk_index": 1, "is_article": 1,
    }

    words, digits = _tokenize_title(title)
    is_case = _is_case_law(title)

    collection = db.legal_knowledge_base
    docs: List[dict] = []

    try:
        if is_case:
            docs = _search_case_law(collection, words, projection)
        else:
            docs = _search_statute(collection, words, digits, title, projection)
    except Exception as e:
        logger.error(f"[SEARCH] DB error for '{title}': {e}")
        return []

    if docs:
        docs.sort(
            key=lambda d: _score_candidate(title, d.get("law_title", "")),
            reverse=True,
        )

    elapsed_ms = int((time.time() - t0) * 1000)
    logger.info(
        f"[SEARCH] '{title}' (case_law={is_case}) → "
        f"{len(docs)} docs in {elapsed_ms}ms"
    )
    return docs


def _search_case_law(collection, words: List[str], projection: dict) -> List[dict]:
    or_branches: List[Dict[str, Any]] = []

    if words:
        and_conditions = []
        for w in words:
            and_conditions.append({
                "$or": [
                    {"law_title": {"$regex": w, "$options": "i"}},
                    {"source": {"$regex": w, "$options": "i"}},
                ]
            })
        or_branches.append({"$and": and_conditions})

    or_branches.append({
        "source": {"$regex": _CASE_LAW_FALLBACK_PATTERN, "$options": "i"},
    })
    or_branches.append({
        "law_title": {"$regex": _CASE_LAW_FALLBACK_PATTERN, "$options": "i"},
    })

    return list(
        collection.find({"$or": or_branches}, projection)
        .limit(MAX_CANDIDATE_DOCS)
    )


def _search_statute(
    collection,
    words: List[str],
    digits: List[str],
    title: str,
    projection: dict,
) -> List[dict]:
    if words:
        conditions: List[Dict[str, Any]] = []
        for w in words:
            conditions.append({
                "$or": [
                    {"law_title": {"$regex": w, "$options": "i"}},
                    {"source": {"$regex": w, "$options": "i"}},
                ]
            })

        conditions.append({
            "source": {"$not": {"$regex": _NON_STATUTE_PATTERN, "$options": "i"}},
        })
        conditions.append({
            "law_title": {"$not": {"$regex": _NON_STATUTE_PATTERN, "$options": "i"}},
        })

        for d in digits:
            clean_d = str(int(d)) if d.isdigit() else d
            d_regex = rf"\b0*{re.escape(clean_d)}\b"
            conditions.append({
                "$or": [
                    {"law_title": {"$regex": d_regex, "$options": "i"}},
                    {"source": {"$regex": d_regex, "$options": "i"}},
                ]
            })

        docs = list(
            collection.find({"$and": conditions}, projection)
            .limit(MAX_CANDIDATE_DOCS)
        )
        if docs:
            return docs

    escaped_title = re.escape(title)
    docs = list(
        collection.find({
            "$and": [
                {"$or": [
                    {"law_title": {"$regex": escaped_title, "$options": "i"}},
                    {"source": {"$regex": escaped_title, "$options": "i"}},
                ]},
                {"source": {"$not": {"$regex": _NON_STATUTE_PATTERN, "$options": "i"}}},
            ]
        }, projection).limit(MAX_CANDIDATE_DOCS)
    )
    if docs:
        return docs

    if words:
        docs = list(
            collection.find({
                "$or": [
                    {"law_title": {"$regex": w, "$options": "i"}}
                    for w in words[:3]
                ]
            }, projection).limit(MAX_CANDIDATE_DOCS)
        )
        if docs:
            return docs

    return []


# ═══════════════════════════════════════════════════════════════════════════
# CONFIDENCE
# ═══════════════════════════════════════════════════════════════════════════

def _compute_confidence(
    doc: dict,
    metadata: dict,
    page_available: bool,
) -> Tuple[str, float, str]:
    if not doc or not doc.get("law_title"):
        return (
            "NONE", 0.0,
            "⚠️ Nuk u gjet asnjë dokument përputhës në bazën ligjore."
        )

    match_type = metadata.get("title_match_type", "unknown")
    article_matches = metadata.get("article_matches", 0)
    candidate_count = metadata.get("candidate_count", 0)

    base_score = {
        "exact": 0.95,
        "code": 0.85,
        "substring": 0.70,
        "word": 0.55,
        "unknown": 0.40,
    }.get(match_type, 0.30)

    if article_matches > 0:
        base_score += 0.05
    if candidate_count > 20:
        base_score -= 0.10
    if not page_available:
        base_score -= 0.05

    base_score = max(0.0, min(1.0, base_score))

    if base_score >= 0.85:
        level = "HIGH"
    elif base_score >= 0.55:
        level = "MEDIUM"
    elif base_score > 0.0:
        level = "LOW"
    else:
        level = "NONE"

    law_name = doc.get("law_title", "")
    source_file = doc.get("source", "")
    if page_available:
        page_num = doc.get("actual_page") or doc.get("page") or doc.get("page_number")
        page_text = f"Faqja {page_num}"
    else:
        page_text = "faqja e panjohur"

    description = (
        f"Përputhje {match_type} me '{law_name}' "
        f"({source_file or 'pa burim'}, {page_text}). "
        f"Score: {base_score:.2f}."
    )

    return level, round(base_score, 2), description


def _confidence_label(level: str) -> str:
    return {
        "HIGH": "Përputhje e saktë me tekstin zyrtar",
        "MEDIUM": "Përputhje e mirë, verifiko referencën",
        "LOW": "Përputhje e dobët, verifiko manualisht",
        "NONE": "Nuk u gjet",
    }.get(level, "I panjohur")


def _confidence_icon(level: str) -> str:
    return {"HIGH": "✅", "MEDIUM": "ℹ️", "LOW": "⚠️", "NONE": "❌"}.get(level, "❔")


def _confidence_color(level: str) -> str:
    return {
        "HIGH": "success", "MEDIUM": "info",
        "LOW": "warning", "NONE": "danger",
    }.get(level, "secondary")


# ═══════════════════════════════════════════════════════════════════════════
# SOURCE INFO
# ═══════════════════════════════════════════════════════════════════════════

def _generate_source_info(
    doc: dict,
    metadata: dict,
    original_law_title: str,
    original_article: str,
) -> dict:
    law_name = doc.get("law_title") or original_law_title
    source_file = doc.get("source") or ""

    raw_page = (
        doc.get("actual_page")
        or doc.get("page")
        or doc.get("page_number")
    )
    try:
        page_num = int(raw_page) if raw_page is not None else None
    except (ValueError, TypeError):
        page_num = None

    page_available = page_num is not None and page_num > 0

    level, score, description = _compute_confidence(doc, metadata, page_available)

    match_count = metadata.get("article_matches") or metadata.get("candidate_count") or (1 if doc else 0)

    is_official = bool(source_file) and bool(law_name)

    if level == "HIGH":
        hint = f"✅ Përputhje e saktë: {law_name}" + (f" (Faqja {page_num})" if page_available else "")
    elif level == "MEDIUM":
        hint = f"ℹ️ Përputhje e mirë: {law_name} — verifiko"
    elif level == "LOW":
        hint = f"⚠️ Përputhje e dobët: {law_name} — verifikim manual i nevojshëm"
    else:
        hint = "❌ Nuk u gjet në bazën ligjore"

    return {
        "confidence": {
            "level": level,
            "label": _confidence_label(level),
            "icon": _confidence_icon(level),
            "color": _confidence_color(level),
            "description": description,
            "score": score,
        },
        "matched_law": law_name,
        "matched_article": doc.get("article_number") or original_article,
        "source_file": source_file,
        "page": page_num,
        "page_available": page_available,
        "was_mapped": metadata.get("was_mapped", False),
        "is_official_statute": is_official,
        "verification_hint": hint,
        "match_count": match_count,
        "title_match_type": metadata.get("title_match_type", "unknown"),
    }


# ═══════════════════════════════════════════════════════════════════════════
# ART VARIANTS
# ═══════════════════════════════════════════════════════════════════════════

def _build_art_variants(raw_article: str) -> List[Any]:
    clean = (
        str(raw_article)
        .replace("Neni", "").replace("neni", "")
        .replace("NENI", "").replace("NENIT", "")
        .replace(".", "").strip()
    )
    if not clean:
        return []

    variants: List[Any] = [
        clean,
        f"{clean}.",
        f"Neni {clean}",
        f"Neni {clean}.",
        f"NENI {clean}",
        f"NENI {clean}.",
        f"neni {clean}",
        f"neni {clean}.",
        f" {clean}",
        f"{clean} ",
    ]

    if "/" in clean or "." in clean:
        base = re.split(r'[/.]', clean)[0]
        variants.extend([base, f"{base}.", f"Neni {base}", int(base) if base.isdigit() else base])

    if clean.isdigit():
        variants.append(int(clean))

    seen = set()
    unique: List[Any] = []
    for v in variants:
        key = (type(v).__name__, str(v))
        if key not in seen:
            seen.add(key)
            unique.append(v)
    return unique


# ═══════════════════════════════════════════════════════════════════════════
# FIND LAW DOCUMENTS  ← V23.1 FIX pymongo bool
# ═══════════════════════════════════════════════════════════════════════════

def find_law_documents(
    db,
    raw_law_title: str,
    raw_article_num: str,
) -> Tuple[List[dict], Optional[dict], Dict[str, Any]]:
    """
    V23.1: FIX `if not db` → `if db is None`.
    """
    t0 = time.time()

    mapped_title = _normalize_hallucinated_title(
        raw_law_title, str(raw_article_num), db=db
    )

    was_mapped = bool(mapped_title) and mapped_title.strip() != raw_law_title.strip()

    metadata: Dict[str, Any] = {
        "original_law_title": raw_law_title,
        "mapped_law_title": mapped_title,
        "article_number": raw_article_num,
        "title_match_type": "unknown",
        "article_matches": 0,
        "candidate_count": 0,
        "was_mapped": was_mapped,
    }

    # ═══ FIX: pymongo bool bug ═══
    if db is None or not mapped_title:
        return [], None, metadata

    try:
        candidate_docs = find_documents_by_title(db, mapped_title)
    except Exception as e:
        logger.error(f"[FIND_LAW] Title search failed for '{mapped_title}': {e}")
        return [], None, metadata

    metadata["candidate_count"] = len(candidate_docs)

    if not candidate_docs:
        return [], None, metadata

    best_doc = candidate_docs[0]
    matched_title = best_doc.get("law_title") or mapped_title

    if not matched_title:
        for d in candidate_docs:
            t = d.get("law_title")
            if t and t.strip():
                matched_title = t.strip()
                break

    norm_mapped = _normalize_diacritics(mapped_title.lower().strip())
    norm_matched = _normalize_diacritics(matched_title.lower().strip())
    if norm_mapped == norm_matched:
        metadata["title_match_type"] = "exact"
    elif norm_mapped in norm_matched or norm_matched in norm_mapped:
        metadata["title_match_type"] = "substring"
    elif re.search(r'\d{2,4}[/\-]\w+\d{1,4}', norm_mapped) and \
         re.search(r'\d{2,4}[/\-]\w+\d{1,4}', norm_matched):
        metadata["title_match_type"] = "code"
    else:
        metadata["title_match_type"] = "word"

    art_variants = _build_art_variants(raw_article_num)

    if art_variants:
        try:
            statute_docs = list(
                db.legal_knowledge_base.find({
                    "law_title": {
                        "$regex": f"^{re.escape(matched_title)}$",
                        "$options": "i",
                    },
                    "article_number": {"$in": art_variants},
                }).sort([("chunk_index", 1), ("_id", 1)])
                .limit(MAX_STATUTE_ARTICLES)
            )
            metadata["article_matches"] = len(statute_docs)

            if statute_docs:
                logger.info(
                    f"[FIND_LAW] '{matched_title}' Neni {raw_article_num}: "
                    f"{len(statute_docs)} chunks ({metadata['title_match_type']}) "
                    f"in {int((time.time() - t0) * 1000)}ms"
                )
                return statute_docs, None, metadata
        except Exception as e:
            logger.error(f"[FIND_LAW] Article query failed: {e}")

    logger.info(
        f"[FIND_LAW] No article match for '{matched_title}' "
        f"Neni {raw_article_num}, returning {min(3, len(candidate_docs))} candidates"
    )
    return candidate_docs[:3], None, metadata


# ═══════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════

__all__ = [
    "find_documents_by_title",
    "find_law_documents",
    "find_pdf_by_number_pair",
    "_generate_source_info",
    "clear_pdf_index",
    "MAX_STATUTE_ARTICLES",
]