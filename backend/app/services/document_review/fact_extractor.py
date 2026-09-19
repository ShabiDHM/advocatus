# FILE: backend/app/services/document_review/fact_extractor.py
# PHOENIX PROTOCOL - FACT EXTRACTOR V1.1
# V1.1: FIX — datat ruhen të dyja (numeric + albanian) edhe nëse ISO është i njëjtë.
#       Çelësi unik tani është (iso, source).
# V1.0: Ekstraktim deterministik.

import re
import logging
from typing import Dict, Any, List, Set, Tuple, Optional

from .constants import MAX_DATES, MAX_CONTEXT_CHARS
from .patterns import (
    DATE_PATTERN,
    DATE_ALBANIAN_PATTERN,
    DEADLINE_PATTERN,
    DEADLINE_CONTEXT_KEYWORDS,
    PARTY_LABEL_PATTERN,
)
from .helpers import (
    parse_date,
    month_name_to_number,
    extract_context,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# EXTRACT DATES — V1.1 FIX
# ═══════════════════════════════════════════════════════════════════════════

def extract_dates(text: str) -> List[Dict[str, Any]]:
    """
    Nxjerr të gjitha datat.
    V1.1: Ruaj të dyja formatet (numeric + albanian) me çelës (iso, source).
    """
    if not text:
        return []

    results: List[Dict[str, Any]] = []
    seen: Set[Tuple[str, str]] = set()  # (iso, source)

    # 1. Datat numerike
    for match in DATE_PATTERN.finditer(text):
        day, month, year = match.group(1), match.group(2), match.group(3)
        dt = parse_date(day, month, year)
        if not dt:
            continue

        iso = dt.isoformat()[:10]
        key = (iso, "numeric")
        if key in seen:
            continue
        seen.add(key)

        results.append({
            "iso": iso,
            "display": dt.strftime("%d.%m.%Y"),
            "day": dt.day,
            "month": dt.month,
            "year": dt.year,
            "position": match.start(),
            "context": extract_context(text, match.start(), window=80),
            "source": "numeric",
        })

        if len(results) >= MAX_DATES:
            break

    # 2. Datat shqip
    for match in DATE_ALBANIAN_PATTERN.finditer(text):
        day = match.group(1)
        month_name = match.group(2)
        year = match.group(3)
        month_num = month_name_to_number(month_name)
        if not month_num:
            continue

        dt = parse_date(day, str(month_num), year)
        if not dt:
            continue

        iso = dt.isoformat()[:10]
        key = (iso, "albanian")
        if key in seen:
            continue
        seen.add(key)

        results.append({
            "iso": iso,
            "display": dt.strftime("%d.%m.%Y"),
            "day": dt.day,
            "month": dt.month,
            "year": dt.year,
            "position": match.start(),
            "context": extract_context(text, match.start(), window=80),
            "source": "albanian",
        })

        if len(results) >= MAX_DATES:
            break

    results.sort(key=lambda x: x["position"])
    return results


# ═══════════════════════════════════════════════════════════════════════════
# EXTRACT DEADLINES
# ═══════════════════════════════════════════════════════════════════════════

def extract_deadlines(text: str) -> List[Dict[str, Any]]:
    """Nxjerr afatet procedurale me kontekst."""
    if not text:
        return []

    results: List[Dict[str, Any]] = []

    for match in DEADLINE_PATTERN.finditer(text):
        num = int(match.group(1))
        unit = match.group(2).lower().strip("ëe")

        if unit.startswith("dit"):
            unit_norm = "ditë"
        elif unit.startswith("muaj"):
            unit_norm = "muaj"
        elif unit.startswith("jav"):
            unit_norm = "javë"
        elif unit.startswith("vjet") or unit.startswith("vit"):
            unit_norm = "vjet"
        else:
            unit_norm = unit

        context = extract_context(text, match.start(), window=120)
        context_lower = context.lower()

        has_legal_context = any(
            kw in context_lower for kw in DEADLINE_CONTEXT_KEYWORDS
        )

        results.append({
            "num": num,
            "unit": unit_norm,
            "display": f"{num} {unit_norm}",
            "position": match.start(),
            "context": context[:MAX_CONTEXT_CHARS],
            "has_legal_context": has_legal_context,
        })

    return results


# ═══════════════════════════════════════════════════════════════════════════
# EXTRACT PARTIES
# ═══════════════════════════════════════════════════════════════════════════

def extract_parties(text: str) -> List[Dict[str, Any]]:
    """Nxjerr palët me role."""
    if not text:
        return []

    results: List[Dict[str, Any]] = []
    seen: Set[Tuple[str, str]] = set()

    for match in PARTY_LABEL_PATTERN.finditer(text):
        role = match.group(0).split(':')[0].split('-')[0].strip()
        name = match.group(1).strip()

        if len(name) < 3:
            continue

        name = re.sub(r'[,.;:]+$', '', name).strip()

        key = (role.lower(), name.lower())
        if key in seen:
            continue
        seen.add(key)

        results.append({
            "role": role,
            "name": name,
            "context": extract_context(text, match.start(), window=80),
        })

    return results


# ═══════════════════════════════════════════════════════════════════════════
# DETECT CONTRADICTIONS
# ═══════════════════════════════════════════════════════════════════════════

def detect_contradictions(
    dates: List[Dict[str, Any]],
    deadlines: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Detekton kontradikta të mundshme."""
    contradictions: List[Dict[str, Any]] = []

    deadlines_by_unit: Dict[str, List[Dict[str, Any]]] = {}
    for d in deadlines:
        if not d.get("has_legal_context"):
            continue
        deadlines_by_unit.setdefault(d["unit"], []).append(d)

    for unit, items in deadlines_by_unit.items():
        if len(items) < 2:
            continue
        unique_nums = set(item["num"] for item in items)
        if len(unique_nums) > 1:
            contradictions.append({
                "type": "deadline_inconsistency",
                "unit": unit,
                "values": sorted(unique_nums),
                "count": len(items),
                "examples": [item["context"][:150] for item in items[:3]],
            })

    return contradictions


# ═══════════════════════════════════════════════════════════════════════════
# BUILD FACT PROFILE
# ═══════════════════════════════════════════════════════════════════════════

def build_fact_profile(text: str) -> Dict[str, Any]:
    """Ndërton profilin e plotë të fakteve."""
    if not text:
        return {
            "dates": [],
            "deadlines": [],
            "legal_deadlines": [],
            "parties": [],
            "contradictions": [],
            "stats": {},
        }

    dates = extract_dates(text)
    deadlines = extract_deadlines(text)
    parties = extract_parties(text)
    contradictions = detect_contradictions(dates, deadlines)

    legal_deadlines = [d for d in deadlines if d.get("has_legal_context")]

    stats = {
        "total_dates": len(dates),
        "total_deadlines": len(deadlines),
        "legal_deadlines": len(legal_deadlines),
        "total_parties": len(parties),
        "total_contradictions": len(contradictions),
    }

    logger.info(
        f"🔬 [FACT_EXTRACTOR] dates={stats['total_dates']}, "
        f"deadlines={stats['total_deadlines']} "
        f"(legal={stats['legal_deadlines']}), "
        f"parties={stats['total_parties']}"
    )

    return {
        "dates": dates,
        "deadlines": deadlines,
        "legal_deadlines": legal_deadlines,
        "parties": parties,
        "contradictions": contradictions,
        "stats": stats,
    }