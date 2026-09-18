# FILE: backend/app/services/rag/document_review_post_processor.py
# PHOENIX PROTOCOL - DOCUMENT REVIEW POST-PROCESSOR V1.0
# Kontroll deterministik pas generimit të LLM-it për dokument review.
#   - Kontrollon ligjet e cituara kundrejt atyre që shfaqen në dokument
#   - Kontrollon nenet e cituara kundrejt atyre që shfaqen në dokument
#   - Zbulon format "Neni X.Y" → duhet "Neni X, par. Y"
#   - Zbulon kode të përziera (KPK vs KPRK, LMDHF vs KDMM)
#   - Shton seksion "KORRIGJIME DHE VËREJTJE" në fund

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

# Format i gabuar: "Neni X.Y" (duhet të jetë "Neni X, par. Y")
_BAD_ARTICLE_FORMAT_RE = re.compile(
    r'\bNen(?:i|it|in|ët)\s+(\d+)\.(\d+)\b',
    re.IGNORECASE | re.UNICODE
)

# Kodet e shkurtra të ligjeve që shpesh përzihen
_LAW_ABBREV_OUTPUT_RE = re.compile(
    r'\b(KPPRK|KPRK|KPK|LPK|LMDHF|LMD|LFK|LSHT|LPP|KDMM|KDPM|LPTS|PSRK)\b',
    re.IGNORECASE
)

# Numrat e lëndëve (për të detektuar "falso precedenta")
_CASE_NUMBER_RE = re.compile(
    r'\b(?:PML|Rev|KMLP|ANR|A\.NR|PZR|PA1|PKR|C|P|CA|PN|KP|KE)\.?\s*(?:[Nn]r\.?)?\s*\d+[/\-\d]*\b',
    re.IGNORECASE
)


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _normalize_law_number(raw: str) -> str:
    return re.sub(r'\s+', '', raw).upper().replace('–', '-')


def _extract_case_numbers(text: str) -> Set[str]:
    """Nxjerr numrat e lëndëve nga teksti."""
    found = _CASE_NUMBER_RE.findall(text)
    return set(n.upper().replace(' ', '') for n in found)


# ═══════════════════════════════════════════════════════════════════════════
# DETECTORS
# ═══════════════════════════════════════════════════════════════════════════

def _find_wrong_law_numbers(output_text: str, verified_citations: Dict[str, Any]) -> List[str]:
    """Ligjet me numër që NUK shfaqen në dokument."""
    whitelist_numbers = set(verified_citations.get("laws", []))
    # Hiq vetëm ata që janë me numër (XX/L-YYY format)
    whitelist_numbers = {n for n in whitelist_numbers if re.match(r'^\d{2}/[A-Z]-\d+$', n)}

    found = _LAW_NUMBER_OUTPUT_RE.findall(output_text)
    normalized_found = set(_normalize_law_number(f) for f in found)

    if not whitelist_numbers:
        return sorted(normalized_found)

    wrong = [n for n in normalized_found if n not in whitelist_numbers]
    return sorted(wrong)


def _find_missing_articles(output_text: str, verified_citations: Dict[str, Any]) -> List[str]:
    """Nenet që NUK shfaqen në dokument."""
    doc_articles = set(str(a["number"]) for a in verified_citations.get("articles", []))

    found = _ARTICLE_OUTPUT_RE.findall(output_text)
    normalized_found = set(found)

    if not doc_articles:
        return sorted(normalized_found)

    missing = [a for a in normalized_found if a not in doc_articles]
    return sorted(missing)


def _find_bad_article_format(output_text: str) -> List[Tuple[str, str]]:
    """Gjen format 'Neni X.Y' që duhet të jenë 'Neni X, par. Y'."""
    matches = _BAD_ARTICLE_FORMAT_RE.findall(output_text)
    return list(set(matches))


