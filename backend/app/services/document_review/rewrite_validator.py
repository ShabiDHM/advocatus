# FILE: backend/app/services/document_review/rewrite_validator.py
# PHOENIX PROTOCOL - REWRITE VALIDATOR V1.0
# V1.0: ANTI-HALLUCINATION për rishkrimin e dokumenteve.
#       - Ekstrakton nga teksti origjinal: data, shuma, nene, numra lënde, ligje.
#       - Ekstrakton të njëjtat nga teksti i rishkruar.
#       - Zbulon elementet E RE që nuk ekzistojnë në origjinal = halucinacion.
#       - Kthen raport të strukturuar me severity.

import re
import logging
from typing import Any, Dict, List, Set, Tuple

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# PATTERNS
# ═══════════════════════════════════════════════════════════════════════════

# Datat: 18.07.2024, 1.2.24, 18/07/2024
DATE_PATTERN = re.compile(
    r'\b(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{2,4})\b'
)

# Shumat: 200 euro, 1.795,39 €, 250 EUR
AMOUNT_PATTERN = re.compile(
    r'\b(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?)\s*(euro|EUR|€)\b',
    re.IGNORECASE,
)

# Nenet: Neni 78, Nenet 48 dhe 51, Nenin 427, Neni 96 par. 2
ARTICLE_PATTERN = re.compile(
    r'\b(?:Nen(?:i|it|in|et|eve|i\s+numri)?)\s+(\d{1,4}[a-z]?(?:\s+dhe\s+\d{1,4}[a-z]?)*)',
    re.IGNORECASE,
)

# Numrat e lëndëve: C.nr. 385/2024, PP.II.nr. 122/24F, P.nr. 883/24, PML.Nr. 122/2025, Rev.Nr. 252/2025
CASE_NUMBER_PATTERN = re.compile(
    r'\b([A-Z]{1,5}(?:\.\s*[IVX]+)?)\.?\s*[Nn]r\.?\s*(\d+[\w/\-.]*/\d{2,4}[A-Z]?)',
)

# Ligjet: 08/L-032, 06/L-074, 2004/32, Ligji Nr. 08/L-168
LAW_NUMBER_PATTERN = re.compile(
    r'\b(\d{2,4}/L-\d+|\d{4}/\d{1,3})\b'
)

# Fjalë të zakonshme që NUK janë shuma/nene
COMMON_FALSE_AMOUNTS: Set[str] = {
    "1", "2", "3", "4", "5", "6", "7", "8", "9", "10",
    "20", "30", "50", "100",
}


# ═══════════════════════════════════════════════════════════════════════════
# EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════

def _extract_dates(text: str) -> Set[str]:
    """Nxjerr data në format ISO normalizuar."""
    dates: Set[str] = set()
    for m in DATE_PATTERN.finditer(text):
        d, mo, y = m.group(1), m.group(2), m.group(3)
        # Normalizo: 1.2.24 → 01.02.2024
        try:
            d_norm = d.zfill(2)
            mo_norm = mo.zfill(2)
            if len(y) == 2:
                y_int = int(y)
                y_norm = f"20{y}" if y_int < 50 else f"19{y}"
            else:
                y_norm = y
            dates.add(f"{d_norm}.{mo_norm}.{y_norm}")
        except Exception:
            continue
    return dates


def _extract_amounts(text: str) -> Set[str]:
    """Nxjerr shumat në format 'X.XX euro' ose 'X euro'."""
    amounts: Set[str] = set()
    for m in AMOUNT_PATTERN.finditer(text):
        num_raw = m.group(1)
        # Normalizo: 1.795,39 → 1795.39 ; 200 → 200
        # Merr formën e thjeshtë numerike
        try:
            # Hiq pikën e mijërave, konverto presjen në pikë dhjetore
            if "," in num_raw and "." in num_raw:
                # 1.795,39 → 1795.39
                num_norm = num_raw.replace(".", "").replace(",", ".")
            elif "," in num_raw:
                # 200,50 → 200.50
                num_norm = num_raw.replace(",", ".")
            elif num_raw.count(".") == 1 and len(num_raw.split(".")[1]) <= 2:
                # 200.50 → 200.50 (dhjetore)
                num_norm = num_raw
            else:
                # 1.795 → 1795 (mijëra)
                num_norm = num_raw.replace(".", "")
            # Rrumbullako në 2 dhjetore
            num_float = float(num_norm)
            amounts.add(f"{num_float:.2f}")
        except Exception:
            amounts.add(num_raw)
    return amounts


