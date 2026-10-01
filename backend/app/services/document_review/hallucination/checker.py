# FILE: backend/app/services/document_review/hallucination/checker.py
# PHOENIX PROTOCOL - HALLUCINATION CHECKER V1.28
# V1.28: ROBUSTNESS + DRY + PERF —
#        (1) DRY: shtuar VALID_STANDARD_ABBREVS si konstante moduli.
#            Ishte e përsëritur identikisht në _check_abbreviation_replacement
#            dhe _check_abbrev_multiple_laws.
#        (2) PERF: check_section thirrej extract_* 2× (një herë direkt për
#            counts, një herë brenda _check_*). Tani thirret një herë dhe
#            rezultati kalohet si parametër optional `found`. Përfitim:
#            ~2× më pak regex për raporte të mëdha.
#        (3) ROBUSTNESS: `i["severity"]` → `i.get("severity")` në logger-a
#            dhe count-e. Parandalon KeyError nëse ndonjë shtesë e ardhshme
#            shton issue pa fushën `severity`.
#
# V1.27: HALLUCINATION MODE + FP WHITELIST —
#        (1) HALLUCINATION_MODE (strict/balanced/lenient) nga env/config.
#            Default: balanced (vetëm HIGH bllokon).
#        (2) Integrim i is_whitelisted_fp() para shtimit të issue.
#        (3) Audit logging i zgjeruar për çdo block.
# V1.25: DYNAMIC KNOWN LAWS + DB LAWS.
# V1.24: ROLE-AWARE (drafting_quality).
# V1.23: ROLE-AWARE (errors_corrections).
# V1.22: GLOBALLY ALLOWED LAWS.

import os
import logging
from typing import Any, Dict, List, Optional, Set

from .constants import (
    AMBIGUOUS_LAW_ABBREVS,
    ROLE_AWARE_SECTIONS,
)
from .regexes import (
    ABBREV_REPLACEMENT_RE,
    ABBREV_WITH_LAW_NUMBER_RE,
    LAW_NAME_WITH_NUMBER_RE,
)
from .normalize import (
    NORMALIZED_KNOWN_LAW_MAP,
    get_globally_allowed_laws,
    is_valid_law_output,
    is_whitelisted_fp,
    normalize_law_name,
    normalize_law_num,
    normalize_precedent_case,
    safe_normalize_law,
)
from .extract import (
    extract_abbrevs,
    extract_articles,
    extract_cases,
    extract_dates_iso,
    extract_laws,
    find_snippet,
    has_real_article_context,
    has_real_citation_context,
    iso_to_albanian_date,
)
from .successors import collect_successor_laws

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# V1.28: STANDARD ABBREVIATIONS (DRY — ishin dublikatë në 2 metoda)
# ═══════════════════════════════════════════════════════════════════════════

VALID_STANDARD_ABBREVS: Set[str] = {
    "KPRK", "KPPRK", "LPK", "LMD", "LMDHF",
    "LFK", "LSHT", "PSRK", "KRK", "LPTS",
}


# ═══════════════════════════════════════════════════════════════════════════
# V1.27: HALLUCINATION MODE
# ═══════════════════════════════════════════════════════════════════════════

def _get_hallucination_mode() -> str:
    """
    Lexon HALLUCINATION_MODE nga settings ose env.
    Default: "balanced".
    """
    try:
        from app.core.config import settings
        mode = getattr(settings, "HALLUCINATION_MODE", None)
        if mode:
            return str(mode).lower().strip()
    except Exception:
        pass

    mode = os.getenv("HALLUCINATION_MODE", "balanced")
    return mode.lower().strip()


HALLUCINATION_MODE = _get_hallucination_mode()


# ═══════════════════════════════════════════════════════════════════════════
# WHITELIST FILTER
# ═══════════════════════════════════════════════════════════════════════════

