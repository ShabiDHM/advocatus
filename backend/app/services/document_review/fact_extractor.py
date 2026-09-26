# FILE: backend/app/services/document_review/fact_extractor.py
# PHOENIX PROTOCOL - FACT EXTRACTOR V3.5
# V3.5: UNUSED IMPORT REMOVED — Hequr AMOUNT_PATTERN nga importet
#       (importohej por nuk përdorej askund). Zero ndryshim funksional.
# V3.4: MEDICAL_TESTS DEDUPE — refactor 2-fazë.
# V3.3: REPORTED CONTEXT UNIFIED — deadlines me flag `is_reported`.
# V3.2: FIX KONTRADIKTA EKSTERNE.
# V3.1: SOURCE DOCUMENT.
# V3.0: ZONES.
# V2.1: Normalize unit + medical_tests kontekst i gjere + dedupe.

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
    DISPOSITIVE_POINT_PATTERN,
    ICD_CODE_PATTERN,
    DIAGNOSIS_KEYWORDS,
    MEDICAL_TEST_KEYWORDS,
    NEGATIVE_RESULT_KEYWORDS,
    PRIOR_CONVICTION_PATTERN,
    CONVICTION_KEYWORDS,
    JUDGE_NAME_PATTERN,
    COURT_NAME_PATTERN,
    APPEAL_DEADLINE_PATTERN,
    PERIOD_PATTERN,
    DISTANCE_PATTERN,
)
from .helpers import (
    parse_date,
    month_name_to_number,
    extract_context,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# V3.0: ZONE CLASSIFICATION
# ═══════════════════════════════════════════════════════════════════════════

ZONE_ANCHORS: List[Tuple[str, str]] = [
    ("facts",      r'\b(?:FAKTET|Faktet|Rrethanat e rastit|Historiku|Ngjarja kritike|Gjendja faktike)\b'),
    ("reasoning",  r'\b(?:ARSYETIMI|Arsyetimi|Nga provat e administruara|Gjykata konstaton|Gjykata vërteton|PËR KËTO ARSYE|Për këto arsye)\b'),
    ("dispositive",r'\b(?:VENDOSI|AKTVENDOSI|VENDOS|AKTVENDOS)\b'),
    ("proposal",   r'\b(?:PROPOZON|PROPOZIMI|PROPOZIM|KËRKESA|Kërkesa|PADIA|Padia)\b'),
]

ZONE_UNKNOWN = "unknown"


# ═══════════════════════════════════════════════════════════════════════════
# V3.2: REPORTED CONTEXT DETECTION
# ═══════════════════════════════════════════════════════════════════════════

_REPORTING_REF_PATTERN = re.compile(
    r'(?:'
    r'në\s+Aktvendimin|në\s+Aktgjykimin|në\s+Vendimin|në\s+Aktin|'
    r'sipas\s+Aktvendimit|sipas\s+Aktgjykimit|sipas\s+Vendimit|sipas\s+Aktit|'
    r'referuar\s+në|referohet\s+në|bazuar\s+në|citim\s+i|'
    r'Aktvendimi\s+(?:Nr\.?|nr\.?)\s*\S+|'
    r'Aktgjykimi\s+(?:Nr\.?|nr\.?)\s*\S+|'
    r'Vendimi\s+(?:Nr\.?|nr\.?)\s*\S+|'
    r'Akti\s+(?:Nr\.?|nr\.?)\s*\S+|'
    r'C\.nr\.?\s*\d+|CA\.nr\.?\s*\d+|P\.nr\.?\s*\d+'
    r')',
    re.IGNORECASE | re.UNICODE,
)

_REPORTED_CONTEXT_WINDOW = 400


def _is_reported_context(text: str, position: int, window: int = _REPORTED_CONTEXT_WINDOW) -> bool:
    """V3.2: Kontrollon nëse pozicioni shfaqet brenda kontekstit të raportimit."""
    if not text:
        return False
    start = max(0, position - window)
    end = min(len(text), position + window)
    context = text[start:end]
    return bool(_REPORTING_REF_PATTERN.search(context))


def _classify_zone_anchors(text: str) -> List[Tuple[int, str]]:
    """V3.0: Gjen te gjithe anchorat e zonave ne tekst."""
    if not text:
        return []
    anchors: List[Tuple[int, str]] = []
    for zone_name, pattern in ZONE_ANCHORS:
        for m in re.finditer(pattern, text, re.IGNORECASE | re.UNICODE):
            anchors.append((m.start(), zone_name))
    anchors.sort(key=lambda x: x[0])
    return anchors


def _zone_at(anchors: List[Tuple[int, str]], position: int) -> str:
    """V3.0: Kthen zonen e fundit te hapur perpara pozicionit."""
    current = ZONE_UNKNOWN
    for pos, zone in anchors:
        if pos > position:
            break
        current = zone
    return current


def _zone_label(zone: str) -> str:
    """Etikete e lexueshme per zonen."""
    return {
        "facts": "Fakte",
        "reasoning": "Arsyetim",
        "dispositive": "Dispozitiv",
        "proposal": "Propozim/Kerkese",
        "reported": "Raportim (citim i dokumentit tjeter)",
        ZONE_UNKNOWN: "Pa zone (hyrie/header)",
    }.get(zone, zone)


# ═══════════════════════════════════════════════════════════════════════════
# V2.1: UNIT NORMALIZER
# ═══════════════════════════════════════════════════════════════════════════

def _normalize_unit(unit_raw: str) -> str:
    """V2.1: Normalizon shumesin shqip ne forme baze."""
    u = unit_raw.lower().strip()
    if u.startswith("dit"):
        return "ditë"
    if u.startswith("muaj"):
        return "muaj"
    if u.startswith("jav"):
        return "javë"
    if u.startswith("vjet") or u.startswith("vit"):
        return "vjet"
    return u


# ═══════════════════════════════════════════════════════════════════════════
# EXTRACT DATES
# ═══════════════════════════════════════════════════════════════════════════

def extract_dates(text: str) -> List[Dict[str, Any]]:
    """Nxjerr te gjitha datat (numerike + shqip)."""
    if not text:
        return []

    results: List[Dict[str, Any]] = []
    seen: Set[Tuple[str, str]] = set()

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
# EXTRACT DEADLINES — V3.3 me is_reported
# ═══════════════════════════════════════════════════════════════════════════

def extract_deadlines(
    text: str,
    source_document: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """V3.3: Nxjerr afatet procedurale + `source_document` + `is_reported`."""
    if not text:
        return []

    results: List[Dict[str, Any]] = []

    for match in DEADLINE_PATTERN.finditer(text):
        num = int(match.group(1))
        unit_norm = _normalize_unit(match.group(2))
        context = extract_context(text, match.start(), window=120)
        context_lower = context.lower()
        has_legal_context = any(
            kw in context_lower for kw in DEADLINE_CONTEXT_KEYWORDS
        )
        is_reported = _is_reported_context(text, match.start())
        results.append({
            "num": num,
            "unit": unit_norm,
            "display": f"{num} {unit_norm}",
            "position": match.start(),
            "context": context[:MAX_CONTEXT_CHARS],
            "has_legal_context": has_legal_context,
            "source_document": source_document or None,
            "is_reported": is_reported,
        })

    return results


# ═══════════════════════════════════════════════════════════════════════════
# EXTRACT PARTIES
# ═══════════════════════════════════════════════════════════════════════════

def extract_parties(text: str) -> List[Dict[str, Any]]:
    """Nxjerr palet me role."""
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
# EXTRACT DISPOSITIVE POINTS
# ═══════════════════════════════════════════════════════════════════════════

def extract_dispositive_points(text: str) -> List[Dict[str, Any]]:
    """Nxjerr pikat e dispozitivit (I, II, III, IV, V, VI, VII)."""
    if not text:
        return []

    results: List[Dict[str, Any]] = []

    for match in DISPOSITIVE_POINT_PATTERN.finditer(text):
        roman = match.group(1).strip()
        content = match.group(2).strip()
        if len(content) < 5:
            continue
        results.append({
            "roman": roman,
            "content": content[:MAX_CONTEXT_CHARS],
            "position": match.start(),
            "context": extract_context(text, match.start(), window=100),
        })

    return results


# ═══════════════════════════════════════════════════════════════════════════
# EXTRACT MEDICAL FINDINGS — V2.1
# ═══════════════════════════════════════════════════════════════════════════

def extract_medical_findings(text: str) -> List[Dict[str, Any]]:
    """V2.1: Nxjerr gjetjet mjekesore me dedupe."""
    if not text:
        return []

    results: List[Dict[str, Any]] = []
    seen: Set[Tuple[str, str]] = set()
    used_positions: List[int] = []
    DEDUPE_WINDOW = 150

    for match in ICD_CODE_PATTERN.finditer(text):
        code = match.group(1).strip()
        context = extract_context(text, match.start(), window=150)
        context_lower = context.lower()
        has_medical = any(kw in context_lower for kw in DIAGNOSIS_KEYWORDS)
        has_medical = has_medical or "kodohet" in context_lower or "kodi" in context_lower
        if not has_medical:
            continue
        key = ("icd", code)
        if key in seen:
            continue
        seen.add(key)
        used_positions.append(match.start())
        results.append({
            "type": "icd_code",
            "code": code,
            "position": match.start(),
            "context": context[:MAX_CONTEXT_CHARS],
            "context_full": context,
        })

    for kw in DIAGNOSIS_KEYWORDS:
        pattern = re.compile(re.escape(kw), re.IGNORECASE)
        for match in pattern.finditer(text):
            if any(abs(match.start() - p) < DEDUPE_WINDOW for p in used_positions):
                continue
            context = extract_context(text, match.start(), window=200)
            context_lower = context.lower()
            if "quhet" in context_lower or "diagnostikuar" in context_lower or "konstatuar" in context_lower:
                key = ("diag_ctx", context[:100].lower())
                if key in seen:
                    continue
                seen.add(key)
                used_positions.append(match.start())
                results.append({
                    "type": "diagnosis_context",
                    "keyword": kw,
                    "position": match.start(),
                    "context": context[:MAX_CONTEXT_CHARS],
                    "context_full": context,
                })

    return results


# ═══════════════════════════════════════════════════════════════════════════
# EXTRACT MEDICAL TESTS — V3.4
# ═══════════════════════════════════════════════════════════════════════════

def extract_medical_tests(text: str) -> List[Dict[str, Any]]:
    """
    V3.4: Nxjerr testet mjekesore + rezultatin.

    Dedup me 2 faza: (1) skano për mbivendosje, (2) apliko heqjet në fund.
    Nuk muton listën gjatë iterimit.
    """
    if not text:
        return []

    results: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    WIDE_WINDOW = 500
    DEDUPE_DISTANCE = 100

    for kw in MEDICAL_TEST_KEYWORDS:
        pattern = re.compile(re.escape(kw), re.IGNORECASE)
        for match in pattern.finditer(text):
            key = f"{kw.lower()}|{match.start()}"
            if key in seen:
                continue
            seen.add(key)
            context = extract_context(text, match.start(), window=WIDE_WINDOW)
            context_lower = context.lower()
            is_negative = any(nk in context_lower for nk in NEGATIVE_RESULT_KEYWORDS)
            is_positive = (
                ("pozitiv" in context_lower or "positive" in context_lower)
                and not is_negative
            )
            result_type = "unknown"
            if is_negative:
                result_type = "negative"
            elif is_positive:
                result_type = "positive"
            results.append({
                "test_type": kw,
                "result": result_type,
                "position": match.start(),
                "context": context[:MAX_CONTEXT_CHARS],
                "context_full": context,
            })

    # V3.4: Dedup me 2 faza (nuk muton gjatë iterimit)
    to_remove: Set[int] = set()
    for i, r in enumerate(results):
        if i in to_remove:
            continue
        for j in range(i + 1, len(results)):
            if j in to_remove:
                continue
            existing = results[j]
            if abs(r["position"] - existing["position"]) < DEDUPE_DISTANCE:
                if r["result"] != "unknown" and existing["result"] == "unknown":
                    to_remove.add(j)
                elif r["result"] == "unknown" and existing["result"] != "unknown":
                    to_remove.add(i)
                    break

    for idx in sorted(to_remove, reverse=True):
        results.pop(idx)

    return results


# ═══════════════════════════════════════════════════════════════════════════
# EXTRACT PRIOR CONVICTIONS
# ═══════════════════════════════════════════════════════════════════════════

def extract_prior_convictions(text: str) -> List[Dict[str, Any]]:
    """Nxjerr denimet e meparshme penale."""
    if not text:
        return []

    results: List[Dict[str, Any]] = []
    seen: Set[str] = set()

    for match in PRIOR_CONVICTION_PATTERN.finditer(text):
        prefix = match.group(1)
        num = match.group(2)
        case_number = f"{prefix}{num}".strip()
        if case_number in seen:
            continue
        context = extract_context(text, match.start(), window=200)
        context_lower = context.lower()
        has_conviction = any(kw in context_lower for kw in CONVICTION_KEYWORDS)
        is_penal = prefix.upper().startswith("P.")
        if not (has_conviction or is_penal):
            continue
        seen.add(case_number)
        results.append({
            "case_number": case_number,
            "is_penal": is_penal,
            "position": match.start(),
            "context": context[:MAX_CONTEXT_CHARS],
            "context_full": context,
        })

    return results


# ═══════════════════════════════════════════════════════════════════════════
# EXTRACT JUDGE / COURT / APPEAL DEADLINE
# ═══════════════════════════════════════════════════════════════════════════

def extract_judge_and_court(
    text: str,
    source_document: Optional[str] = None,
) -> Dict[str, Any]:
    """Nxjerr gjyqtarin, gjykaten dhe afatin e ankeses."""
    result: Dict[str, Any] = {
        "judge_name": None,
        "court_name": None,
        "appeal_deadline": None,
        "appeal_deadline_days": None,
        "source_document": source_document or None,
    }
    if not text:
        return result

    judge_match = JUDGE_NAME_PATTERN.search(text)
    if judge_match:
        result["judge_name"] = judge_match.group(1).strip()

    court_match = COURT_NAME_PATTERN.search(text)
    if court_match:
        result["court_name"] = court_match.group(1).strip()

    appeal_match = APPEAL_DEADLINE_PATTERN.search(text)
    if appeal_match:
        days = int(appeal_match.group(1))
        unit_raw = appeal_match.group(2).lower()
        unit_norm = _normalize_unit(unit_raw)
        result["appeal_deadline"] = f"{days} {unit_norm}"
        result["appeal_deadline_days"] = days

    return result


# ═══════════════════════════════════════════════════════════════════════════
# CONTRADICTIONS — V3.3 (ZONE-AWARE + REPORTED CONTEXT)
# ═══════════════════════════════════════════════════════════════════════════

def _extract_all_periods(
    text: str,
    exclude_positions: Optional[Set[int]] = None,
) -> List[Dict[str, Any]]:
    """V3.2: Nxjerr periudhat + flag `is_reported`."""
    if not text:
        return []
    exclude = exclude_positions or set()
    results: List[Dict[str, Any]] = []
    for match in PERIOD_PATTERN.finditer(text):
        if match.start() in exclude:
            continue
        num = int(match.group(1))
        unit_norm = _normalize_unit(match.group(2))
        is_reported = _is_reported_context(text, match.start())
        results.append({
            "num": num,
            "unit": unit_norm,
            "position": match.start(),
            "context": extract_context(text, match.start(), window=150),
            "is_reported": is_reported,
        })
    return results


def _extract_all_distances(text: str) -> List[Dict[str, Any]]:
    """Nxjerr te gjitha distancat (per kontradikta)."""
    if not text:
        return []
    results = []
    for match in DISTANCE_PATTERN.finditer(text):
        num = int(match.group(1))
        is_reported = _is_reported_context(text, match.start())
        results.append({
            "num": num,
            "unit": "metra",
            "position": match.start(),
            "context": extract_context(text, match.start(), window=100),
            "is_reported": is_reported,
        })
    return results


def detect_contradictions(
    dates: List[Dict[str, Any]],
    deadlines: List[Dict[str, Any]],
    periods: Optional[List[Dict[str, Any]]] = None,
    distances: Optional[List[Dict[str, Any]]] = None,
    text: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """V3.3: Kontradikta zone-aware + reported context."""
    contradictions: List[Dict[str, Any]] = []

    zone_anchors: List[Tuple[int, str]] = []
    if text:
        zone_anchors = _classify_zone_anchors(text)

    def _annotate(items: List[Dict[str, Any]]) -> None:
        if not zone_anchors:
            for it in items:
                it.setdefault("zone", ZONE_UNKNOWN)
            return
        for it in items:
            it["zone"] = _zone_at(zone_anchors, it.get("position", 0))

    # 1. Deadlines
    _annotate(deadlines)
    deadlines_by_zone_unit: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for d in deadlines:
        if not d.get("has_legal_context"):
            continue
        key = (d.get("zone", ZONE_UNKNOWN), d["unit"])
        deadlines_by_zone_unit.setdefault(key, []).append(d)

    for (zone, unit), items in deadlines_by_zone_unit.items():
        if len(items) < 2:
            continue
        unique_nums = set(item["num"] for item in items)
        if len(unique_nums) > 1:
            all_reported = all(item.get("is_reported", False) for item in items)
            kind = "reported" if all_reported else "internal"
            contradictions.append({
                "type": "deadline_inconsistency",
                "kind": kind,
                "zone": zone,
                "zone_label": _zone_label(zone),
                "unit": unit,
                "values": sorted(unique_nums),
                "count": len(items),
                "examples": [item["context"][:150] for item in items[:3]],
            })

    # 2. Periods
    if periods:
        _annotate(periods)
        periods_by_zone_unit: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
        for p in periods:
            key = (p.get("zone", ZONE_UNKNOWN), p["unit"])
            periods_by_zone_unit.setdefault(key, []).append(p)

        for (zone, unit), items in periods_by_zone_unit.items():
            if len(items) < 2:
                continue
            unique_nums = set(item["num"] for item in items)
            if len(unique_nums) <= 1:
                continue
            all_reported = all(item.get("is_reported", False) for item in items)
            kind = "reported" if all_reported else "internal"
            contradictions.append({
                "type": "period_inconsistency",
                "kind": kind,
                "zone": zone,
                "zone_label": _zone_label(zone),
                "unit": unit,
                "values": sorted(unique_nums),
                "count": len(items),
                "examples": [item["context"][:200] for item in items[:3]],
            })

    # 3. Distances
    if distances:
        _annotate(distances)
        distances_by_zone: Dict[str, List[Dict[str, Any]]] = {}
        for d in distances:
            distances_by_zone.setdefault(d.get("zone", ZONE_UNKNOWN), []).append(d)

        for zone, items in distances_by_zone.items():
            unique_distances = set(d["num"] for d in items)
            if len(items) > 1 and len(unique_distances) > 1:
                all_reported = all(item.get("is_reported", False) for item in items)
                kind = "reported" if all_reported else "internal"
                contradictions.append({
                    "type": "distance_inconsistency",
                    "kind": kind,
                    "zone": zone,
                    "zone_label": _zone_label(zone),
                    "unit": "metra",
                    "values": sorted(unique_distances),
                    "count": len(items),
                    "examples": [d["context"][:150] for d in items[:3]],
                })

    return contradictions


# ═══════════════════════════════════════════════════════════════════════════
# BUILD FACT PROFILE — V3.5
# ═══════════════════════════════════════════════════════════════════════════

def build_fact_profile(
    text: str,
    source_document: Optional[str] = None,
) -> Dict[str, Any]:
    """V3.5: Nderton profilin e plote te fakteve + source_document."""
    if not text:
        return {
            "dates": [],
            "deadlines": [],
            "legal_deadlines": [],
            "parties": [],
            "contradictions": [],
            "reported_contradictions": [],
            "dispositive_points": [],
            "medical_findings": [],
            "medical_tests": [],
            "prior_convictions": [],
            "judge_and_court": {},
            "stats": {},
            "source_document": source_document or None,
        }

    dates = extract_dates(text)
    deadlines = extract_deadlines(text, source_document=source_document)
    parties = extract_parties(text)
    dispositive_points = extract_dispositive_points(text)
    medical_findings = extract_medical_findings(text)
    medical_tests = extract_medical_tests(text)
    prior_convictions = extract_prior_convictions(text)
    judge_and_court = extract_judge_and_court(text, source_document=source_document)

    legal_deadlines = [d for d in deadlines if d.get("has_legal_context")]
    legal_positions: Set[int] = {d["position"] for d in legal_deadlines}

    periods = _extract_all_periods(text, exclude_positions=legal_positions)
    distances = _extract_all_distances(text)

    contradictions = detect_contradictions(
        dates, deadlines,
        periods=periods, distances=distances,
        text=text,
    )

    internal_contradictions = [c for c in contradictions if c.get("kind") != "reported"]
    reported_contradictions = [c for c in contradictions if c.get("kind") == "reported"]

    stats = {
        "total_dates": len(dates),
        "total_deadlines": len(deadlines),
        "legal_deadlines": len(legal_deadlines),
        "total_parties": len(parties),
        "total_contradictions": len(contradictions),
        "internal_contradictions": len(internal_contradictions),
        "reported_contradictions": len(reported_contradictions),
        "total_dispositive_points": len(dispositive_points),
        "total_medical_findings": len(medical_findings),
        "total_medical_tests": len(medical_tests),
        "total_prior_convictions": len(prior_convictions),
        "has_judge": bool(judge_and_court.get("judge_name")),
        "has_court": bool(judge_and_court.get("court_name")),
        "has_appeal_deadline": bool(judge_and_court.get("appeal_deadline")),
    }

    logger.info(
        f"🔬 [FACT_EXTRACTOR V3.5] dates={stats['total_dates']}, "
        f"deadlines={stats['total_deadlines']} "
        f"(legal={stats['legal_deadlines']}), "
        f"parties={stats['total_parties']}, "
        f"contradictions={stats['total_contradictions']} "
        f"(internal={stats['internal_contradictions']}, "
        f"reported={stats['reported_contradictions']}), "
        f"dispositive_points={stats['total_dispositive_points']}, "
        f"medical_findings={stats['total_medical_findings']}, "
        f"source={source_document or '(pa emer)'}"
    )

    return {
        "dates": dates,
        "deadlines": deadlines,
        "legal_deadlines": legal_deadlines,
        "parties": parties,
        "contradictions": internal_contradictions,
        "reported_contradictions": reported_contradictions,
        "dispositive_points": dispositive_points,
        "medical_findings": medical_findings,
        "medical_tests": medical_tests,
        "prior_convictions": prior_convictions,
        "judge_and_court": judge_and_court,
        "stats": stats,
        "source_document": source_document or None,
    }