def _extract_articles(text: str) -> Set[str]:
    """Nxjerr numrat e neneve (vetëm numrat, pa 'Neni')."""
    articles: Set[str] = set()
    for m in ARTICLE_PATTERN.finditer(text):
        nums_block = m.group(1)
        # Nda me 'dhe' ose ','
        parts = re.split(r'\s+dhe\s+|\s*,\s*|\s*;\s*', nums_block)
        for p in parts:
            p_clean = p.strip()
            if p_clean:
                articles.add(p_clean)
    return articles


def _extract_case_numbers(text: str) -> Set[str]:
    """Nxjerr numrat e lëndëve në format 'PREFIX.Nr.X/YEAR'."""
    cases: Set[str] = set()
    for m in CASE_NUMBER_PATTERN.finditer(text):
        prefix = m.group(1).upper().strip()
        num = m.group(2)
        # Normalizo prefixin: heq pikat
        prefix_clean = prefix.replace(".", "").replace(" ", "")
        cases.add(f"{prefix_clean}.Nr.{num}")
    return cases


def _extract_law_numbers(text: str) -> Set[str]:
    """Nxjerr numrat e ligjeve (08/L-032, 2004/32)."""
    laws: Set[str] = set()
    for m in LAW_NUMBER_PATTERN.finditer(text):
        laws.add(m.group(1))
    return laws


# ═══════════════════════════════════════════════════════════════════════════
# CONTEXT
# ═══════════════════════════════════════════════════════════════════════════

def _find_context(text: str, value: str, window: int = 60) -> str:
    """Gjen kontekstin rreth një vlere në tekst."""
    idx = text.find(value)
    if idx == -1:
        # Provo case-insensitive
        idx = text.lower().find(value.lower())
    if idx == -1:
        return ""
    start = max(0, idx - window)
    end = min(len(text), idx + len(value) + window)
    snippet = text[start:end].replace("\n", " ").strip()
    return f"...{snippet}..."


# ═══════════════════════════════════════════════════════════════════════════
# MAIN VALIDATE
# ═══════════════════════════════════════════════════════════════════════════

