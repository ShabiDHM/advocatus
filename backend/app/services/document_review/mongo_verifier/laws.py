# FILE: backend/app/services/document_review/mongo_verifier/laws.py
# PHOENIX PROTOCOL - MONGO VERIFIER / LAWS V1.1
# V1.1: DYNAMIC ALLOWED LAWS — Shtuar get_all_law_numbers_from_db().
#       Lexon të gjitha numrat e ligjeve nga legal_knowledge_base, nxjerr
#       numrin nga law_title. Zero hardcoding në hallucination_checker.
# V1.0: Ekstraktuar nga mongo_verifier.py V2.11 (pa ndryshim logjike).

import logging
import re
from typing import Any, Dict, List, Set

from .config import LEGAL_KB_COLLECTION
from .successor_laws import _get_successor_law
from .text_utils import _extract_law_number_from_text

logger = logging.getLogger(__name__)


def verify_law_numbers(db, laws_by_number: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not laws_by_number:
        return []
    if db is None:
        return [
            {**law, "exists": False, "matched_doc": None, "match_reason": "no_db"}
            for law in laws_by_number
        ]

    results = []
    collection = db[LEGAL_KB_COLLECTION]

    for law in laws_by_number:
        law_number = law["number"]
        result = {
            "number": law_number,
            "name": law.get("name", ""),
            "exists": False,
            "matched_doc": None,
            "match_reason": "",
        }

        try:
            m = re.match(r'(\d{2})/L-(\d+)', law_number)
            if not m:
                m2 = re.match(r'(\d{4})/(\d+)', law_number)
                if m2:
                    part1, part2 = m2.group(1), m2.group(2)
                    title_patterns = [rf"\b{part1}\s*[\/\-_\s]?\s*{part2}\b"]
                else:
                    result["match_reason"] = "invalid_number_format"
                    results.append(result)
                    continue
            else:
                part1, part2 = m.group(1), m.group(2)
                title_patterns = [
                    rf"\b{part1}\s*[\/\-_\s]?\s*L\s*[\/\-_\s]?\s*{part2}\b",
                    rf"\b{part1}\s+L\s+{part2}\b",
                ]

            for pattern in title_patterns:
                doc = collection.find_one(
                    {"law_title": {"$regex": pattern, "$options": "i"}},
                    {"law_title": 1, "source": 1, "text": 1},
                )
                if doc:
                    result["exists"] = True
                    result["matched_doc"] = {
                        "law_title": doc.get("law_title", ""),
                        "source": doc.get("source", ""),
                    }
                    result["match_reason"] = "number_in_title"
                    break

            if not result["exists"]:
                successor_info = _get_successor_law(law_number)
                if successor_info and successor_info.get("successor") != law_number:
                    result["match_reason"] = f"law_replaced_by:{successor_info['successor']}"
                    result["suggested_replacement"] = {
                        "old_law": law_number,
                        "new_law": successor_info["successor"],
                        "new_law_name": successor_info.get("name", ""),
                        "note": successor_info.get("note", ""),
                    }
                else:
                    result["match_reason"] = "law_not_in_db"

        except Exception as e:
            logger.warning(f"⚠️ [verify_law_numbers] Error for {law_number}: {e}")
            result["match_reason"] = f"error:{type(e).__name__}"

        results.append(result)

    verified = sum(1 for r in results if r["exists"])
    replaced = sum(
        1 for r in results
        if r.get("match_reason", "").startswith("law_replaced_by")
    )

    logger.info(
        f"📚 [MONGO_VERIFIER V2.12] Laws by number: {len(results)} total, "
        f"{verified} verified, {replaced} replaced"
    )
    return results


# ═══════════════════════════════════════════════════════════════════════════
# V1.1: DYNAMIC ALLOWED LAWS
# ═══════════════════════════════════════════════════════════════════════════

def get_all_law_numbers_from_db(db) -> Set[str]:
    """
    V1.1: Lexon TË GJITHA numrat e ligjeve nga legal_knowledge_base.

    Nxjerr numrin nga law_title (p.sh. "Ligji Nr. 06/L-074 Kodi Penal"
    → "06/L-074"). Kthen set të normalizuar.

    Përdoret nga service.py dhe verifier.py për të kaluar si
    extra_allowed_laws tek hallucination_checker — zero hardcoding.

    Kthen set bosh nëse DB është e padisponueshme ose bosh.
    """
    if db is None:
        return set()

    try:
        collection = db[LEGAL_KB_COLLECTION]
        cursor = collection.find({}, {"law_title": 1, "_id": 0})

        laws: Set[str] = set()
        for doc in cursor:
            title = (doc.get("law_title") or "").strip()
            if not title:
                continue
            num = _extract_law_number_from_text(title)
            if num:
                normalized = _normalize_law_number(num)
                if normalized:
                    laws.add(normalized)

        logger.info(
            f"📚 [LAWS V1.1] U lexuan {len(laws)} numra ligjesh nga DB "
            f"(koleksioni: {LEGAL_KB_COLLECTION})"
        )
        return laws

    except Exception as e:
        logger.warning(f"⚠️ [LAWS V1.1] Leximi i ligjeve nga DB dështoi: {e}")
        return set()


def _normalize_law_number(num: str) -> str:
    """
    Normalizon numrin e ligjit: heq hapësira, normalizon `–`/`-`, upper.
    P.sh. "06 / L - 074" → "06/L-074"; "2004/32" → "2004/32".
    """
    if not num:
        return ""
    s = str(num).strip()
    s = re.sub(r'\s+', '', s)
    s = s.replace('–', '-').replace('—', '-')
    s = s.upper()
    return s