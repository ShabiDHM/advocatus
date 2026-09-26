# FILE: backend/app/services/rag/document_review_post_processor.py
# PHOENIX PROTOCOL - DOCUMENT REVIEW POST-PROCESSOR V1.1
# V1.1: (1) FIX — whitelist regex pranon format "2004/32" (4-shifror),
#           përveç "08/L-185".
#       (2) FIX — _find_fake_precedents flagon VETËM kur numri i lëndës
#           shfaqet në kontekst "precedent/referuar/sipas/bazuar/ngjashëm",
#           jo kudo në output (eliminon false-positive kur LLM citon lëndën
#           aktuale).
# V1.0: Krijim fillestar.

import re
import logging
from typing import Dict, Any, List, Set, Tuple

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# REGEX
# ═══════════════════════════════════════════════════════════════════════════

_LAW_NUMBER_OUTPUT_RE = re.compile(
    r'\bLigj(?:it|i|ji|in)?\s+(?:Nr\.?\s*)?(\d{2}\s*\/\s*[A-Za-z]\s*[-–]?\s*\d{2,4})\b',
    re.IGNORECASE | re.UNICODE
)

_ARTICLE_OUTPUT_RE = re.compile(
    r'\bNen(?:i|it|in|ët)\s+(\d+(?:[\.\/]\d+)*)',
    re.IGNORECASE | re.UNICODE
)

_BAD_ARTICLE_FORMAT_RE = re.compile(
    r'\bNen(?:i|it|in|ët)\s+(\d+)\.(\d+)\b',
    re.IGNORECASE | re.UNICODE
)

_LAW_ABBREV_OUTPUT_RE = re.compile(
    r'\b(KPPRK|KPRK|KPK|LPK|LMDHF|LMD|LFK|LSHT|LPP|KDMM|KDPM|LPTS|PSRK)\b',
    re.IGNORECASE
)

_CASE_NUMBER_RE = re.compile(
    r'\b(?:PML|Rev|KMLP|ANR|A\.NR|PZR|PA1|PKR|C|P|CA|PN|KP|KE)\.?\s*(?:[Nn]r\.?)?\s*\d+[/\-\d]*\b',
    re.IGNORECASE
)

# V1.1: Regex i zgjeruar për whitelist — pranon "XX/L-NNN" dhe "YYYY/NN"
_LAW_NUMBER_WHITELIST_RE = re.compile(r'^\d{2,4}(?:/[A-Z])?-?\d+$')

# V1.1: Fjalë që tregojnë se numri i lëndës trajtohet si PRECEDENT
_PRECEDENT_CLAIM_WORDS = [
    "precedent", "precedenti", "precedentë",
    "referuar", "referohet", "sipas",
    "bazuar", "ngjashëm", "ngjashem", "analog",
]


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _normalize_law_number(raw: str) -> str:
    return re.sub(r'\s+', '', raw).upper().replace('–', '-')


def _extract_case_numbers(text: str) -> Set[str]:
    found = _CASE_NUMBER_RE.findall(text)
    return set(n.upper().replace(' ', '') for n in found)


# ═══════════════════════════════════════════════════════════════════════════
# DETECTORS
# ═══════════════════════════════════════════════════════════════════════════

def _find_wrong_law_numbers(output_text: str, verified_citations: Dict[str, Any]) -> List[str]:
    whitelist_numbers = set(verified_citations.get("laws", []))
    # V1.1: Regex i zgjeruar — pranon "2004/32" dhe "08/L-185"
    whitelist_numbers = {n for n in whitelist_numbers if _LAW_NUMBER_WHITELIST_RE.match(n)}

    found = _LAW_NUMBER_OUTPUT_RE.findall(output_text)
    normalized_found = set(_normalize_law_number(f) for f in found)

    if not whitelist_numbers:
        return sorted(normalized_found)

    wrong = [n for n in normalized_found if n not in whitelist_numbers]
    return sorted(wrong)


def _find_missing_articles(output_text: str, verified_citations: Dict[str, Any]) -> List[str]:
    doc_articles = set(str(a["number"]) for a in verified_citations.get("articles", []))

    found = _ARTICLE_OUTPUT_RE.findall(output_text)
    normalized_found = set(found)

    if not doc_articles:
        return sorted(normalized_found)

    missing = [a for a in normalized_found if a not in doc_articles]
    return sorted(missing)


def _find_bad_article_format(output_text: str) -> List[Tuple[str, str]]:
    matches = _BAD_ARTICLE_FORMAT_RE.findall(output_text)
    return list(set(matches))


def _find_abbreviation_mismatches(output_text: str, verified_citations: Dict[str, Any]) -> List[str]:
    doc_text_citations = verified_citations.get("laws", [])
    doc_abbrevs = set()
    for law in doc_text_citations:
        if re.match(r'^[A-Z]{2,6}$', law):
            doc_abbrevs.add(law.upper())

    found_abbrevs = set(m.upper() for m in _LAW_ABBREV_OUTPUT_RE.findall(output_text))

    if not doc_abbrevs:
        return sorted(found_abbrevs)

    extra = [a for a in found_abbrevs if a not in doc_abbrevs]
    return sorted(extra)