def _filter_whitelisted(
    kind: str,
    values: Set[str],
    content: str,
) -> Set[str]:
    """
    V1.27: Heq vlerat që përputhen me whitelist (false-positive të njohura).
    """
    if not values:
        return values
    kept: Set[str] = set()
    removed: List[str] = []
    for v in values:
        if is_whitelisted_fp(kind, v, content):
            removed.append(v)
        else:
            kept.add(v)
    if removed:
        logger.info(
            f"[HALLUCINATION V1.28] Whitelist filtered ({kind}): {removed[:10]}"
        )
    return kept


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
        extra_allowed_dates: Optional[Set[str]] = None,
        extra_allowed_articles: Optional[Set[str]] = None,
        extra_allowed_laws: Optional[Set[str]] = None,
    ):
        self.allowed = self._build_allowed(
            citation_profile,
            fact_profile,
            verification_report,
            extra_allowed_cases=extra_allowed_cases,
            extra_allowed_dates=extra_allowed_dates,
            extra_allowed_articles=extra_allowed_articles,
            extra_allowed_laws=extra_allowed_laws,
        )
        logger.info(
            f"[HALLUCINATION V1.28] Mode={HALLUCINATION_MODE}, "
            f"Allowed values: "
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
        extra_allowed_dates: Optional[Set[str]] = None,
        extra_allowed_articles: Optional[Set[str]] = None,
        extra_allowed_laws: Optional[Set[str]] = None,
    ) -> Dict[str, Set[str]]:
        dates_iso: Set[str] = set()
        for d in fact_profile.get("dates", []) or []:
            if d.get("iso"):
                dates_iso.add(d["iso"])

        if extra_allowed_dates:
            for d in extra_allowed_dates:
                if d:
                    dates_iso.add(str(d))

        laws: Set[str] = set()

        base_laws: Set[str] = set()
        for l in citation_profile.get("laws_by_number", []) or []:
            if l.get("number"):
                n = safe_normalize_law(str(l["number"]))
                if n:
                    base_laws.add(n)
                    laws.add(n)

        for l in verification_report.get("laws_by_number", []) or []:
            if l.get("number"):
                n = safe_normalize_law(str(l["number"]))
                if n:
                    laws.add(n)

        successors = collect_successor_laws(verification_report)
        laws.update(successors)

        globally_allowed = get_globally_allowed_laws()
        new_globals = globally_allowed - laws
        laws.update(globally_allowed)
        if new_globals:
            logger.info(
                f"[HALLUCINATION V1.28] Globally allowed laws (JSON): "
                f"+{len(new_globals)} → {sorted(new_globals)}"
            )

        if extra_allowed_laws:
            new_db = {str(x) for x in extra_allowed_laws if x} - laws
            laws.update(extra_allowed_laws)
            if new_db:
                logger.info(
                    f"[HALLUCINATION V1.28] DB allowed laws: "
                    f"+{len(new_db)} → {sorted(new_db)}"
                )

        logger.info(
            f"[HALLUCINATION V1.28] Laws: base={len(base_laws)}, "
            f"successors={len(successors)}, "
            f"global={len(globally_allowed)}, total={len(laws)}"
        )

        articles: Set[str] = set()
        for a in citation_profile.get("articles", []) or []:
            if a.get("number"):
                articles.add(a["number"])

        if extra_allowed_articles:
            before = len(articles)
            for a in extra_allowed_articles:
                if a:
                    articles.add(str(a).strip())
            added = len(articles) - before
            if added > 0:
                logger.info(
                    f"[HALLUCINATION V1.28] Extra allowed articles "
                    f"(from precedents): +{added}"
                )

        cases: Set[str] = set()
        for c in citation_profile.get("case_numbers", []) or []:
            # V1.28: .get() një herë, jo dy herë
            cn = c.get("case_number")
            if cn:
                from ..helpers import normalize_case_number
                n = normalize_case_number(cn) or cn
                cases.add(n)

        if extra_allowed_cases:
            before = len(cases)
            for cn in extra_allowed_cases:
                if not cn:
                    continue
                norm = normalize_precedent_case(cn)
                if norm:
                    cases.add(norm)
                cases.add(cn.upper().strip())
            added = len(cases) - before
            if added > 0:
                logger.info(
                    f"[HALLUCINATION V1.28] Extra allowed cases "
                    f"(from precedents): +{added}"
                )

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

    # ────────────────────────────────────────────────────────────────────
    # META-LAYER CHECKS
    # ────────────────────────────────────────────────────────────────────

    def _check_law_name_number_consistency(
        self, content: str,
    ) -> List[Dict[str, Any]]:
        issues: List[Dict[str, Any]] = []
        if not content:
            return issues

        for m in LAW_NAME_WITH_NUMBER_RE.finditer(content):
            raw_name = m.group(1).strip()
            raw_num = m.group(2).strip()

            name_norm = normalize_law_name(raw_name)
            num_norm = normalize_law_num(raw_num)

            matched_key = None
            for known_name in NORMALIZED_KNOWN_LAW_MAP:
                if known_name in name_norm or name_norm in known_name:
                    matched_key = known_name
                    break

            if not matched_key:
                continue

            valid_nums = {
                normalize_law_num(v)
                for v in NORMALIZED_KNOWN_LAW_MAP[matched_key]
            }

            if num_norm not in valid_nums:
                snippet = find_snippet(content, raw_num, window=80)
                issues.append({
                    "type": "law_name_number_mismatch",
                    "value": f"{raw_name} (Nr. {raw_num})",
                    "severity": "medium",
                    "message": (
                        f"Numri '{raw_num}' nuk i përket '{raw_name}'. "
                        f"Numrat e pranuar: {sorted(valid_nums)}."
                    ),
                    "snippet": snippet,
                })

        return issues

    def _check_abbreviation_replacement(
        self, content: str,
    ) -> List[Dict[str, Any]]:
        issues: List[Dict[str, Any]] = []
        if not content:
            return issues

        allowed_abbrevs = self.allowed.get("abbrevs", set())
        # V1.28: përdor konstante moduli
        valid_std = VALID_STANDARD_ABBREVS

        for m in ABBREV_REPLACEMENT_RE.finditer(content):
            groups = m.groups()
            from_abbr = to_abbr = None
            for i in range(0, len(groups), 2):
                if i + 1 < len(groups) and groups[i] and groups[i + 1]:
                    from_abbr = groups[i].upper().strip()
                    to_abbr = groups[i + 1].upper().strip()
                    break

            if not from_abbr or not to_abbr:
                continue
            if from_abbr == to_abbr:
                continue

            from_is_valid = (
                from_abbr in valid_std or from_abbr in allowed_abbrevs
            )
            to_is_valid = to_abbr in valid_std

            if from_is_valid and not to_is_valid:
                snippet = find_snippet(content, m.group(0), window=80)
                issues.append({
                    "type": "invalid_abbrev_replacement",
                    "value": f"{from_abbr} → {to_abbr}",
                    "severity": "high",
                    "message": (
                        f"Rekomandim i gabuar: '{from_abbr}' është akronim "
                        f"standard i vlefshëm, ndërsa '{to_abbr}' nuk është. "
                        f"MOS e zëvendëso."
                    ),
                    "snippet": snippet,
                })

        return issues

    def _check_abbrev_multiple_laws(
        self, content: str,
    ) -> List[Dict[str, Any]]:
        issues: List[Dict[str, Any]] = []
        if not content:
            return issues

        allowed_abbrevs = self.allowed.get("abbrevs", set())
        # V1.28: përdor konstante moduli
        known_abbrevs = VALID_STANDARD_ABBREVS | set(allowed_abbrevs)

        abbr_to_nums: Dict[str, Set[str]] = {}
        for m in ABBREV_WITH_LAW_NUMBER_RE.finditer(content):
            abbr = m.group(1).upper()
            num = normalize_law_num(m.group(2))
            if abbr not in known_abbrevs:
                continue
            abbr_to_nums.setdefault(abbr, set()).add(num)

        for abbr, nums in abbr_to_nums.items():
            if len(nums) >= 2:
                issues.append({
                    "type": "abbrev_multiple_laws",
                    "value": f"{abbr} ↔ {sorted(nums)}",
                    "severity": "medium",
                    "message": (
                        f"Akronimi '{abbr}' lidhet me {len(nums)} numra të "
                        f"ndryshëm ligjesh: {sorted(nums)}. "
                        f"Kontrollo konsistencën."
                    ),
                    "snippet": find_snippet(content, abbr, window=100),
                })

        return issues

    # ────────────────────────────────────────────────────────────────────
    # STANDARD CHECKS (V1.28: pranojnë `found` për të shmangur ekstraksion 2×)
    # ────────────────────────────────────────────────────────────────────

    def _check_dates(
        self, content: str, found: Optional[Set[str]] = None,
    ) -> List[Dict[str, Any]]:
        if found is None:
            found = extract_dates_iso(content)
        unknown = found - self.allowed["dates_iso"]
        unknown = _filter_whitelisted("date", unknown, content)
        issues = []
        for d in sorted(unknown):
            if not has_real_citation_context(content, d, prefixes=("",)):
                logger.info(
                    f"[HALLUCINATION V1.28] Skip date '{d}' — "
                    f"shfaqet vetëm në kontekst sugjerimi."
                )
                continue

            display_date = iso_to_albanian_date(d)
            issues.append({
                "type": "date",
                "value": display_date,
                "severity": "high",
                "message": f"Data '{display_date}' nuk shfaqet në faktet e dokumentit.",
                "snippet": find_snippet(content, d),
            })
        return issues

    def _check_articles(
        self, content: str, found: Optional[Set[str]] = None,
    ) -> List[Dict[str, Any]]:
        if found is None:
            found = extract_articles(content)
        unknown = found - self.allowed["articles"]
        unknown = _filter_whitelisted("article", unknown, content)
        issues = []
        for a in sorted(unknown):
            if not has_real_article_context(content, a):
                logger.info(
                    f"[HALLUCINATION V1.28] Skip article '{a}' — "
                    f"shfaqet vetëm në kontekst sugjerimi."
                )
                continue

            issues.append({
                "type": "article", "value": f"Neni {a}", "severity": "medium",
                "message": f"Neni {a} nuk u gjet ne citimet e dokumentit.",
                "snippet": (
                    find_snippet(content, f"Neni {a}")
                    or find_snippet(content, f"Nenit {a}")
                ),
            })
        return issues

    def _check_laws(
        self, content: str, found: Optional[Set[str]] = None,
    ) -> List[Dict[str, Any]]:
        if found is None:
            found = extract_laws(content)
        unknown = found - self.allowed["laws"]
        unknown = _filter_whitelisted("law", unknown, content)
        issues = []
        for l in sorted(unknown):
            if not has_real_citation_context(content, l, prefixes=("",)):
                logger.info(
                    f"[HALLUCINATION V1.28] Skip law '{l}' — "
                    f"shfaqet vetëm në kontekst sugjerimi."
                )
                continue

            issues.append({
                "type": "law", "value": l, "severity": "medium",
                "message": f"Ligji '{l}' nuk u gjet ne citimet e dokumentit.",
                "snippet": find_snippet(content, l),
            })
        return issues

    def _check_cases(
        self, content: str, found: Optional[Set[str]] = None,
    ) -> List[Dict[str, Any]]:
        if found is None:
            found = extract_cases(content)
        unknown = found - self.allowed["cases"]
        unknown = _filter_whitelisted("case", unknown, content)
        issues = []
        for c in sorted(unknown):
            if not has_real_citation_context(content, c, prefixes=("",)):
                logger.info(
                    f"[HALLUCINATION V1.28] Skip case '{c}' — "
                    f"shfaqet vetëm në kontekst sugjerimi."
                )
                continue

            issues.append({
                "type": "case_number", "value": c, "severity": "high",
                "message": f"Numri i lendes '{c}' nuk u gjet ne dokument.",
                "snippet": find_snippet(content, c),
            })
        return issues

    def _check_abbrevs(
        self, content: str, found: Optional[Set[str]] = None,
    ) -> List[Dict[str, Any]]:
        if found is None:
            found = extract_abbrevs(content)
        unknown = found - self.allowed["abbrevs"]
        unknown = _filter_whitelisted("abbreviation", unknown, content)
        issues = []
        for a in sorted(unknown):
            if not has_real_citation_context(content, a, prefixes=("",)):
                logger.info(
                    f"[HALLUCINATION V1.28] Skip abbrev '{a}' — "
                    f"shfaqet vetëm në kontekst sugjerimi."
                )
                continue

            if a in AMBIGUOUS_LAW_ABBREVS:
                severity = "medium"
                msg = (
                    f"Akronimi '{a}' është i njohur si ambigu / jo-standard. "
                    f"Përdor formën e plotë të ligjit ose akronimin standard."
                )
            else:
                severity = "low"
                msg = f"Akronimi '{a}' nuk u gjet ne citimet e dokumentit."

            issues.append({
                "type": "abbreviation", "value": a, "severity": severity,
                "message": msg,
                "snippet": find_snippet(content, a),
            })
        return issues

    # ────────────────────────────────────────────────────────────────────
    # MAIN ENTRY PER SECTION
    # ────────────────────────────────────────────────────────────────────

    def check_section(
        self, section_key: str, content: str,
    ) -> Dict[str, Any]:
        if not content or not content.strip():
            return {
                "section_key": section_key, "status": "empty", "issues": [],
                "severity_counts": {"high": 0, "medium": 0, "low": 0},
                "counts": {
                    "dates_found": 0, "dates_unknown": 0,
                    "articles_found": 0, "articles_unknown": 0,
                    "laws_found": 0, "laws_unknown": 0,
                    "cases_found": 0, "cases_unknown": 0,
                    "abbrevs_found": 0, "abbrevs_unknown": 0,
                },
            }

        # V1.28: ekstrakto NJË herë, kalo rezultatet te _check_*
        found_dates = extract_dates_iso(content)
        found_articles = extract_articles(content)
        found_laws = extract_laws(content)
        found_cases = extract_cases(content)
        found_abbrevs = extract_abbrevs(content)

        issues: List[Dict[str, Any]] = []
        issues.extend(self._check_dates(content, found_dates))
        issues.extend(self._check_articles(content, found_articles))
        issues.extend(self._check_laws(content, found_laws))
        issues.extend(self._check_cases(content, found_cases))
        issues.extend(self._check_abbrevs(content, found_abbrevs))
        issues.extend(self._check_law_name_number_consistency(content))
        issues.extend(self._check_abbreviation_replacement(content))
        issues.extend(self._check_abbrev_multiple_laws(content))

        # V1.28: .get() për robustness
        high = sum(1 for i in issues if i.get("severity") == "high")
        medium = sum(1 for i in issues if i.get("severity") == "medium")
        low = sum(1 for i in issues if i.get("severity") == "low")

        # ═══════════════════════════════════════════════════════════════════
        # V1.27: MODE-BASED + ROLE-AWARE
        # ═══════════════════════════════════════════════════════════════════
        if HALLUCINATION_MODE == "lenient":
            effective_status = "clean_low" if (high + medium + low) > 0 else "clean"
        elif HALLUCINATION_MODE == "strict":
            if section_key in ROLE_AWARE_SECTIONS:
                if high > 0:
                    effective_status = "suspect"
                else:
                    effective_status = "clean_low" if (medium + low) > 0 else "clean"
            else:
                if high > 0 or medium > 0:
                    effective_status = "suspect"
                elif low > 0:
                    effective_status = "clean_low"
                else:
                    effective_status = "clean"
        else:  # balanced (default)
            if high > 0:
                effective_status = "suspect"
            elif (medium + low) > 0:
                effective_status = "clean_low"
            else:
                effective_status = "clean"

        if effective_status == "suspect":
            logger.warning(
                f"🛡️ [HALLUCINATION V1.28 AUDIT] section={section_key} "
                f"BLOCKED — high={high}, medium={medium}, low={low}, "
                f"mode={HALLUCINATION_MODE}, role_aware="
                f"{section_key in ROLE_AWARE_SECTIONS}"
            )
            # V1.28: .get() për robustness
            for i in issues[:5]:
                logger.warning(
                    f"   → {i.get('severity')}: {i.get('type')} = {i.get('value')}"
                )

        return {
            "section_key": section_key,
            "status": effective_status,
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
    extra_allowed_dates: Optional[Set[str]] = None,
    extra_allowed_articles: Optional[Set[str]] = None,
    extra_allowed_laws: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    """
    V1.28: Kontrollon të gjitha section-t. Mode-based (strict/balanced/lenient),
    role-aware, whitelist-filter, DB laws, successor laws, globally allowed.
    """
    checker = HallucinationChecker(
        citation_profile, fact_profile, verification_report,
        extra_allowed_cases=extra_allowed_cases,
        extra_allowed_dates=extra_allowed_dates,
        extra_allowed_articles=extra_allowed_articles,
        extra_allowed_laws=extra_allowed_laws,
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

        for issue in report["issues"]:
            sev = issue.get("severity", "?")
            itype = issue.get("type", "?")
            ival = issue.get("value", "?")
            imsg = issue.get("message", "")
            isnip = (issue.get("snippet", "") or "")[:160]
            logger.info(
                f"[HALLUCINATION V1.28] 📌 section={key} severity={sev} "
                f"type={itype} value='{ival}'"
            )
            logger.info(f"[HALLUCINATION V1.28]    message: {imsg}")
            if isnip:
                logger.info(f"[HALLUCINATION V1.28]    snippet: {isnip}")

        if report["status"] == "suspect":
            suspicious.append(key)

    if sev_totals["high"] > 0 or sev_totals["medium"] > 0:
        global_status = "suspect"
    elif sev_totals["low"] > 0:
        global_status = "clean_low"
    else:
        global_status = "clean"

    if global_status == "suspect" and not suspicious:
        global_status = "clean_low"
        logger.info(
            "[HALLUCINATION V1.28] Global status downgraded to 'clean_low' "
            "— medium/low vetëm në role-aware sections."
        )

    logger.info(
        f"[HALLUCINATION V1.28] Status={global_status}, "
        f"mode={HALLUCINATION_MODE}, "
        f"total_issues={total_issues} "
        f"(high={sev_totals['high']}, medium={sev_totals['medium']}, "
        f"low={sev_totals['low']}), "
        f"suspicious_sections={suspicious}"
    )

    return {
        "status": global_status,
        "mode": HALLUCINATION_MODE,
        "total_issues": total_issues,
        "severity_totals": sev_totals,
        "per_section": per_section,
        "suspicious_sections": suspicious,
    }