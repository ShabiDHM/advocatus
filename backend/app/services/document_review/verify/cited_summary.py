# FILE: backend/app/services/document_review/verify/cited_summary.py
# PHOENIX PROTOCOL - VERIFY CITED SUMMARY V1.1
# V1.1: VERSION SYNC —
#       - Logger messages referonin "V1.17" (version i draft_verifier.py
#         para modularizimit) ndërsa file-i është V1.0. Tani "V1.1".
# V1.0: Ekstraktuar nga draft_verifier.py V1.17 (pa ndryshim logjike).

import logging
from typing import Any, Dict, List, Set

from ..hallucination_checker import _extract_articles, _extract_cases

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# EXTRACT FROM PRECEDENT EXCERPTS
# ═══════════════════════════════════════════════════════════════════════════

def extract_precedent_articles(
    precedents: List[Dict[str, Any]],
) -> Set[str]:
    found: Set[str] = set()
    if not precedents:
        return found

    for p in precedents:
        if not isinstance(p, dict):
            continue
        excerpt = (p.get("text_excerpt") or "").strip()
        if not excerpt:
            continue
        try:
            found.update(_extract_articles(excerpt))
        except Exception as e:
            logger.warning(
                f"⚠️ [VERIFY V1.1] Article extract failed for precedent "
                f"{p.get('case_number')}: {e}"
            )

    return found


def extract_precedent_cases(
    precedents: List[Dict[str, Any]],
) -> Set[str]:
    found: Set[str] = set()
    if not precedents:
        return found

    for p in precedents:
        if not isinstance(p, dict):
            continue
        excerpt = (p.get("text_excerpt") or "").strip()
        if not excerpt:
            continue
        try:
            found.update(_extract_cases(excerpt))
        except Exception as e:
            logger.warning(
                f"⚠️ [VERIFY V1.1] Case extract failed for precedent "
                f"{p.get('case_number')}: {e}"
            )

    return found


# ═══════════════════════════════════════════════════════════════════════════
# SUMMARY OF CITED PRECEDENTS
# ═══════════════════════════════════════════════════════════════════════════

def summarize_cited_precedents(
    verification_report: Dict[str, Any],
) -> Dict[str, Any]:
    cases = (verification_report or {}).get("case_numbers", []) or []

    cited: List[Dict[str, Any]] = []
    for c in cases:
        if not isinstance(c, dict):
            continue
        if c.get("is_likely_own"):
            continue
        cited.append(c)

    verified: List[str] = []
    unverified: List[str] = []

    for c in cited:
        cn = str(c.get("case_number", "")).strip()
        if not cn:
            continue
        if c.get("is_precedent"):
            verified.append(cn)
        else:
            unverified.append(cn)

    return {
        "total_cited": len(cited),
        "verified": verified,
        "unverified": unverified,
        "verified_count": len(verified),
        "unverified_count": len(unverified),
    }