def validate_rewrite(
    original_text: str,
    rewritten_text: str,
) -> Dict[str, Any]:
    """
    Krahason origjinalin me të rishkruarin.
    Zbulon elementet E RE që nuk ekzistojnë në origjinal = halucinacion i mundshëm.

    Kthen:
      {
        "is_safe": bool,
        "severity": "clean" | "warning" | "danger",
        "total_issues": int,
        "issues": [ {type, value, context, severity}, ... ],
        "stats": {...},
        "high_count": int,
        "medium_count": int,
      }
    """
    if not original_text or not rewritten_text:
        return {
            "is_safe": False,
            "severity": "danger",
            "total_issues": 0,
            "issues": [],
            "stats": {},
            "high_count": 0,
            "medium_count": 0,
        }

    # ── EXTRACT NGA TË DYJA ──
    orig_dates = _extract_dates(original_text)
    new_dates = _extract_dates(rewritten_text)

    orig_amounts = _extract_amounts(original_text)
    new_amounts = _extract_amounts(rewritten_text)

    orig_articles = _extract_articles(original_text)
    new_articles = _extract_articles(rewritten_text)

    orig_cases = _extract_case_numbers(original_text)
    new_cases = _extract_case_numbers(rewritten_text)

    orig_laws = _extract_law_numbers(original_text)
    new_laws = _extract_law_numbers(rewritten_text)

    # ── DIFF (elemente të re) ──
    new_dates_only = new_dates - orig_dates
    new_amounts_only = new_amounts - orig_amounts
    new_articles_only = new_articles - orig_articles
    new_cases_only = new_cases - orig_cases
    new_laws_only = new_laws - orig_laws

    # ── FILTRO FALSE POSITIVES ──
    new_amounts_only = {
        a for a in new_amounts_only
        if float(a) not in {float(x) for x in COMMON_FALSE_AMOUNTS}
    }

    # ── NDËRTO LISTËN E ISSUE-AVE ──
    issues: List[Dict[str, Any]] = []

    # Datat e re — SEVERITY HIGH (kritike ligjore)
    for d in sorted(new_dates_only):
        issues.append({
            "type": "date",
            "type_label": "Datë e re",
            "value": d,
            "context": _find_context(rewritten_text, d.split(".")[0] + "." + d.split(".")[1]),
            "severity": "high",
        })

    # Numrat e lëndëve të re — SEVERITY HIGH
    for c in sorted(new_cases_only):
        issues.append({
            "type": "case_number",
            "type_label": "Numër lënde i ri",
            "value": c,
            "context": _find_context(rewritten_text, c),
            "severity": "high",
        })

    # Nenet e re — SEVERITY HIGH (kritike juridike)
    for a in sorted(new_articles_only):
        issues.append({
            "type": "article",
            "type_label": "Nen i ri",
            "value": f"Neni {a}",
            "context": _find_context(rewritten_text, f"Neni {a}"),
            "severity": "high",
        })

    # Ligjet e re — SEVERITY MEDIUM
    for l in sorted(new_laws_only):
        issues.append({
            "type": "law_number",
            "type_label": "Numër ligji i ri",
            "value": l,
            "context": _find_context(rewritten_text, l),
            "severity": "medium",
        })

    # Shumat e re — SEVERITY MEDIUM
    for am in sorted(new_amounts_only):
        issues.append({
            "type": "amount",
            "type_label": "Shumë e re",
            "value": f"{am} euro",
            "context": _find_context(rewritten_text, am.split(".")[0]),
            "severity": "medium",
        })

    # ── STATS ──
    high_count = sum(1 for i in issues if i["severity"] == "high")
    medium_count = sum(1 for i in issues if i["severity"] == "medium")
    total_issues = len(issues)

    # ── SEVERITY FINAL ──
    if high_count > 0:
        severity = "danger"
        is_safe = False
    elif medium_count > 0:
        severity = "warning"
        is_safe = False
    else:
        severity = "clean"
        is_safe = True

    stats = {
        "dates_original": len(orig_dates),
        "dates_rewritten": len(new_dates),
        "dates_new": len(new_dates_only),
        "amounts_original": len(orig_amounts),
        "amounts_rewritten": len(new_amounts),
        "amounts_new": len(new_amounts_only),
        "articles_original": len(orig_articles),
        "articles_rewritten": len(new_articles),
        "articles_new": len(new_articles_only),
        "cases_original": len(orig_cases),
        "cases_rewritten": len(new_cases),
        "cases_new": len(new_cases_only),
        "laws_original": len(orig_laws),
        "laws_rewritten": len(new_laws),
        "laws_new": len(new_laws_only),
    }

    logger.info(
        f"🔍 [REWRITE VALIDATOR] severity={severity}, "
        f"total_issues={total_issues} (high={high_count}, medium={medium_count}) | "
        f"dates +{len(new_dates_only)}, articles +{len(new_articles_only)}, "
        f"cases +{len(new_cases_only)}, amounts +{len(new_amounts_only)}, "
        f"laws +{len(new_laws_only)}"
    )

    return {
        "is_safe": is_safe,
        "severity": severity,
        "total_issues": total_issues,
        "issues": issues,
        "stats": stats,
        "high_count": high_count,
        "medium_count": medium_count,
    }