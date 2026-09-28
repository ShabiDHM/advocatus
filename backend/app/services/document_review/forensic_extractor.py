# FILE: backend/app/services/document_review/forensic_extractor.py
# PHOENIX PROTOCOL - FORENSIC EXTRACTOR V1.2
# Nxjerr vlera të strukturuara nga teksti i një dokumenti për analizë
# forensike cross-document.
#
# FILOZOFIA: Ekstraktim DETERMINISTIK (regex + dataclass). Zero LLM.
# Çdo fushë është testueshme veçmas. Nuk vendos "ky është gabim" —
# vetëm nxjerr vlerat. Motor-i (forensic_engine) gjykon.
#
# V1.2: FIX P1 — _extract_document_numbers() filtron numrat 4-shifrorë
#       që janë vite (1900-2100). Shmang false-positive si '2024' si
#       numër dokumenti.
# V1.1: Shtuar `full_text` në DocumentForensicData.
# V1.0: Versioni fillestar.

import logging
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# REGEX PATTERNS
# ═══════════════════════════════════════════════════════════════════════════

_RE_DOC_NUMBER = re.compile(
    r'Numri\s+i\s+dokumentit\s*[:\-]?\s*(\d{4,})',
    re.IGNORECASE | re.UNICODE,
)

_RE_CASE_NUMBER = re.compile(
    r'\b([A-Z][A-Za-z]*)\s*\.?\s*nr\.?\s*(\d+)\s*[\/\-]\s*(\d{2,4})\b',
    re.UNICODE,
)

_RE_DATE_NUMERIC = re.compile(
    r'\b(\d{1,2})\s*[\.\/\-]\s*(\d{1,2})\s*[\.\/\-]\s*(\d{2,4})\b',
)

_RE_DATE_ALB = re.compile(
    r'\b(\d{1,2})\s+'
    r'(janar|shkurt|mars|prill|maj|qershor|korrik|gusht|shtator|tetor|nëntor|dhjetor)'
    r'\s+(\d{4})\b',
    re.IGNORECASE | re.UNICODE,
)

_RE_NUMERIC_CLAIM = re.compile(
    r'\b(\d+(?:[.,]\d+)?)\s*'
    r'(dit[ëe]|jav[ëe]|muaj|vjet?|or[ëe]|minuta?|metra?|kilometra?|%)\b',
    re.IGNORECASE | re.UNICODE,
)

_RE_ROMAN_SECTION = re.compile(
    r'^\s*([IVX]{1,6})\s*[\.\)]\s+(.+?)$',
    re.MULTILINE,
)

_RE_ARABIC_SECTION = re.compile(
    r'^\s*(\d{1,2})\s*[\.\)]\s+([A-ZËÇ][^\n]{5,80})$',
    re.MULTILINE,
)

_ALB_MONTHS = {
    "janar": 1, "shkurt": 2, "mars": 3, "prill": 4, "maj": 5, "qershor": 6,
    "korrik": 7, "gusht": 8, "shtator": 9, "tetor": 10, "nëntor": 11, "dhjetor": 12,
}


# ═══════════════════════════════════════════════════════════════════════════
# DATACLASS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class NumericClaim:
    value: float
    unit: str
    context: str
    position: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": self.value,
            "unit": self.unit,
            "context": self.context,
            "position": self.position,
        }


@dataclass
class Section:
    marker: str
    heading: str
    position: int

    def to_dict(self) -> Dict[str, Any]:
        return {"marker": self.marker, "heading": self.heading, "position": self.position}


@dataclass
class DocumentForensicData:
    file_name: str
    text_length: int
    full_text: str = ""

    document_numbers: Set[str] = field(default_factory=set)
    case_numbers: Set[str] = field(default_factory=set)
    own_case_number: Optional[str] = None

    dates_iso: Set[str] = field(default_factory=set)
    earliest_date: Optional[str] = None
    latest_date: Optional[str] = None

    numeric_claims: List[NumericClaim] = field(default_factory=list)

    sections: List[Section] = field(default_factory=list)
    section_markers: Set[str] = field(default_factory=set)

    doc_type_hints: Set[str] = field(default_factory=set)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_name": self.file_name,
            "text_length": self.text_length,
            "document_numbers": sorted(self.document_numbers),
            "case_numbers": sorted(self.case_numbers),
            "own_case_number": self.own_case_number,
            "dates_iso": sorted(self.dates_iso),
            "earliest_date": self.earliest_date,
            "latest_date": self.latest_date,
            "numeric_claims": [n.to_dict() for n in self.numeric_claims],
            "sections": [s.to_dict() for s in self.sections],
            "section_markers": sorted(self.section_markers),
            "doc_type_hints": sorted(self.doc_type_hints),
        }

    def to_dict_with_text(self) -> Dict[str, Any]:
        d = self.to_dict()
        d["full_text"] = self.full_text
        return d


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _normalize_year(year_str: str) -> int:
    y = int(year_str)
    if y < 100:
        return 2000 + y
    return y


def _safe_iso(d: int, m: int, y: int) -> Optional[str]:
    try:
        dt = date(y, m, d)
        return dt.isoformat()
    except (ValueError, TypeError):
        return None


def _extract_context(text: str, pos: int, window: int = 80) -> str:
    start = max(0, pos - window)
    end = min(len(text), pos + window)
    return text[start:end].replace("\n", " ").strip()


# ═══════════════════════════════════════════════════════════════════════════
# EXTRACTORS
# ═══════════════════════════════════════════════════════════════════════════

