# FILE: backend/app/services/document_review/hallucination_checker.py
# PHOENIX PROTOCOL - HALLUCINATION CHECKER V1.5
# V1.5: SPLIT ARTICLE LISTS — "Neni 137, 138, 143" tani split-ohet në 3 vlera
#       të veçanta para se të krahasohet me allowed. Kjo eliminon false-positives
#       të prodhuara nga ARTICLE_PATTERN V2.5 (që kap lista me presje).
# V1.4: Skip prefixes numrave të lendeve.
# V1.3: Precedente të vërteta.
# V1.2: FIX rstrip.
# V1.1: FIX normalizim.
# V1.0: Post-check mbi output-in e LLM.

import re
import logging
from typing import Dict, Any, List, Optional, Set

from .patterns import (
    DATE_PATTERN,
    DATE_ALBANIAN_PATTERN,
    ARTICLE_PATTERN,
    LAW_NUMBER_PATTERN,
    LAW_NUMBER_WITH_NAME_PATTERN,
    CASE_NUMBER_PATTERN,
    ABBREV_PATTERN,
)
from .helpers import (
    parse_date,
    month_name_to_number,
    normalize_law_number,
    normalize_case_number,
    is_valid_law_abbrev,
)
from .citation_extractor import _normalize_article_number

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# V1.4: PREFIXE NUMRASH LENDEJSH (nuk jane akronime ligjesh)
# ═══════════════════════════════════════════════════════════════════════════

CASE_NUMBER_PREFIXES: Set[str] = {
    "PA1", "PKR", "PML", "REV", "KMLP", "ANR", "PZR",
    "CP", "AC", "PN", "KP", "ARJ", "A", "P",
    "KPK", "KPPRK", "KPRK",
}


# ═══════════════════════════════════════════════════════════════════════════
# V1.5: SPLIT ARTICLE LISTS
# ═══════════════════════════════════════════════════════════════════════════

def _split_article_numbers(raw: str) -> List[str]:
    """
    V1.5: Ndan "137, 138, 143 dhe 144" → ['137', '138', '143', '144'].
    Trajton presje, pikëpresje, dhe 'dhe'.
    """
    if not raw:
        return []
    parts = re.split(r'\s*[,;]\s*|\s+dhe\s+', raw.strip())
    return [p.strip() for p in parts if p.strip()]


# ═══════════════════════════════════════════════════════════════════════════
# V1.3: NORMALIZIM PRECEDENTESH
# ═══════════════════════════════════════════════════════════════════════════

def _normalize_precedent_case(case_number: str) -> Optional[str]:
    if not case_number:
        return None

    m = CASE_NUMBER_PATTERN.search(case_number)
    if m:
        prefix = m.group(1).upper()
        num_part = m.group(2).rstrip(".,;:")
        if not num_part:
            return None
        raw = f"{prefix}.nr.{num_part}"
        return normalize_case_number(raw)

    return normalize_case_number(case_number) or case_number.upper().strip()


# ═══════════════════════════════════════════════════════════════════════════
# EXTRACTORS
# ═══════════════════════════════════════════════════════════════════════════

def _extract_dates_iso(text: str) -> Set[str]:
    found: Set[str] = set()
    if not text:
        return found

    for m in DATE_PATTERN.finditer(text):
        dt = parse_date(m.group(1), m.group(2), m.group(3))
        if dt:
            found.add(dt.isoformat()[:10])

    for m in DATE_ALBANIAN_PATTERN.finditer(text):
        month_num = month_name_to_number(m.group(2))
        if not month_num:
            continue
        dt = parse_date(m.group(1), str(month_num), m.group(3))
        if dt:
            found.add(dt.isoformat()[:10])

    return found


def _extract_articles(text: str) -> Set[str]:
    """
    V1.5: Nxjerr nenet, duke SPLIT-uar listat me presje.
    "Neni 137, 138, 143" → {"137", "138", "143"}
    """
    found: Set[str] = set()
    if not text:
        return found

    for m in ARTICLE_PATTERN.finditer(text):
        art_raw = m.group(1)
        par_raw = m.group(2)

        # V1.5: Split lista "137, 138, 143"
        parts = _split_article_numbers(art_raw)
        for part in parts:
            if not part:
                continue
            art, _ = _normalize_article_number(part, par_raw)
            if art:
                found.add(art)

    return found


def _extract_laws(text: str) -> Set[str]:
    found: Set[str] = set()
    if not text:
        return found

    for m in LAW_NUMBER_WITH_NAME_PATTERN.finditer(text):
        n = normalize_law_number(m.group(1))
        if n:
            found.add(n)

    for m in LAW_NUMBER_PATTERN.finditer(text):
        n = normalize_law_number(m.group(0))
        if n:
            found.add(n)

    return found


def _extract_cases(text: str) -> Set[str]:
    found: Set[str] = set()
    if not text:
        return found

    for m in CASE_NUMBER_PATTERN.finditer(text):
        prefix = m.group(1).upper()
        num_part = m.group(2).rstrip(".,;:")
        if not num_part:
            continue
        raw = f"{prefix}.nr.{num_part}"
        n = normalize_case_number(raw)
        if n:
            found.add(n)

    return found


