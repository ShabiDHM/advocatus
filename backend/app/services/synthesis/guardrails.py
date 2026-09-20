# FILE: backend/app/services/synthesis/guardrails.py
# PHOENIX PROTOCOL - GUARDRAILS V1.1
# V1.1: FIX konsistence me citation_extraction V1.2 (split article/paragraph).
#       (A) verify_attribution: normalizo "1.2" ↔ "1, par. 2" përpara krahasimit
#       (B) verify_citations: normalizo "1.2" → "1" për krahasim me doc_articles
#       (C) correct_citations_with_llm: përfshi paragraph në articles_list
# V1.0: Ekstraktuar nga synthesis_service.py V3.8.

import logging
import re
from typing import Any, Dict, List, Set, Tuple
from collections import defaultdict

from app.services.llm.llm_client import _call_llm, FAST_SEARCH_MODEL

from .patterns import (
    CITATION_WITH_LAW_PATTERN,
    VERIFIED_ARTICLE_PATTERN,
    DEADLINE_PATTERN,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# V1.1: HELPERS — unifikim me citation_extraction
# ═══════════════════════════════════════════════════════════════════════════

def _normalize_article_display(
    article_raw: str,
    paragraph_raw: str = None,
) -> str:
    """
    V1.1: Ndan + formaton numrin e nenit njësoj si citation_extraction V1.2.

    Rastet:
      ("1.2", None) → "1, par. 2"
      ("1",   "2")  → "1, par. 2"
      ("1",   None) → "1"
      ("1.2.3", None) → "1.2.3"  (format i panjohur, ruaj)

    Përdoret për krahasim me article_law_pairs të formatuara.
    """
    art = (article_raw or "").strip()
    par = (paragraph_raw or "").strip() if paragraph_raw else None

    if par:
        return f"{art}, par. {par}"

    m = re.match(r'^(\d+)\.(\d+)$', art)
    if m:
        return f"{m.group(1)}, par. {m.group(2)}"

    return art


def _extract_base_article_number(article_raw: str) -> str:
    """
    V1.1: Nxjerr VETËM numrin bazë të nenit (pa paragraf).
    Përdoret për krahasim me doc_articles_available.

      "1.2" → "1"
      "1"   → "1"
      "1/2" → "1/2"  (jo format paragrafi)
    """
    art = (article_raw or "").strip()
    m = re.match(r'^(\d+)\.(\d+)$', art)
    if m:
        return m.group(1)
    return art


# ═══════════════════════════════════════════════════════════════════════════
# GUARDRAIL #5 — Verifikim i Atribuimit (Neni + Ligji)
# ═══════════════════════════════════════════════════════════════════════════

def verify_attribution_word_by_word(
    output_text: str,
    verified_citations: Dict[str, Any],
) -> Dict[str, Any]:
    if not output_text:
        return {"verified": [], "unverified": [], "hallucination_rate": 0.0}

    article_law_pairs = set(
        tuple(p) for p in verified_citations.get("article_law_pairs", [])
    )

    if not article_law_pairs:
        return {
            "verified": [],
            "unverified": [],
            "hallucination_rate": 0.0,
            "warning": "no_pairs_available",
        }

    verified: List[Dict[str, Any]] = []
    unverified: List[Dict[str, Any]] = []
    seen: Set[Tuple[str, str]] = set()

    for match in CITATION_WITH_LAW_PATTERN.finditer(output_text):
        article_raw = match.group(1)
        paragraph_raw = match.group(2)
        law = match.group(3).upper()

        # V1.1: Normalizo article në formatin "1, par. 2" (i njëjti si citation_extraction)
        article_normalized = _normalize_article_display(article_raw, paragraph_raw)

        law_normalized = law.strip()
        key = (article_normalized, law_normalized)
        if key in seen:
            continue
        seen.add(key)

        entry = {
            "article": article_normalized,
            "paragraph": paragraph_raw,
            "law": law_normalized,
            "raw": match.group(0).strip(),
        }

        found = False
        for pair_art, pair_law in article_law_pairs:
            if pair_art != article_normalized:
                continue
            if pair_law.upper() == law_normalized:
                found = True
                break
            if law_normalized in pair_law.upper() or pair_law.upper() in law_normalized:
                found = True
                break

        if found:
            verified.append(entry)
        else:
            unverified.append(entry)

    total = len(verified) + len(unverified)
    hallucination_rate = (
        round(len(unverified) / max(1, total) * 100, 1) if total > 0 else 0.0
    )

    return {
        "verified": verified,
        "unverified": unverified,
        "total_attributions": total,
        "hallucination_rate": hallucination_rate,
    }


# ═══════════════════════════════════════════════════════════════════════════
# GUARDRAIL #5b — Detektim i Kontradiktave të Afateve
# ═══════════════════════════════════════════════════════════════════════════

def detect_deadline_contradictions(output_text: str) -> Dict[str, Any]:
    if not output_text:
        return {"deadlines_found": [], "contradictions": []}

    deadlines: List[Dict[str, Any]] = []

    for match in DEADLINE_PATTERN.finditer(output_text):
        num = int(match.group(1))
        unit = match.group(2).lower().strip("ëe")

        if unit.startswith("dit"):
            unit_normalized = "ditë"
        elif unit.startswith("muaj"):
            unit_normalized = "muaj"
        elif unit.startswith("jav"):
            unit_normalized = "javë"
        elif unit.startswith("vjet"):
            unit_normalized = "vjet"
        else:
            unit_normalized = unit

        deadlines.append({
            "num": num,
            "unit": unit_normalized,
            "raw": match.group(0).strip(),
            "position": match.start(),
        })

    contradictions: List[Dict[str, Any]] = []
    by_unit: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for d in deadlines:
        by_unit[d["unit"]].append(d)

    for unit, items in by_unit.items():
        if len(items) < 2:
            continue
        unique_nums = set(item["num"] for item in items)
        if len(unique_nums) > 1:
            contradictions.append({
                "unit": unit,
                "values": sorted(unique_nums),
                "count": len(items),
                "examples": [item["raw"] for item in items[:3]],
            })

    return {
        "deadlines_found": deadlines,
        "contradictions": contradictions,
    }


# ═══════════════════════════════════════════════════════════════════════════
# GUARDRAIL #4 — Citation Checker (fjalë-për-fjalë, vetëm numrat)
# ═══════════════════════════════════════════════════════════════════════════

def verify_citations_word_by_word(
    output_text: str,
    doc_articles_available: Set[str],
) -> Dict[str, Any]:
    if not output_text:
        return {
            "verified": [],
            "unverified": [],
            "total_articles_output": 0,
            "hallucination_rate": 0.0,
        }

    verified: List[str] = []
    unverified: List[str] = []
    seen: Set[str] = set()

    for match in VERIFIED_ARTICLE_PATTERN.finditer(output_text):
        num_raw = match.group(1)

        # V1.1: Normalizo "1.2" → "1" për krahasim me doc_articles_available
        # (i cili tani përmban numrat e bazë, jo format "1.2")
        num = _extract_base_article_number(num_raw)

        if num in seen:
            continue
        seen.add(num)

        if num in doc_articles_available:
            verified.append(num)
        else:
            unverified.append(num)

    total = len(seen)
    hallucination_rate = (
        round(len(unverified) / max(1, total) * 100, 1) if total > 0 else 0.0
    )

    return {
        "verified": sorted(verified),
        "unverified": sorted(unverified),
        "total_articles_output": total,
        "hallucination_rate": hallucination_rate,
    }


# ═══════════════════════════════════════════════════════════════════════════
# GUARDRAIL #3 — Verifikim i Dyfishtë (LLM Correction)
# ═══════════════════════════════════════════════════════════════════════════

def correct_citations_with_llm(
    output_text: str,
    checker_report: Dict[str, Any],
    attribution_report: Dict[str, Any],
    verified_citations: Dict[str, Any],
) -> str:
    unverified_articles = checker_report.get("unverified", [])
    unverified_attrs = attribution_report.get("unverified", [])

    if not unverified_articles and not unverified_attrs:
        return output_text

    laws_list = ", ".join(verified_citations.get("laws", [])) or "asnjë"

    # V1.1: Përfshi paragraph në listën e neneve
    articles_list = ", ".join(
        f"Neni {a['number']}" + (f", par. {a['paragraph']}" if a.get("paragraph") else "")
        for a in verified_citations.get("articles", [])[:50]
    ) or "asnjë"

    # article_law_pairs tani vjen i formatuar "1, par. 2" nga V1.2
    pairs_list = " | ".join(
        f"Neni {a} i {l}" for a, l in verified_citations.get("article_law_pairs", [])[:50]
    ) or "asnjë"

    issues = []
    if unverified_articles:
        issues.append(
            "NENET QË NUK EKZISTOJNË NË FASHIKULL:\n" +
            "\n".join(f"  ❌ Neni {n}" for n in unverified_articles)
        )
    if unverified_attrs:
        issues.append(
            "ÇIFTET E GABUARA (Neni + Ligji):\n" +
            "\n".join(
                f"  ❌ {a['raw']} (kombinim i palejuar)" for a in unverified_attrs
            )
        )

    system_prompt = """Ti je "Verifikues i Saktësisë Ligjore" në Gjykatën Supreme të Kosovës.

DETYRA: Pastron output-in duke:
1. Fshirë citimet e neneve që NUK ekzistojnë në dokumente.
2. Fshirë çiftet e gabuara (Neni X i LIGJI) që nuk shfaqen në dokumente.

RREGULLA ABSOLUTE:
1. Fshij ÇDO nen që shfaqet në "NENET QË NUK EKZISTOJNË".
2. Fshij ÇDO citim që shfaqet në "ÇIFTET E GABUARA".
3. Ruaj vetëm citimet e vërteta që ekzistojnë në dokumente.
4. NUK LEJOHET të shtosh nene të re.
5. Ruaj strukturën, titujt, formatimin markdown.
6. NUK shpjego — kthe VETËM tekstin e pastruar."""

    user_content = f"""BURIMI I SË VËRTETËS:
- Ligjet e verifikuara: {laws_list}
- Nenet e verifikuara: {articles_list}
- Çiftet e vërteta (Neni X i Ligji): {pairs_list}

───────────────────────────────────────────────────────

PROBLEMET E ZBULUARA:
{chr(10).join(issues)}

───────────────────────────────────────────────────────

OUTPUT-I QË DUHET PASTRUAR:
{output_text}

───────────────────────────────────────────────────────

Kthe tekstin e pastruar (pa gabime citimesh):"""

    try:
        corrected = _call_llm(
            system_prompt=system_prompt,
            user_content=user_content,
            json_mode=False,
            temperature=0.0,
            model=FAST_SEARCH_MODEL,
        )
        return corrected or output_text
    except Exception as e:
        logger.warning(f"⚠️ [GUARDRAIL #3] LLM correction failed: {e}")
        return output_text