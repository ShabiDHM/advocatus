# FILE: backend/app/services/document_review/mongo_verifier/case_numbers.py
# PHOENIX PROTOCOL - MONGO VERIFIER / CASE NUMBERS V1.1
# V1.1: ROBUSTNESS + VERSION SYNC —
#       - `case["case_number"]` → `case.get("case_number", "")`; skip nëse bosh.
#       - Log message: "V2.12" → "V1.1" (ishte mbetje e versionit të vjetër).
# V1.0 (V2.12 modular): Ekstraktuar nga mongo_verifier.py V2.11.

import logging
import re
from typing import Any, Dict, List, Optional, Set

from .config import LEGAL_KB_COLLECTION, CASE_LAW_COLLECTION

logger = logging.getLogger(__name__)


CASE_NUMBER_SEP_REGEX = r'[\s\.\/\-_]*'


def _case_number_patterns(case_number: str) -> List[str]:
    r"""
    V2.9: Ndërton pattern-e regex fleksibël për numrin e lëndës.
    Pranon:
      - 'PML.Nr.185/2025'  (kanonik)
      - 'PML.185/2025'     (pa 'Nr')
      - 'PML Nr 185 2025'  (vetëm hapësira)
      - 'PML-185-2025'     (me dash)
      - 'PML185/2025'      (pa separator pas prefiksit)
      - 'PML.Nr.185.2025'  (pika)
    Dhe ekspandon vitin 2-shifror ↔ 4-shifror në të dy drejtimet.
    """
    if not case_number:
        return []

    clean = case_number.strip().upper()
    sep = CASE_NUMBER_SEP_REGEX

    m = re.match(
        rf'^([A-ZÇË]+){sep}(?:NR{sep})?(\d+){sep}(\d{{2,4}})\s*$',
        clean,
    )
    if not m:
        parts = re.split(r'[\.\/\-\s]+', clean)
        parts = [re.escape(p) for p in parts if p]
        if not parts:
            return []
        return [rf'\b{sep.join(parts)}\b']

    prefix, num, year = m.group(1), m.group(2), m.group(3)
    prefix_esc = re.escape(prefix)
    num_esc = re.escape(num)

    patterns: List[str] = []

    patterns.append(
        rf'\b{prefix_esc}{sep}(?:NR{sep})?{num_esc}{sep}{re.escape(year)}\b'
    )

    if len(year) == 4 and year.startswith("20"):
        short_year = year[2:]
        patterns.append(
            rf'\b{prefix_esc}{sep}(?:NR{sep})?{num_esc}{sep}{re.escape(short_year)}\b'
        )
    elif len(year) == 2:
        patterns.append(
            rf'\b{prefix_esc}{sep}(?:NR{sep})?{num_esc}{sep}20{re.escape(year)}\b'
        )

    return patterns


def _find_case_number_doc(
    collection,
    case_number: str,
) -> Optional[Dict[str, Any]]:
    patterns = _case_number_patterns(case_number)
    if not patterns:
        return None

    projection = {
        "case_number": 1, "text": 1, "source": 1,
        "page": 1, "actual_page": 1, "chunk_id": 1,
        "law_title": 1, "title": 1,
    }

    for pattern in patterns:
        try:
            doc = collection.find_one(
                {"case_number": {"$regex": pattern, "$options": "i"}},
                projection,
            )
            if doc:
                return doc
        except Exception as e:
            logger.warning(
                f"⚠️ [_find_case_number_doc] Regex failed for '{pattern}': {e}"
            )
            continue

    return None


def verify_case_numbers(db, case_numbers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    V2.9: Verifikon numrat e lëndëve të cituara.

    Rrjedha:
      1. Nëse 'is_likely_own' → skip.
      2. Kontrollo availability të CASE_LAW_COLLECTION + LEGAL_KB_COLLECTION.
      3. Për çdo numër, provo koleksionet sipas radhës.
      4. Match_reason përfshin emrin e koleksionit ku u gjet.
    """
    if not case_numbers:
        return []

    results: List[Dict[str, Any]] = []

    available_collections: Set[str] = set()
    if db is not None:
        try:
            available_collections = set(db.list_collection_names())
        except Exception as e:
            logger.warning(
                f"⚠️ [verify_case_numbers] list_collection_names failed: {e}"
            )

    search_collections: List[str] = []
    if CASE_LAW_COLLECTION in available_collections:
        search_collections.append(CASE_LAW_COLLECTION)
    if LEGAL_KB_COLLECTION in available_collections:
        search_collections.append(LEGAL_KB_COLLECTION)

    for case in case_numbers:
        # V1.1: .get() — skip nëse mungon numri
        case_number = (case.get("case_number") or "").strip()
        if not case_number:
            logger.warning("⚠️ [verify_case_numbers] Entry pa 'case_number' — skip")
            continue

        result = {
            "case_number": case_number,
            "prefix": case.get("prefix", ""),
            "is_likely_own": case.get("is_likely_own", False),
            "context": case.get("context", ""),
            "is_precedent": False,
            "matched_doc": None,
            "match_reason": "",
        }

        if case.get("is_likely_own"):
            result["match_reason"] = "own_case_number"
            results.append(result)
            continue

        if db is None:
            result["match_reason"] = "no_db"
            results.append(result)
            continue

        if not search_collections:
            result["match_reason"] = "no_case_law_collection_available"
            results.append(result)
            continue

        found = False
        for collection_name in search_collections:
            try:
                collection = db[collection_name]
                doc = _find_case_number_doc(collection, case_number)
                if doc:
                    result["is_precedent"] = True
                    result["matched_doc"] = {
                        "case_number": doc.get("case_number", ""),
                        "source": doc.get("source", ""),
                    }
                    result["match_reason"] = f"found_in_{collection_name}"
                    found = True
                    break
            except Exception as e:
                logger.warning(
                    f"⚠️ [verify_case_numbers] Error searching "
                    f"{collection_name} for {case_number}: {e}"
                )

        if not found:
            result["match_reason"] = "not_found_in_any_collection"

        results.append(result)

    precedents = sum(1 for r in results if r.get("is_precedent"))
    cited = sum(1 for r in results if not r.get("is_likely_own"))

    logger.info(
        f"📚 [MONGO_VERIFIER V1.1] Case numbers: {len(results)} total, "
        f"{cited} cited, {precedents} real precedents "
        f"(searched: {search_collections})"
    )
    return results