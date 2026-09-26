# FILE: backend/app/services/document_review/fact_extractor.py
# PHOENIX PROTOCOL - FACT EXTRACTOR V3.17
# V3.17: EXPANDED PERIOD/DEADLINE PATTERN — Prano mbarime rasore shqipe:
#        "muaj"/"muajsh"/"muajve", "ditë"/"ditësh"/"ditëve", "javë"/"javësh"/"javëve",
#        "vjet"/"vite"/"vitesh"/"vitit". Zbulo kontradikta "6 muaj" vs "12 muajve".
# V3.16: PREFIX-BASED ROOTS.
# V3.15: SENTENCE-BOUNDED CONTEXT.
# V3.12: ROLE-BASED SUSPECT EXTRACTION.

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
    NUMBERED_LINE_PATTERN,
    is_valid_person_name,
)
from .helpers import (
    parse_date,
    month_name_to_number,
    extract_context,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# V3.17: EXPANDED PERIOD/DEADLINE PATTERN — override lokal
# ═══════════════════════════════════════════════════════════════════════════

# V3.17: Prano të gjitha mbarimet rasore shqipe:
#   ditë / ditësh / ditëve / dite / ditesh / diteve
#   muaj / muajsh / muajve
#   javë / javësh / javëve / jave / javesh / javeve
#   vit / vjet / vite / vitesh / viteve / vitit
_EXPANDED_PERIOD_PATTERN = re.compile(
    r'\b(\d+)\s*'
    r'('
    r'dit(?:ë|e)?(?:sh|ve)?'
    r'|muaj(?:sh|ve)?'
    r'|jav(?:ë|e)?(?:sh|ve)?'
    r'|vjet(?:sh|ve)?'
    r'|vit(?:e|esh|eve|it)?'
    r')'
    r'\b',
    re.IGNORECASE | re.UNICODE,
)


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


_REPORTING_REF_PATTERN = re.compile(
    r'(?:'
    r'në\s+Aktvendimin|në\s+Aktgjykimin|në\s+Vendimin|në\s+Aktin|'
    r'sipas\s+Aktvendimit|sipas\s+Aktgjykimit|sipas\s+Vendimit|sipas\s+Aktit|'
    r'referuar\s+në|referohet\s+në|bazuar\s+në|citim\s+i|'
    r'Aktvendimi\s+(?:Nr\.?|nr\.?)\s*\S+|'
    r'Aktgjykimi\s+(?:Nr\.?|nr\.?)\s*\S+|'
    r'Vendimi\s+(?:Nr\.?|nr\.?)\s*\S+|'
    r'Akti\s+(?:Nr\.?|nr\.?)\s*\S+|'
    r'C\.nr\.?\s*\d+(?:/\d+)?|'
    r'CA\.nr\.?\s*\d+(?:/\d+)?|'
    r'P\.nr\.?\s*\d+(?:/\d+)?'
    r')',
    re.IGNORECASE | re.UNICODE,
)

_REPORTED_CONTEXT_WINDOW = 400


def _normalize_cn_for_match(s: str) -> str:
    if not s:
        return ""
    return re.sub(r'[\s\.\-]+', '', s.upper())


def _is_reported_context(
    text: str,
    position: int,
    window: int = _REPORTED_CONTEXT_WINDOW,
    own_case_numbers: Optional[Set[str]] = None,
) -> bool:
    if not text:
        return False
    start = max(0, position - window)
    end = min(len(text), position + window)
    context = text[start:end]

    refs = [m.group(0) for m in _REPORTING_REF_PATTERN.finditer(context)]
    if not refs:
        return False

    if own_case_numbers:
        own_normalized = {
            _normalize_cn_for_match(cn) for cn in own_case_numbers if cn
        }
        for ref in refs:
            ref_norm = _normalize_cn_for_match(ref)
            if not ref_norm:
                continue
            if not any(ch.isdigit() for ch in ref_norm):
                continue

            is_self = False
            for own_norm in own_normalized:
                if not own_norm or len(own_norm) < 4:
                    continue
                if ref_norm in own_norm or own_norm in ref_norm:
                    is_self = True
                    break
            if not is_self:
                return True

        return False

    return True


def _classify_zone_anchors(text: str) -> List[Tuple[int, str]]:
    if not text:
        return []
    anchors: List[Tuple[int, str]] = []
    for zone_name, pattern in ZONE_ANCHORS:
        for m in re.finditer(pattern, text, re.IGNORECASE | re.UNICODE):
            anchors.append((m.start(), zone_name))
    anchors.sort(key=lambda x: x[0])
    return anchors


def _zone_at(anchors: List[Tuple[int, str]], position: int) -> str:
    current = ZONE_UNKNOWN
    for pos, zone in anchors:
        if pos > position:
            break
        current = zone
    return current


def _zone_label(zone: str) -> str:
    return {
        "facts": "Fakte",
        "reasoning": "Arsyetim",
        "dispositive": "Dispozitiv",
        "proposal": "Propozim/Kerkese",
        "reported": "Raportim (citim i dokumentit tjeter)",
        ZONE_UNKNOWN: "Pa zone (hyrie/header)",
    }.get(zone, zone)


def _normalize_unit(unit_raw: str) -> str:
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
# V3.15: SENTENCE-BOUNDED CONTEXT
# ═══════════════════════════════════════════════════════════════════════════

_SENTENCE_SEPARATORS = ('. ', '; ', ': ', '! ', '? ', '\n')


def _extract_sentence_context(
    text: str,
    position: int,
    value_length: int,
    max_lookback: int = 120,
    max_lookahead: int = 120,
) -> str:
    if not text:
        return ""

    back_start = max(0, position - max_lookback)
    pre_segment = text[back_start:position]

    best_start = back_start
    best_pre_idx = -1
    for sep in _SENTENCE_SEPARATORS:
        idx = pre_segment.rfind(sep)
        if idx > best_pre_idx:
            best_pre_idx = idx
            best_start = back_start + idx + len(sep)

    start = best_start

    value_end = position + value_length
    forward_end = min(len(text), value_end + max_lookahead)
    post_segment = text[value_end:forward_end]

    best_end = forward_end
    best_post_idx = -1
    for sep in _SENTENCE_SEPARATORS:
        idx = post_segment.find(sep)
        if idx != -1 and (best_post_idx == -1 or idx < best_post_idx):
            best_post_idx = idx
            best_end = value_end + idx + len(sep)

    return text[start:best_end].strip()


# ═══════════════════════════════════════════════════════════════════════════
# EXTRACT DATES
# ═══════════════════════════════════════════════════════════════════════════

def extract_dates(text: str) -> List[Dict[str, Any]]:
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
# EXTRACT DEADLINES
# ═══════════════════════════════════════════════════════════════════════════

def extract_deadlines(
    text: str,
    source_document: Optional[str] = None,
    own_case_numbers: Optional[Set[str]] = None,
) -> List[Dict[str, Any]]:
    if not text:
        return []

    results: List[Dict[str, Any]] = []

    # V3.17: Përdor _EXPANDED_PERIOD_PATTERN (pranon muajve/ditëve/javëve)
    for match in _EXPANDED_PERIOD_PATTERN.finditer(text):
        num = int(match.group(1))
        unit_norm = _normalize_unit(match.group(2))
        context = extract_context(text, match.start(), window=120)
        value_len = match.end() - match.start()
        sentence_ctx = _extract_sentence_context(text, match.start(), value_len)
        context_lower = context.lower()
        has_legal_context = any(
            kw in context_lower for kw in DEADLINE_CONTEXT_KEYWORDS
        )
        is_reported = _is_reported_context(
            text, match.start(), own_case_numbers=own_case_numbers
        )
        results.append({
            "num": num,
            "unit": unit_norm,
            "display": f"{num} {unit_norm}",
            "position": match.start(),
            "context": context[:MAX_CONTEXT_CHARS],
            "sentence_context": sentence_ctx[:MAX_CONTEXT_CHARS],
            "has_legal_context": has_legal_context,
            "source_document": source_document or None,
            "is_reported": is_reported,
        })

    return results


# ═══════════════════════════════════════════════════════════════════════════
# EXTRACT PARTIES
# ═══════════════════════════════════════════════════════════════════════════

def extract_parties(text: str) -> List[Dict[str, Any]]:
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
# V3.12: ROLE-BASED SUSPECT EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════

_LINE_SEPARATORS_RE = re.compile(r'\s+[—–]\s+|\s+-\s+')


def _split_comma_names(s: str) -> List[str]:
    if not s or ',' not in s:
        return []

    pieces = s.split(',')
    names: List[str] = []
    for piece in pieces:
        clean = piece.strip()
        clean = re.split(r'\s+[—–-]\s+', clean, maxsplit=1)[0].strip()
        if is_valid_person_name(clean):
            names.append(clean)

    return names if len(names) >= 2 else []


def _try_parse_line(line: str) -> List[Tuple[str, str]]:
    if not line:
        return []

    line = line.strip()
    if len(line) < 5 or len(line) > 400:
        return []

    line = re.sub(r'^\s*\d+\s*[\.\)]\s*', '', line).strip()

    if ':' in line:
        before, _, after = line.partition(':')
        before = before.strip()
        after = after.strip()

        names = _split_comma_names(after)
        if len(names) >= 2:
            return [(n, "") for n in names]

        if is_valid_person_name(before) and len(after) >= 3:
            return [(before, after[:200])]

    if ',' in line:
        names = _split_comma_names(line)
        if len(names) >= 2:
            return [(n, "") for n in names]

    m = _LINE_SEPARATORS_RE.split(line, maxsplit=1)
    if len(m) == 2:
        left = m[0].strip()
        right = m[1].strip()
        if is_valid_person_name(left) and len(right) >= 3:
            return [(left, right[:200])]

    return []


def extract_suspects(text: str) -> List[Dict[str, Any]]:
    if not text:
        return []

    results: List[Dict[str, Any]] = []
    seen_names: Set[str] = set()

    lines = text.split("\n")
    current_pos = 0

    for line in lines:
        line_start = current_pos
        current_pos += len(line) + 1

        pairs = _try_parse_line(line)
        for name, role in pairs:
            key = name.lower().strip()
            if key in seen_names:
                continue
            seen_names.add(key)
            results.append({
                "index": len(results) + 1,
                "name": name,
                "position_hint": role,
                "context": extract_context(text, line_start, window=200),
                "position": line_start,
            })

    return results


# ═══════════════════════════════════════════════════════════════════════════
# EXTRACT DISPOSITIVE POINTS
# ═══════════════════════════════════════════════════════════════════════════

def extract_dispositive_points(text: str) -> List[Dict[str, Any]]:
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
# EXTRACT MEDICAL FINDINGS
# ═══════════════════════════════════════════════════════════════════════════

def extract_medical_findings(text: str) -> List[Dict[str, Any]]:
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
# EXTRACT MEDICAL TESTS
# ═══════════════════════════════════════════════════════════════════════════

def extract_medical_tests(text: str) -> List[Dict[str, Any]]:
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
# CONTRADICTIONS
# ═══════════════════════════════════════════════════════════════════════════

def _extract_all_periods(
    text: str,
    exclude_positions: Optional[Set[int]] = None,
    own_case_numbers: Optional[Set[str]] = None,
) -> List[Dict[str, Any]]:
    if not text:
        return []
    exclude = exclude_positions or set()
    results: List[Dict[str, Any]] = []
    # V3.17: Përdor _EXPANDED_PERIOD_PATTERN
    for match in _EXPANDED_PERIOD_PATTERN.finditer(text):
        if match.start() in exclude:
            continue
        num = int(match.group(1))
        unit_norm = _normalize_unit(match.group(2))
        value_len = match.end() - match.start()
        is_reported = _is_reported_context(
            text, match.start(), own_case_numbers=own_case_numbers
        )
        results.append({
            "num": num,
            "unit": unit_norm,
            "position": match.start(),
            "context": extract_context(text, match.start(), window=150),
            "sentence_context": _extract_sentence_context(
                text, match.start(), value_len
            )[:MAX_CONTEXT_CHARS],
            "is_reported": is_reported,
        })
    return results


def _extract_all_distances(
    text: str,
    own_case_numbers: Optional[Set[str]] = None,
) -> List[Dict[str, Any]]:
    if not text:
        return []
    results = []
    for match in DISTANCE_PATTERN.finditer(text):
        num = int(match.group(1))
        value_len = match.end() - match.start()
        is_reported = _is_reported_context(
            text, match.start(), own_case_numbers=own_case_numbers
        )
        results.append({
            "num": num,
            "unit": "metra",
            "position": match.start(),
            "context": extract_context(text, match.start(), window=100),
            "sentence_context": _extract_sentence_context(
                text, match.start(), value_len
            )[:MAX_CONTEXT_CHARS],
            "is_reported": is_reported,
        })
    return results


# ═══════════════════════════════════════════════════════════════════════════
# V3.16: PREFIX-BASED ROOT MATCHING (Albanian morphology)
# ═══════════════════════════════════════════════════════════════════════════

_CONTEXT_STOPWORDS = frozenset([
    "gjykata", "gjykatës", "gjykate", "gjykatë",
    "vendimi", "vendimit", "vendim", "vendime", "vendimet",
    "aktvendimi", "aktvendim", "aktgjykimi", "aktgjykim",
    "ligji", "ligjit", "ligjin", "ligje", "ligjet",
    "kodi", "kodit", "kodin", "kodet",
    "neni", "nenit", "nenin", "nenet", "nenët",
    "pika", "pikat", "pikës", "pikes",
    "paragrafi", "paragrafit", "paragrafin",
    "këtë", "ketë", "këtij", "ketij", "kësaj", "kesaj",
    "nga", "për", "per", "me", "pa", "në", "ne",
    "dhe", "ose", "por", "kur", "ku", "si", "sa",
    "është", "eshte", "janë", "jane", "ishte", "kanë", "kane",
    "kjo", "ky", "këto", "keto", "këta", "keta", "ato", "ata",
    "gjithashtu", "përfundimisht", "perfundimisht",
    "sipas", "të", "te", "i", "e", "a", "u",
])

ROOT_PREFIX_LEN = 5


def _extract_context_roots(ctx: str, prefix_len: int = ROOT_PREFIX_LEN) -> Set[str]:
    if not ctx:
        return set()
    words = re.findall(r'[a-zA-ZëçËÇ]{5,}', ctx.lower())
    roots: Set[str] = set()
    for w in words:
        if w in _CONTEXT_STOPWORDS:
            continue
        roots.add(w[:prefix_len] if len(w) > prefix_len else w)
    return roots


def _contexts_share_topic(
    items: List[Dict[str, Any]],
    min_shared: int = 1,
) -> bool:
    if len(items) < 2:
        return False

    root_sets = [
        _extract_context_roots(it.get("sentence_context", ""))
        for it in items
    ]

    for i in range(len(root_sets)):
        for j in range(i + 1, len(root_sets)):
            if len(root_sets[i] & root_sets[j]) >= min_shared:
                return True

    return False


def detect_contradictions(
    dates: List[Dict[str, Any]],
    deadlines: List[Dict[str, Any]],
    periods: Optional[List[Dict[str, Any]]] = None,
    distances: Optional[List[Dict[str, Any]]] = None,
    text: Optional[str] = None,
    own_case_numbers: Optional[Set[str]] = None,
) -> List[Dict[str, Any]]:
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

    EXAMPLE_CHARS = 250
    EXAMPLE_LIMIT = 4

    # ─── 1. Deadlines ───
    _annotate(deadlines)
    deadlines_by_unit: Dict[str, List[Dict[str, Any]]] = {}
    for d in deadlines:
        if not d.get("has_legal_context"):
            continue
        deadlines_by_unit.setdefault(d["unit"], []).append(d)

    for unit, items in deadlines_by_unit.items():
        if len(items) < 2:
            continue
        unique_nums = set(item["num"] for item in items)
        if len(unique_nums) <= 1:
            continue

        if not _contexts_share_topic(items, min_shared=1):
            logger.info(
                f"⏭️ [V3.17 CONTRADICTION SKIP] deadline {unit} "
                f"{sorted(unique_nums)} — kontekst i ndryshëm."
            )
            continue

        all_reported = all(item.get("is_reported", False) for item in items)
        kind = "reported" if all_reported else "internal"
        zones_present = sorted({item.get("zone", ZONE_UNKNOWN) for item in items})
        contradictions.append({
            "type": "deadline_inconsistency",
            "kind": kind,
            "zone": zones_present[0] if len(zones_present) == 1 else "cross_zone",
            "zone_label": (
                _zone_label(zones_present[0])
                if len(zones_present) == 1
                else f"Cross-zone: {', '.join(_zone_label(z) for z in zones_present)}"
            ),
            "unit": unit,
            "values": sorted(unique_nums),
            "count": len(items),
            "examples": [item["context"][:EXAMPLE_CHARS] for item in items[:EXAMPLE_LIMIT]],
        })

    # ─── 2. Periods ───
    if periods:
        _annotate(periods)
        periods_by_unit: Dict[str, List[Dict[str, Any]]] = {}
        for p in periods:
            periods_by_unit.setdefault(p["unit"], []).append(p)

        for unit, items in periods_by_unit.items():
            if len(items) < 2:
                continue
            unique_nums = set(item["num"] for item in items)
            if len(unique_nums) <= 1:
                continue

            if not _contexts_share_topic(items, min_shared=1):
                logger.info(
                    f"⏭️ [V3.17 CONTRADICTION SKIP] period {unit} "
                    f"{sorted(unique_nums)} — kontekst i ndryshëm."
                )
                continue

            all_reported = all(item.get("is_reported", False) for item in items)
            kind = "reported" if all_reported else "internal"
            zones_present = sorted({item.get("zone", ZONE_UNKNOWN) for item in items})
            contradictions.append({
                "type": "period_inconsistency",
                "kind": kind,
                "zone": zones_present[0] if len(zones_present) == 1 else "cross_zone",
                "zone_label": (
                    _zone_label(zones_present[0])
                    if len(zones_present) == 1
                    else f"Cross-zone: {', '.join(_zone_label(z) for z in zones_present)}"
                ),
                "unit": unit,
                "values": sorted(unique_nums),
                "count": len(items),
                "examples": [item["context"][:EXAMPLE_CHARS] for item in items[:EXAMPLE_LIMIT]],
            })

    # ─── 3. Distances ───
    if distances:
        _annotate(distances)
        distances_by_unit: Dict[str, List[Dict[str, Any]]] = {}
        for d in distances:
            distances_by_unit.setdefault(d["unit"], []).append(d)

        for unit, items in distances_by_unit.items():
            unique_distances = set(d["num"] for d in items)
            if len(items) <= 1 or len(unique_distances) <= 1:
                continue

            if not _contexts_share_topic(items, min_shared=1):
                logger.info(
                    f"⏭️ [V3.17 CONTRADICTION SKIP] distance {unit} "
                    f"{sorted(unique_distances)} — kontekst i ndryshëm."
                )
                continue

            all_reported = all(item.get("is_reported", False) for item in items)
            kind = "reported" if all_reported else "internal"
            zones_present = sorted({item.get("zone", ZONE_UNKNOWN) for item in items})
            contradictions.append({
                "type": "distance_inconsistency",
                "kind": kind,
                "zone": zones_present[0] if len(zones_present) == 1 else "cross_zone",
                "zone_label": (
                    _zone_label(zones_present[0])
                    if len(zones_present) == 1
                    else f"Cross-zone: {', '.join(_zone_label(z) for z in zones_present)}"
                ),
                "unit": unit,
                "values": sorted(unique_distances),
                "count": len(items),
                "examples": [d["context"][:EXAMPLE_CHARS] for d in items[:EXAMPLE_LIMIT]],
            })

    return contradictions


# ═══════════════════════════════════════════════════════════════════════════
# BUILD FACT PROFILE — V3.17
# ═══════════════════════════════════════════════════════════════════════════

def build_fact_profile(
    text: str,
    source_document: Optional[str] = None,
    own_case_numbers: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    if not text:
        return {
            "dates": [],
            "deadlines": [],
            "legal_deadlines": [],
            "parties": [],
            "suspects": [],
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

    own_cns: Set[str] = set(own_case_numbers or set())

    dates = extract_dates(text)
    deadlines = extract_deadlines(
        text,
        source_document=source_document,
        own_case_numbers=own_cns,
    )
    parties = extract_parties(text)
    suspects = extract_suspects(text)
    dispositive_points = extract_dispositive_points(text)
    medical_findings = extract_medical_findings(text)
    medical_tests = extract_medical_tests(text)
    prior_convictions = extract_prior_convictions(text)
    judge_and_court = extract_judge_and_court(text, source_document=source_document)

    legal_deadlines = [d for d in deadlines if d.get("has_legal_context")]
    legal_positions: Set[int] = {d["position"] for d in legal_deadlines}

    periods = _extract_all_periods(
        text,
        exclude_positions=legal_positions,
        own_case_numbers=own_cns,
    )
    distances = _extract_all_distances(text, own_case_numbers=own_cns)

    contradictions = detect_contradictions(
        dates, deadlines,
        periods=periods, distances=distances,
        text=text,
        own_case_numbers=own_cns,
    )

    internal_contradictions = [c for c in contradictions if c.get("kind") != "reported"]
    reported_contradictions = [c for c in contradictions if c.get("kind") == "reported"]

    stats = {
        "total_dates": len(dates),
        "total_deadlines": len(deadlines),
        "legal_deadlines": len(legal_deadlines),
        "total_parties": len(parties),
        "total_suspects": len(suspects),
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
        f"🔬 [FACT_EXTRACTOR V3.17] dates={stats['total_dates']}, "
        f"deadlines={stats['total_deadlines']} "
        f"(legal={stats['legal_deadlines']}), "
        f"parties={stats['total_parties']}, "
        f"suspects={stats['total_suspects']}, "
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
        "suspects": suspects,
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