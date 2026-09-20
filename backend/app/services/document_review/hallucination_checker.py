# FILE: backend/app/services/document_review/hallucination_checker.py
# PHOENIX PROTOCOL - HALLUCINATION CHECKER V1.2
# V1.2: FIX — _extract_cases rstrip(".,;:") mbi num_part. CASE_NUMBER_PATTERN
#       perfshin '.' ne karakteret e lejuara, duke gelltitur piken e fjalisë:
#       "P.nr.123/2024." -> num_part="123/2024." -> false-positive 'suspect'.
# V1.1: FIX — _build_allowed normalizon numrat e lendeve (symetrik me
#       _extract_cases).
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
# EXTRACTORS (nga teksti i LLM)
# ═══════════════════════════════════════════════════════════════════════════

def _extract_dates_iso(text: str) -> Set[str]:
    """Nxjerr datat (numerike + shqip) ne format ISO."""
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
    """Nxjerr numrat e neneve (pa paragraph)."""
    found: Set[str] = set()
    if not text:
        return found

    for m in ARTICLE_PATTERN.finditer(text):
        art_raw = m.group(1)
        par_raw = m.group(2)
        art, _ = _normalize_article_number(art_raw, par_raw)
        found.add(art)

    return found


def _extract_laws(text: str) -> Set[str]:
    """Nxjerr numrat e ligjeve (normalizuar)."""
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
    """
    Nxjerr numrat e lendeve (normalizuar).

    V1.2: rstrip(".,;:") per te hequr piken e fjalisë qe CASE_NUMBER_PATTERN
    e gelltit per shkak te '.' brenda karaktereve te lejuara.
    """
    found: Set[str] = set()
    if not text:
        return found

    for m in CASE_NUMBER_PATTERN.finditer(text):
        prefix = m.group(1).upper()
        # V1.2: heq pikat/presjet ne fund
        num_part = m.group(2).rstrip(".,;:")
        if not num_part:
            continue
        raw = f"{prefix}.nr.{num_part}"
        n = normalize_case_number(raw)
        if n:
            found.add(n)

    return found


def _extract_abbrevs(text: str) -> Set[str]:
    """Nxjerr akronimet e vlefshme ligjore."""
    found: Set[str] = set()
    if not text:
        return found

    for m in ABBREV_PATTERN.finditer(text):
        abbr = m.group(1)
        if is_valid_law_abbrev(abbr):
            found.add(abbr.upper())

    return found


# ═══════════════════════════════════════════════════════════════════════════
# CONTEXT SNIPPET (per debugging)
# ═══════════════════════════════════════════════════════════════════════════

def _find_snippet(text: str, value: str, window: int = 80) -> str:
    """Gjen nje fragment teksti rreth vleres se dhene."""
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
    """
    Kontrollon output-in e LLM kunder listes se vlerave te lejuara.
    Ndertohet nje here, perdoret per shume seksione.
    """

    def __init__(
        self,
        citation_profile: Dict[str, Any],
        fact_profile: Dict[str, Any],
        verification_report: Dict[str, Any],
    ):
        self.allowed = self._build_allowed(
            citation_profile, fact_profile, verification_report
        )
        logger.info(
            f"[HALLUCINATION V1.2] Allowed values: "
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
    ) -> Dict[str, Set[str]]:
        """
        Mbledh vlerat e lejuara nga profilet.
        Normalizon te gjitha vlerat ne te njejten menyre si _extract_*(),
        per te shmangur false-positives nga mospershtatje formati.
        """
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

        # V1.1: normalizuar (symetrik me _extract_cases)
        cases: Set[str] = set()
        for c in citation_profile.get("case_numbers", []) or []:
            if c.get("case_number"):
                n = normalize_case_number(c["case_number"]) or c["case_number"]
                cases.add(n)

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

    # ─────────────────────────────────────────────────────────────────────
    # CHECKS PER TIP
    # ─────────────────────────────────────────────────────────────────────

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

    # ─────────────────────────────────────────────────────────────────────
    # CHECK SEKTION
    # ─────────────────────────────────────────────────────────────────────

    def check_section(
        self,
        section_key: str,
        content: str,
    ) -> Dict[str, Any]:
        """
        Kontrollon nje seksion. Kthen raport te strukturuar.
        """
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
) -> Dict[str, Any]:
    """
    Kontrollon te gjitha seksionet e nje raporti.
    """
    checker = HallucinationChecker(
        citation_profile, fact_profile, verification_report
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
        f"[HALLUCINATION V1.2] Status={global_status}, "
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