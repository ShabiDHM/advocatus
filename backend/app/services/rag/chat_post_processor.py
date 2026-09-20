# FILE: backend/app/services/rag/chat_post_processor.py
# PHOENIX PROTOCOL - CHAT POST-PROCESSOR V2.2
# V2.2: FIX — _find_missing_articles normalizon "Neni 1.2" -> "1" para krahasimit,
#       duke perdorur _normalize_article_number V1.5. Eliminon false-positives
#       per citime me paragraph.
# V2.1: Shtuar verejtje pozitive per "dy ligje te vlefshme" me burim dokumenti.
# V2.0: Hequr kontradiktat. Vetem citime ligjesh + nenesh.
# V1.2: FIX formatim markdown.

import re
import logging
from typing import Dict, Any, List

from ..document_review.citation_extractor import _normalize_article_number

logger = logging.getLogger(__name__)

MAX_DISPLAY_CORRECT_ARTICLES = 5


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


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _normalize_law_number(raw: str) -> str:
    return re.sub(r'\s+', '', raw).upper().replace('–', '-')


def _normalize_article_str(raw: str) -> str:
    """
    V2.2: Normalizon nje string artikulli sipas konventes ligjore shqipe.
    "1.2" -> "1"   (neni 1, par. 2)
    "1"   -> "1"
    "5/2" -> "5/2" (formë e pazakonshme, lihet)
    """
    if not raw:
        return raw
    art, _ = _normalize_article_number(raw, None)
    return art


def _extract_articles_normalized(output_text: str) -> List[str]:
    """
    V2.2: Nxjerr nenet nga output-i i LLM dhe i normalizon.
    Kthen liste me numra nenesh unik (pa paragraph).
    """
    found: List[str] = []
    for m in _ARTICLE_OUTPUT_RE.finditer(output_text):
        art = _normalize_article_str(m.group(1))
        if art:
            found.append(art)
    return found


# ═══════════════════════════════════════════════════════════════════════════
# DETECTORS
# ═══════════════════════════════════════════════════════════════════════════

def _find_wrong_law_numbers(output_text: str, whitelist: Dict[str, Any]) -> List[str]:
    whitelist_numbers = set(whitelist.get("laws_number", []))
    if not whitelist_numbers:
        found = _LAW_NUMBER_OUTPUT_RE.findall(output_text)
        normalized_found = set(_normalize_law_number(f) for f in found)
        return sorted(normalized_found)

    found = _LAW_NUMBER_OUTPUT_RE.findall(output_text)
    normalized_found = set(_normalize_law_number(f) for f in found)

    wrong = [n for n in normalized_found if n not in whitelist_numbers]
    return sorted(wrong)


def _find_missing_articles(output_text: str, whitelist: Dict[str, Any]) -> List[str]:
    """
    V2.2: Krahason nenet (te normalizuara) me whitelist.
    Normalizon edhe whitelist-in per te shmangur mospershtatje formati.
    """
    # V2.2: Normalizo whitelist-in (defensive)
    whitelist_articles = set(
        _normalize_article_str(a) for a in whitelist.get("articles", [])
    )

    # V2.2: Normalizo output-in
    normalized_found = set(_extract_articles_normalized(output_text))

    if not whitelist_articles:
        return sorted(normalized_found)

    missing = [a for a in normalized_found if a not in whitelist_articles]
    return sorted(missing)


# ═══════════════════════════════════════════════════════════════════════════
# V2.1: DUAL LAW NOTE (vërejtje pozitive)
# ═══════════════════════════════════════════════════════════════════════════