def _extract_abbrevs(text: str) -> Set[str]:
    found: Set[str] = set()
    if not text:
        return found

    for m in ABBREV_PATTERN.finditer(text):
        abbr = m.group(1)
        abbr_up = abbr.upper()

        if abbr_up in CASE_NUMBER_PREFIXES:
            continue

        if is_valid_law_abbrev(abbr):
            found.add(abbr_up)

    return found


# ═══════════════════════════════════════════════════════════════════════════
# CONTEXT SNIPPET
# ═══════════════════════════════════════════════════════════════════════════

def _find_snippet(text: str, value: str, window: int = 80) -> str:
    if not text or not value:
        return ""
    idx = text.find(value)
    if idx == -1:
        return ""
    start = max(0, idx - window)
    end = min(len(text), idx + len(value) + window)
    snippet = text[start:end].replace("\n", " ").strip()
    return f"...{snippet}..."


# ═══════════════════════════════════════════════════════════════════════════
# CHECKER CLASS
# ═══════════════════════════════════════════════════════════════════════════

class HallucinationChecker:
    def __init__(
        self,
        citation_profile: Dict[str, Any],
        fact_profile: Dict[str, Any],
        verification_report: Dict[str, Any],
        extra_allowed_cases: Optional[Set[str]] = None,
    ):
        self.allowed = self._build_allowed(
            citation_profile,
            fact_profile,
            verification_report,
            extra_allowed_cases=extra_allowed_cases,
        )
        logger.info(
            f"[HALLUCINATION V1.5] Allowed values: "
            f"dates={len(self.allowed['dates_iso'])}, "
            f"laws={len(self.allowed['laws'])}, "
            f"articles={len(self.allowed['articles'])}, "
            f"cases={len(self.allowed['cases'])}, "
            f"abbrevs={len(self.allowed['abbrevs'])}"
        )

    @staticmethod
    def _build_allowed(
        citation_profile: Dict[str, Any],
        fact_profile: Dict[str, Any],
        verification_report: Dict[str, Any],
        extra_allowed_cases: Optional[Set[str]] = None,
    ) -> Dict[str, Set[str]]:
        dates_iso: Set[str] = set()
        for d in fact_profile.get("dates", []) or []:
            if d.get("iso"):
                dates_iso.add(d["iso"])

        laws: Set[str] = set()
        for l in citation_profile.get("laws_by_number", []) or []:
            if l.get("number"):
                n = normalize_law_number(l["number"]) or l["number"]
                laws.add(n)
        for l in verification_report.get("laws_by_number", []) or []:
            if l.get("number"):
                n = normalize_law_number(l["number"]) or l["number"]
                laws.add(n)

        articles: Set[str] = set()
        for a in citation_profile.get("articles", []) or []:
            if a.get("number"):
                articles.add(a["number"])

        cases: Set[str] = set()
        for c in citation_profile.get("case_numbers", []) or []:
            if c.get("case_number"):
                n = normalize_case_number(c["case_number"]) or c["case_number"]
                cases.add(n)

        if extra_allowed_cases:
            for cn in extra_allowed_cases:
                if not cn:
                    continue
                norm = _normalize_precedent_case(cn)
                if norm:
                    cases.add(norm)
                cases.add(cn.upper().strip())

        abbrevs: Set[str] = set()
        for a in citation_profile.get("abbreviations", []) or []:
            abbrevs.add(a.upper())

        return {
            "dates_iso": dates_iso,
            "laws": laws,
            "articles": articles,
            "cases": cases,
            "abbrevs": abbrevs,
        }

    def _check_dates(self, content: str) -> List[Dict[str, Any]]:
        found = _extract_dates_iso(content)
        unknown = found - self.allowed["dates_iso"]
        issues = []
        for d in sorted(unknown):
            issues.append({
                "type": "date",
                "value": d,
                "severity": "high",
                "message": f"Data '{d}' nuk shfaqet ne faktet e dokumentit.",
                "snippet": _find_snippet(content, d),
            })
        return issues

    def _check_articles(self, content: str) -> List[Dict[str, Any]]:
        found = _extract_articles(content)
        unknown = found - self.allowed["articles"]
        issues = []
        for a in sorted(unknown):
            issues.append({
                "type": "article",
                "value": f"Neni {a}",
                "severity": "medium",
                "message": f"Neni {a} nuk u gjet ne citimet e dokumentit.",
                "snippet": _find_snippet(content, f"Neni {a}") or _find_snippet(content, f"Nenit {a}"),
            })
        return issues

    def _check_laws(self, content: str) -> List[Dict[str, Any]]:
        found = _extract_laws(content)
        unknown = found - self.allowed["laws"]
        issues = []
        for l in sorted(unknown):
            issues.append({
                "type": "law",
                "value": l,
                "severity": "medium",
                "message": f"Ligji '{l}' nuk u gjet ne citimet e dokumentit.",
                "snippet": _find_snippet(content, l),
            })
        return issues

    def _check_cases(self, content: str) -> List[Dict[str, Any]]:
        found = _extract_cases(content)
        unknown = found - self.allowed["cases"]
        issues = []
        for c in sorted(unknown):
            issues.append({
                "type": "case_number",
                "value": c,
                "severity": "high",
                "message": f"Numri i lendes '{c}' nuk u gjet ne dokument.",
                "snippet": _find_snippet(content, c),
            })
        return issues

    def _check_abbrevs(self, content: str) -> List[Dict[str, Any]]:
        found = _extract_abbrevs(content)
        unknown = found - self.allowed["abbrevs"]
        issues = []
        for a in sorted(unknown):
            issues.append({
                "type": "abbreviation",
                "value": a,
                "severity": "low",
                "message": f"Akronimi '{a}' nuk u gjet ne citimet e dokumentit.",
                "snippet": _find_snippet(content, a),
            })
        return issues

    def check_section(
        self,
        section_key: str,
        content: str,
    ) -> Dict[str, Any]:
        if not content or not content.strip():
            return {
                "section_key": section_key,
                "status": "empty",
                "issues": [],
                "severity_counts": {"high": 0, "medium": 0, "low": 0},
                "counts": {
                    "dates_found": 0, "dates_unknown": 0,
                    "articles_found": 0, "articles_unknown": 0,
                    "laws_found": 0, "laws_unknown": 0,
                    "cases_found": 0, "cases_unknown": 0,
                    "abbrevs_found": 0, "abbrevs_unknown": 0,
                },
            }

        found_dates = _extract_dates_iso(content)
        found_articles = _extract_articles(content)
        found_laws = _extract_laws(content)
        found_cases = _extract_cases(content)
        found_abbrevs = _extract_abbrevs(content)

        issues: List[Dict[str, Any]] = []
        issues.extend(self._check_dates(content))
        issues.extend(self._check_articles(content))
        issues.extend(self._check_laws(content))
        issues.extend(self._check_cases(content))
        issues.extend(self._check_abbrevs(content))

        high = sum(1 for i in issues if i["severity"] == "high")
        medium = sum(1 for i in issues if i["severity"] == "medium")
        low = sum(1 for i in issues if i["severity"] == "low")

        if high == 0 and medium == 0:
            status = "clean" if low == 0 else "clean_low"
        else:
            status = "suspect"

        return {
            "section_key": section_key,
            "status": status,
            "issues": issues,
            "severity_counts": {"high": high, "medium": medium, "low": low},
            "counts": {
                "dates_found": len(found_dates),
                "dates_unknown": len(found_dates - self.allowed["dates_iso"]),
                "articles_found": len(found_articles),
                "articles_unknown": len(found_articles - self.allowed["articles"]),
                "laws_found": len(found_laws),
                "laws_unknown": len(found_laws - self.allowed["laws"]),
                "cases_found": len(found_cases),
                "cases_unknown": len(found_cases - self.allowed["cases"]),
                "abbrevs_found": len(found_abbrevs),
                "abbrevs_unknown": len(found_abbrevs - self.allowed["abbrevs"]),
            },
        }