def _find_fake_precedents(output_text: str, doc_case_numbers: Set[str]) -> List[str]:
    """
    V1.1: Flagon numrin e lëndës vetëm nëse shfaqet në kontekst 'precedent'
    (brenda 250 chars pas fjalës trigger). Jo kudo në output.
    """
    if not doc_case_numbers:
        return []

    output_lower = output_text.lower()
    output_nospace = output_lower.replace(' ', '')

    fake: List[str] = []
    for cn in doc_case_numbers:
        cn_clean = cn.replace(' ', '').lower()
        if cn_clean not in output_nospace:
            continue

        near_precedent = False
        for word in _PRECEDENT_CLAIM_WORDS:
            idx = output_lower.find(word)
            while idx != -1:
                window = output_lower[idx:idx + 250].replace(' ', '')
                if cn_clean in window:
                    near_precedent = True
                    break
                idx = output_lower.find(word, idx + 1)
            if near_precedent:
                break

        if near_precedent:
            fake.append(cn)

    return sorted(set(fake))


# ═══════════════════════════════════════════════════════════════════════════
# PUBLIC
# ═══════════════════════════════════════════════════════════════════════════

def build_review_correction_section(
    output_text: str,
    verified_citations: Dict[str, Any],
    doc_text: str,
    section_key: str = "",
) -> str:
    wrong_laws = _find_wrong_law_numbers(output_text, verified_citations)
    missing_articles = _find_missing_articles(output_text, verified_citations)
    bad_formats = _find_bad_article_format(output_text)
    abbrev_mismatches = _find_abbreviation_mismatches(output_text, verified_citations)

    fake_precedents: List[str] = []
    if section_key == "supreme_court_precedents":
        doc_cases = _extract_case_numbers(doc_text[:5000])
        fake_precedents = _find_fake_precedents(output_text, doc_cases)

    has_any_issue = (
        wrong_laws or missing_articles or bad_formats
        or abbrev_mismatches or fake_precedents
    )

    if not has_any_issue:
        return ""

    parts: List[str] = []
    parts.append("\n\n---\n")
    parts.append("## ⚠️ KORRIGJIME DHE VËREJTJE AUTOMATIKE\n\n")
    parts.append("*Ky seksion kontrollohet automatikisht — bazuar në citimet që shfaqen në dokumentin origjinal.*\n")

    if wrong_laws:
        parts.append("\n### 🔴 Ligje që nuk shfaqen në dokument\n\n")
        for law in wrong_laws:
            parts.append(f"- ❌ **Ligji Nr. {law}** — nuk citohet në këtë dokument.\n")
        whitelist = [n for n in verified_citations.get("laws", []) if _LAW_NUMBER_WHITELIST_RE.match(n)]
        if whitelist:
            parts.append("\n✅ **Ligji/ligjet që shfaqen vërtet në dokument:**\n\n")
            for n in whitelist:
                parts.append(f"- **Ligji Nr. {n}**\n")

    if abbrev_mismatches:
        parts.append("\n### 🔴 Kode ligjesh që nuk shfaqen në dokument\n\n")
        parts.append("Përgjigja citon kode ligjesh që **nuk shfaqen në dokumentin origjinal**:\n\n")
        for abbr in abbrev_mismatches:
            parts.append(f"- ❌ **{abbr}** — nuk citohet në këtë dokument.\n")

    if missing_articles:
        parts.append("\n### 🔴 Nene që nuk shfaqen në dokument\n\n")
        for art in missing_articles[:10]:
            parts.append(f"- ❌ **Neni {art}** — nuk citohet në këtë dokument.\n")
        if len(missing_articles) > 10:
            parts.append(f"- ... dhe {len(missing_articles) - 10} nene të tjera.\n")

        doc_arts = verified_citations.get("articles", [])
        if doc_arts:
            parts.append("\n✅ **Nenet që shfaqen vërtet në dokument:**\n\n")
            for a in doc_arts[:10]:
                par = f", par. {a['paragraph']}" if a.get("paragraph") else ""
                parts.append(f"- **Neni {a['number']}{par}**\n")

    if bad_formats:
        parts.append("\n### 🟡 Format i gabuar i citimit\n\n")
        parts.append("Format i saktë është **\"Neni X, par. Y\"** — jo **\"Neni X.Y\"**:\n\n")
        for major, minor in bad_formats[:10]:
            parts.append(f"- ⚠️ `Neni {major}.{minor}` → **Neni {major}, par. {minor}**\n")

    if fake_precedents:
        parts.append("\n### 🔴 Numra lënde të trajtuar gabimisht si precedentë\n\n")
        parts.append("Këta numra **i përkasin dokumentit origjinal** — nuk janë precedentë:\n\n")
        for cn in fake_precedents:
            parts.append(f"- ❌ **{cn}** — ky është numri i lëndës së dokumentit, jo precedent.\n")

    parts.append("\n---\n\n")
    parts.append("*Ky kontroll automatik nuk zëvendëson verifikimin manual nga avokati.*\n")

    return "".join(parts)