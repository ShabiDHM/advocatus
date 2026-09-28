# FILE: backend/app/services/document_review/verify/scoring.py
# PHOENIX PROTOCOL - VERIFY SCORING V1.0
# Ekstraktuar nga draft_verifier.py V1.17 (pa ndryshim logjike).

import re
from typing import Any, Dict, Tuple

from .config import READINESS_SCORES


def extract_formal_pct(sections: Dict[str, Dict[str, Any]]) -> float:
    sec = sections.get("formal_completeness")
    if not sec:
        return 0.0

    content = sec.get("content") or ""

    m = re.search(
        r'(\d+)\s*/\s*(\d+)\s*pjes[ëe]?\s*(?:t[ëe]\s*)?pranishme\s*\(\s*(\d+(?:[.,]\d+)?)\s*%\s*\)',
        content,
        re.IGNORECASE,
    )
    if m:
        try:
            return float(m.group(3).replace(",", "."))
        except ValueError:
            pass

    m2 = re.search(r'\(\s*(\d+(?:[.,]\d+)?)\s*%\s*\)', content)
    if m2:
        try:
            return float(m2.group(1).replace(",", "."))
        except ValueError:
            pass

    return 0.0


def calculate_score(
    sections: Dict[str, Dict[str, Any]],
    verification_report: Dict[str, Any],
    readiness: str,
) -> Tuple[int, Dict[str, float]]:
    formal_pct = extract_formal_pct(sections)

    stats = verification_report.get("stats", {}) or {}
    articles_total = int(stats.get("articles_total", 0) or 0)
    articles_verified = int(stats.get("articles_verified", 0) or 0)

    if articles_total > 0:
        legal_pct = (articles_verified / articles_total) * 100.0
    else:
        legal_pct = 70.0

    readiness_pct = float(READINESS_SCORES.get(readiness, 0))

    score = formal_pct * 0.35 + legal_pct * 0.35 + readiness_pct * 0.30
    score_int = int(round(min(100.0, max(0.0, score))))

    breakdown = {
        "formal": round(formal_pct, 1),
        "legal": round(legal_pct, 1),
        "readiness": readiness_pct,
    }

    return score_int, breakdown