# ═══════════════════════════════════════════════════════════════════════════
# TOP-LEVEL API
# ═══════════════════════════════════════════════════════════════════════════

def check_all_sections(
    sections: Dict[str, Any],
    citation_profile: Dict[str, Any],
    fact_profile: Dict[str, Any],
    verification_report: Dict[str, Any],
    extra_allowed_cases: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    checker = HallucinationChecker(
        citation_profile,
        fact_profile,
        verification_report,
        extra_allowed_cases=extra_allowed_cases,
    )

    per_section: Dict[str, Any] = {}
    total_issues = 0
    sev_totals = {"high": 0, "medium": 0, "low": 0}
    suspicious: List[str] = []

    for key, sec in sections.items():
        content = (sec or {}).get("content", "") if isinstance(sec, dict) else ""
        report = checker.check_section(key, content)
        per_section[key] = report

        total_issues += len(report["issues"])
        for s in ("high", "medium", "low"):
            sev_totals[s] += report["severity_counts"].get(s, 0)

        if report["status"] == "suspect":
            suspicious.append(key)

    if sev_totals["high"] > 0 or sev_totals["medium"] > 0:
        global_status = "suspect"
    elif sev_totals["low"] > 0:
        global_status = "clean_low"
    else:
        global_status = "clean"

    logger.info(
        f"[HALLUCINATION V1.5] Status={global_status}, "
        f"total_issues={total_issues} "
        f"(high={sev_totals['high']}, medium={sev_totals['medium']}, "
        f"low={sev_totals['low']}), "
        f"suspicious_sections={suspicious}"
    )

    return {
        "status": global_status,
        "total_issues": total_issues,
        "severity_totals": sev_totals,
        "per_section": per_section,
        "suspicious_sections": suspicious,
    }