def _find_abbreviation_mismatches(output_text: str, verified_citations: Dict[str, Any]) -> List[str]:
    """
    Gjen kodet e shkurtra të ligjeve që NUK shfaqen në dokument.
    P.sh. nëse dokumenti citon LMDHF por output-i citon KDMM.
    """
    # Nxjerr akronimet që shfaqen në dokument
    doc_text_citations = verified_citations.get("laws", [])
    doc_abbrevs = set()
    for law in doc_text_citations:
        if re.match(r'^[A-Z]{2,6}$', law):
            doc_abbrevs.add(law.upper())

    found_abbrevs = set(m.upper() for m in _LAW_ABBREV_OUTPUT_RE.findall(output_text))

    if not doc_abbrevs:
        return sorted(found_abbrevs)

    # Kthe akronimet që janë në output por jo në dokument
    extra = [a for a in found_abbrevs if a not in doc_abbrevs]
    return sorted(extra)


def _find_fake_precedents(output_text: str, doc_case_numbers: Set[str]) -> List[str]:
    """
    Gjen numra lënde që trajtohen si precedentë, por që janë nga vetë dokumenti.
    Ky është hallucinim i rëndë logjik (dokumenti nuk mund të jetë precedent i vetes).
    """
    # Në output-in e seksionit precedentësh, gjej numrat
    fake = []
    for cn in doc_case_numbers:
        if cn in output_text.upper().replace(' ', ''):
            fake.append(cn)
    return sorted(fake)


# ═══════════════════════════════════════════════════════════════════════════
# PUBLIC — build correction section
# ═══════════════════════════════════════════════════════════════════════════

def build_review_correction_section(
    output_text: str,
    verified_citations: Dict[str, Any],
    doc_text: str,
    section_key: str = "",
) -> str:
    """
    Ndërton seksionin e korrigjimeve për një section të document review.
    Kthen string bosh nëse nuk ka probleme.
    """
    wrong_laws = _find_wrong_law_numbers(output_text, verified_citations)
    missing_articles = _find_missing_articles(output_text, verified_citations)
    bad_formats = _find_bad_article_format(output_text)
    abbrev_mismatches = _find_abbreviation_mismatches(output_text, verified_citations)

    # Fake precedents — vetëm për section precedentsh
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

    # ═══ Ligjet e gabuara ═══
    if wrong_laws:
        parts.append("\n### 🔴 Ligje që nuk shfaqen në dokument\n\n")
        for law in wrong_laws:
            parts.append(f"- ❌ **Ligji Nr. {law}** — nuk citohet në këtë dokument.\n")
        whitelist = [n for n in verified_citations.get("laws", []) if re.match(r'^\d{2}/[A-Z]-\d+$', n)]
        if whitelist:
            parts.append("\n✅ **Ligji/ligjet që shfaqen vërtet në dokument:**\n\n")
            for n in whitelist:
                parts.append(f"- **Ligji Nr. {n}**\n")

    # ═══ Akronimet e gabuara (KPK vs KPRK, LMDHF vs KDMM) ═══
    if abbrev_mismatches:
        parts.append("\n### 🔴 Kode ligjesh që nuk shfaqen në dokument\n\n")
        parts.append("Përgjigja citon kode ligjesh që **nuk shfaqen në dokumentin origjinal**:\n\n")
        for abbr in abbrev_mismatches:
            parts.append(f"- ❌ **{abbr}** — nuk citohet në këtë dokument.\n")

    # ═══ Nenet e gabuara ═══
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

    # ═══ Formati "Neni X.Y" ═══
    if bad_formats:
        parts.append("\n### 🟡 Format i gabuar i citimit\n\n")
        parts.append("Format i saktë është **\"Neni X, par. Y\"** — jo **\"Neni X.Y\"**:\n\n")
        for major, minor in bad_formats[:10]:
            parts.append(f"- ⚠️ `Neni {major}.{minor}` → **Neni {major}, par. {minor}**\n")

    # ═══ Fake precedents ═══
    if fake_precedents:
        parts.append("\n### 🔴 Numra lënde të trajtuar gabimisht si precedentë\n\n")
        parts.append("Këta numra **i përkasin dokumentit origjinal** — nuk janë precedentë:\n\n")
        for cn in fake_precedents:
            parts.append(f"- ❌ **{cn}** — ky është numri i lëndës së dokumentit, jo precedent.\n")

    parts.append("\n---\n\n")
    parts.append("*Ky kontroll automatik nuk zëvendëson verifikimin manual nga avokati.*\n")

    return "".join(parts)