def _build_dual_law_note(whitelist: Dict[str, Any]) -> str:
    """
    Nëse dokumentet gjykatore citojnë DY OSE MË SHUMË ligje të ndryshme,
    shto një vërejtje pozitive që tregon cilat ligje dhe në cilat dokumente.
    """
    laws_by_file = whitelist.get("laws_by_file", {})
    all_laws = whitelist.get("laws_number", [])

    if len(all_laws) < 2:
        return ""

    distinct_sets = [tuple(sorted(laws)) for laws in laws_by_file.values()]
    if len(set(distinct_sets)) < 2:
        return ""

    parts: List[str] = []
    parts.append("\n### ℹ️ Vërejtje pozitive: Ligje të ndryshme në dokumente të ndryshme\n\n")
    parts.append("Fashikulli përmban ligje të ndryshme në dokumente të ndryshme gjykatore:\n\n")

    for file_name, laws in laws_by_file.items():
        for law in laws:
            parts.append(f"- **Ligji Nr. {law}** — cituar në `{file_name}`\n")

    parts.append(
        "\n*Rekomandim: Kontrollo cilën ligj citon dokumenti përkatës para se të "
        "përdorësh si referencë ligjore në raport.*\n"
    )

    return "".join(parts)


# ═══════════════════════════════════════════════════════════════════════════
# PUBLIC — build correction section
# ═══════════════════════════════════════════════════════════════════════════

def build_correction_section(
    output_text: str,
    whitelist: Dict[str, Any],
) -> str:
    wrong_laws = _find_wrong_law_numbers(output_text, whitelist)
    missing_articles = _find_missing_articles(output_text, whitelist)
    dual_law_note = _build_dual_law_note(whitelist)

    if not (wrong_laws or missing_articles or dual_law_note):
        return ""

    parts: List[str] = []
    parts.append("\n\n---\n")
    parts.append("## ⚠️ KORRIGJIME DHE VËREJTJE AUTOMATIKE\n\n")

    source_filter = whitelist.get("source_filter", "unknown")
    if source_filter == "judicial_only":
        parts.append("*Ky seksion kontrollohet automatikisht — bazuar në citimet që shfaqen në **dokumentet gjykatore** të fashikullit.*\n")
    else:
        parts.append("*Ky seksion kontrollohet automatikisht — bazuar në citimet që shfaqen në shkresat e fashkullit.*\n")

    # ═══ Ligjet e gabuara ═══
    if wrong_laws:
        parts.append("\n### 🔴 Ligje që nuk shfaqen në shkresat gjykatore\n\n")
        parts.append("Përgjigja më sipër citon ligje që **nuk shfaqen në asnjë dokument gjykatore të kësaj lënde**:\n\n")
        for law in wrong_laws:
            parts.append(f"- ❌ **Ligji Nr. {law}**\n")
        whitelist_nums = whitelist.get("laws_number", [])
        if whitelist_nums:
            parts.append("\n✅ **Ligji/ligjet që shfaqen në shkresat gjykatore:**\n\n")
            for n in whitelist_nums:
                parts.append(f"- **Ligji Nr. {n}**\n")

    # ═══ Nenet e gabuara ═══
    if missing_articles:
        parts.append("\n### 🔴 Nene që nuk shfaqen në shkresat gjykatore\n\n")
        parts.append("Përgjigja më sipër citon nene që **nuk ekzistojnë në shkresat gjykatore të kësaj lënde**:\n\n")
        for art in missing_articles[:10]:
            parts.append(f"- ❌ **Neni {art}**\n")
        if len(missing_articles) > 10:
            parts.append(f"- ... dhe {len(missing_articles) - 10} nene të tjera.\n")

        correct_display = whitelist.get("articles_display") or []
        correct_all = whitelist.get("articles") or []
        correct_to_show = correct_display if correct_display else correct_all[:MAX_DISPLAY_CORRECT_ARTICLES]

        if correct_to_show:
            parts.append("\n✅ **Nenet kryesore që shfaqen në shkresat gjykatore:**\n\n")
            for art in correct_to_show:
                parts.append(f"- **Neni {art}**\n")
            if len(correct_all) > len(correct_to_show):
                parts.append(
                    f"\n*... dhe {len(correct_all) - len(correct_to_show)} nene të tjera në shkresat gjykatore.*\n"
                )

    # ═══ Vërejtje pozitive: dy ligje ═══
    if dual_law_note:
        parts.append(dual_law_note)

    parts.append("\n---\n\n")
    parts.append("*Ky kontroll automatik nuk zëvendëson verifikimin manual nga avokati.*\n")

    return "".join(parts)