def _extract_document_numbers(text: str) -> Set[str]:
    """
    Numra dokumenti — 'Numri i dokumentit: X'.
    V1.2 (FIX P1): Filtro false-positives — numrat 4-shifrorë që janë vite
    (1900-2100) nuk janë numra dokumenti.
    """
    results: Set[str] = set()
    for m in _RE_DOC_NUMBER.finditer(text):
        num = m.group(1)
        if len(num) < 4:
            continue
        try:
            as_int = int(num)
        except ValueError:
            continue
        # Filtro vitet 1900-2100
        if 1900 <= as_int <= 2100:
            continue
        results.add(num)
    return results


def _extract_case_numbers(text: str) -> Set[str]:
    results = set()
    for m in _RE_CASE_NUMBER.finditer(text):
        prefix = m.group(1).strip().upper()
        num = m.group(2)
        year = _normalize_year(m.group(3))
        results.add(f"{prefix}.nr.{num}/{year}")
    return results


def _extract_dates(text: str) -> Set[str]:
    dates: Set[str] = set()

    for m in _RE_DATE_NUMERIC.finditer(text):
        d, mo, y = int(m.group(1)), int(m.group(2)), _normalize_year(m.group(3))
        iso = _safe_iso(d, mo, y)
        if iso:
            dates.add(iso)

    for m in _RE_DATE_ALB.finditer(text):
        d = int(m.group(1))
        mo = _ALB_MONTHS.get(m.group(2).lower())
        y = int(m.group(3))
        if mo:
            iso = _safe_iso(d, mo, y)
            if iso:
                dates.add(iso)

    return dates


def _extract_numeric_claims(text: str) -> List[NumericClaim]:
    claims: List[NumericClaim] = []
    for m in _RE_NUMERIC_CLAIM.finditer(text):
        try:
            value = float(m.group(1).replace(",", "."))
        except ValueError:
            continue
        unit_raw = m.group(2).lower()
        if unit_raw.startswith("dit"):
            unit = "ditë"
        elif unit_raw.startswith("jav"):
            unit = "javë"
        elif unit_raw.startswith("muaj"):
            unit = "muaj"
        elif unit_raw.startswith("vjet") or unit_raw.startswith("vit"):
            unit = "vjet"
        elif unit_raw.startswith("or"):
            unit = "orë"
        elif unit_raw.startswith("metra") or unit_raw.startswith("kilometra"):
            unit = "metra"
        elif unit_raw.startswith("minuta"):
            unit = "minuta"
        else:
            unit = unit_raw

        claims.append(NumericClaim(
            value=value,
            unit=unit,
            context=_extract_context(text, m.start(), window=80),
            position=m.start(),
        ))
    return claims


def _extract_sections(text: str) -> List[Section]:
    sections: List[Section] = []

    for m in _RE_ROMAN_SECTION.finditer(text):
        heading = m.group(2).strip()
        if 5 < len(heading) < 200:
            sections.append(Section(
                marker=m.group(1), heading=heading[:200], position=m.start()
            ))

    if not sections:
        for m in _RE_ARABIC_SECTION.finditer(text):
            heading = m.group(2).strip()
            sections.append(Section(
                marker=m.group(1), heading=heading[:200], position=m.start()
            ))

    return sections


def _infer_doc_type_hints(text: str) -> Set[str]:
    text_upper = text[:5000].upper()
    hints: Set[str] = set()

    if re.search(r'\b(AKTVENDIM|AKTGJYKIM|VENDIM)\b', text_upper):
        hints.add("decision")

    if re.search(r'\bPROCESVERBAL\b', text_upper):
        hints.add("session_protocol")

    if re.search(
        r'\b(PSIKIATRI|EKSPERTIZ[ËE]?\s+PSIKIATRIKE|MENDIM[I]?\s+(I\s+)?EKSPERT[ËE]VE)\b',
        text_upper,
    ):
        hints.add("psychiatric_report")

    if re.search(r'\b(TEST|TOKSIKOLOGJI|NARKOTIK)\b', text_upper):
        hints.add("test_report")

    if re.search(r'\bURDH[ËE]R\s*MBROJT', text_upper):
        hints.add("protection_order")

    return hints


# ═══════════════════════════════════════════════════════════════════════════
# MAIN API
# ═══════════════════════════════════════════════════════════════════════════

def extract_forensic_data(text: str, file_name: str) -> DocumentForensicData:
    if not text:
        return DocumentForensicData(
            file_name=file_name,
            text_length=0,
            full_text="",
        )

    doc_numbers = _extract_document_numbers(text)
    case_numbers = _extract_case_numbers(text)
    dates = _extract_dates(text)
    numeric_claims = _extract_numeric_claims(text)
    sections = _extract_sections(text)
    doc_type_hints = _infer_doc_type_hints(text)

    sorted_dates = sorted(dates)
    earliest = sorted_dates[0] if sorted_dates else None
    latest = sorted_dates[-1] if sorted_dates else None

    own_case: Optional[str] = None
    header_zone = text[:2000]
    header_cases = _extract_case_numbers(header_zone)
    if header_cases:
        own_case = sorted(header_cases)[0]

    return DocumentForensicData(
        file_name=file_name,
        text_length=len(text),
        full_text=text,
        document_numbers=doc_numbers,
        case_numbers=case_numbers,
        own_case_number=own_case,
        dates_iso=dates,
        earliest_date=earliest,
        latest_date=latest,
        numeric_claims=numeric_claims,
        sections=sections,
        section_markers=set(s.marker for s in sections),
        doc_type_hints=doc_type_hints,
    )