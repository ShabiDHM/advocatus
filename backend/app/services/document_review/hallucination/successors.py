# FILE: backend/app/services/document_review/hallucination/successors.py
# PHOENIX PROTOCOL - HALLUCINATION SUCCESSORS V1.26
# V1.26: DEAD PARAMETER FIX —
#        - `scan_dict_for_laws(d, context_label)` pranonte `context_label`
#          por nuk e përdorte. Të gjithë thirrësit e kalonin (successor[i],
#          art5.sr, art3.alt2, ...) → informacion konteksti i humbur.
#          Tani logohet në DEBUG për tracing se cilat burime kontribuuan
#          cilat numra. Nuk ndryshon API-n, logjikën, as performance.
# V1.25: Grumbullon ligjet pasardhëse nga verification_report.

import logging
from typing import Any, Dict, Set

from .normalize import safe_normalize_law
from .extract import extract_law_numbers_from_title_strict

logger = logging.getLogger(__name__)


# Field-at që përmbajnë numër ligji direkt
_EXPLICIT_LAW_NUMBER_FIELDS = ("law_number", "number", "new_law")

# Field-at që përmbajnë titull ligji (numri nxirret me regex)
_LAW_TITLE_FIELDS = ("law_title", "law_name")


def scan_dict_for_laws(d: Dict[str, Any], context_label: str) -> Set[str]:
    """
    Nxjerr numra ligjesh nga një dict (law_number + law_title).

    context_label: etiketë për tracing (p.sh. "successor[0]", "art5.sr").
                   Logohet në DEBUG kur kontribuohen numra.
    """
    found: Set[str] = set()
    if not isinstance(d, dict):
        return found

    for key in _EXPLICIT_LAW_NUMBER_FIELDS:
        val = d.get(key)
        if val:
            n = safe_normalize_law(str(val))
            if n:
                found.add(n)

    for key in _LAW_TITLE_FIELDS:
        val = d.get(key)
        if val:
            nums = extract_law_numbers_from_title_strict(str(val))
            if nums:
                found.update(nums)

    # V1.26: Përdorim context_label për tracing
    if found and logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            f"[HALLUCINATION V1.26] scan_dict_for_laws({context_label}): "
            f"+{len(found)} → {sorted(found)}"
        )

    return found


def collect_successor_laws(verification_report: Dict[str, Any]) -> Set[str]:
    """
    Grumbullon të gjithë numrat e ligjeve pasardhëse nga verification_report.
    Përfshin: successor_laws, article law_hint, suggested_replacement,
    matched_doc, alternative_laws.
    """
    successors: Set[str] = set()
    if not verification_report:
        return successors

    top_level = verification_report.get("successor_laws") or []
    for idx, s in enumerate(top_level):
        if isinstance(s, dict):
            successors.update(scan_dict_for_laws(s, f"successor[{idx}]"))
        elif isinstance(s, str):
            n = safe_normalize_law(s)
            if n:
                successors.add(n)
            successors.update(extract_law_numbers_from_title_strict(s))

    for idx, a in enumerate(verification_report.get("articles", []) or []):
        if not isinstance(a, dict):
            continue

        art_num = a.get("article_number", "?")

        law_hint = a.get("law_hint")
        if law_hint:
            n = safe_normalize_law(str(law_hint))
            if n:
                successors.add(n)
            successors.update(extract_law_numbers_from_title_strict(str(law_hint)))

        sr = a.get("suggested_replacement")
        if isinstance(sr, dict):
            successors.update(scan_dict_for_laws(sr, f"art{art_num}.sr"))

        matched_doc = a.get("matched_doc")
        if isinstance(matched_doc, dict):
            successors.update(scan_dict_for_laws(matched_doc, f"art{art_num}.md"))

        alts = a.get("alternative_laws")
        if isinstance(alts, list):
            for alt_idx, alt in enumerate(alts):
                if isinstance(alt, dict):
                    successors.update(scan_dict_for_laws(alt, f"art{art_num}.alt{alt_idx}"))

        alt_matched = a.get("matched_document")
        if isinstance(alt_matched, dict):
            successors.update(scan_dict_for_laws(alt_matched, f"art{art_num}.md2"))

    if successors:
        logger.info(
            f"[HALLUCINATION V1.26] Successor laws collected: {sorted(successors)}"
        )
    else:
        logger.info(f"[HALLUCINATION V1.26] No successor laws collected.")

    return successors