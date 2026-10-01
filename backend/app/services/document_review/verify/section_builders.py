# FILE: backend/app/services/document_review/verify/section_builders.py
# PHOENIX PROTOCOL - VERIFY SECTION BUILDERS V1.2
# V1.2: SINGLE SOURCE OF TRUTH —
#       - `from ..verify_prompts import MIN_PRECEDENT_SIMILARITY` →
#         `from .prompt_constants import MIN_PRECEDENT_SIMILARITY`.
#         Hiqet varësia nga shimi legacy; importi vjen direkt nga moduli
#         modular që është burimi i vërtetë i konstantës.
# V1.1: LOG PREFIX FIX — "[V1.17]" → "[V1.1]".
# V1.0: Ekstraktuar nga draft_verifier.py V1.17 (pa ndryshim logjike).

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from .config import INTERNATIONAL_LAW_KEYWORDS
from .prompt_constants import MIN_PRECEDENT_SIMILARITY

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# INTERNATIONAL LAW DETECTION
# ═══════════════════════════════════════════════════════════════════════════

def is_international_law(law_hint: str) -> bool:
    if not law_hint:
        return False
    h = law_hint.lower()
    return any(kw in h for kw in INTERNATIONAL_LAW_KEYWORDS)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 2.A — VERIFIED ARTICLES BLOCK
# ═══════════════════════════════════════════════════════════════════════════

def build_verified_articles_block(verification_report: Dict[str, Any]) -> str:
    articles = (verification_report or {}).get("articles", []) or []

    verified = [a for a in articles if a.get("exists")]
    international = [
        a for a in articles
        if not a.get("exists") and is_international_law(a.get("law_hint", ""))
    ]
    missing = [
        a for a in articles
        if not a.get("exists") and not is_international_law(a.get("law_hint", ""))
    ]

    lines: List[str] = ["### A. Nenet e verifikuara", ""]

    if verified:
        grouped: Dict[str, List[str]] = {}
        for a in verified:
            doc = a.get("matched_doc") or {}
            law = (doc.get("law_title") or a.get("law_hint") or "—").strip()
            num = str(a.get("article_number", "?")).strip()
            para = f" par. {a['paragraph']}" if a.get("paragraph") else ""
            grouped.setdefault(law, []).append(f"Neni {num}{para}")

        for law, nums in grouped.items():
            lines.append(f"**{law}** ({len(nums)} nene):")
            lines.append(f"✅ {', '.join(nums)}")
            lines.append("")
    else:
        lines.append("⚠️ Nuk u verifikua asnjë nen në bazën e të dhënave.")
        lines.append("")

    if international:
        lines.append("### A2. Referenca ndërkombëtare")
        lines.append("")
        lines.append(
            "Këto referenca janë pjesë e instrumenteve ndërkombëtare dhe "
            "nuk verifikohen automatikisht nga baza e të dhënave ligjore të Kosovës:"
        )
        lines.append("")

        intl_grouped: Dict[str, List[str]] = {}
        for a in international:
            law = (a.get("law_hint") or "—").strip()
            num = str(a.get("article_number", "?")).strip()
            para = f" par. {a['paragraph']}" if a.get("paragraph") else ""
            intl_grouped.setdefault(law, []).append(f"Neni {num}{para}")

        for law, nums in intl_grouped.items():
            lines.append(f"**{law}**: {', '.join(nums)}")
        lines.append("")

    if missing:
        lines.append("### A3. Nene që NUK u gjetën në bazën e të dhënave")
        lines.append("")
        for a in missing:
            num = str(a.get("article_number", "?")).strip()
            hint = a.get("law_hint") or "—"
            lines.append(f"⚠️ Neni {num} i {hint} — nuk u gjet në bazë.")
        lines.append("")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 3.A — PRECEDENTS SKELETON
# ═══════════════════════════════════════════════════════════════════════════

def build_precedents_facts_skeleton(
    precedents: List[Dict[str, Any]],
) -> Tuple[str, int]:
    filtered = [
        p for p in precedents
        if (p.get("similarity") or 0.0) >= MIN_PRECEDENT_SIMILARITY
    ]

    if not filtered:
        return (
            "### A. Precedentët e identifikuar\n\n"
            "Nuk u identifikuan precedentë relevantë në bazën e Gjykatës Supreme "
            "për këtë çështje.\n\n",
            0,
        )

    lines: List[str] = ["### A. Precedentët e identifikuar", ""]

    for i, p in enumerate(filtered, 1):
        cn = str(p.get("case_number", "?")).strip()
        sim = float(p.get("similarity") or 0.0)
        excerpt = (p.get("text_excerpt") or "").strip()
        topic = p.get("topic_label")
        source = str(p.get("source") or "").strip()
        page = p.get("page")

        sim_pct = int(round(sim * 100))

        if sim >= 0.85:
            level = "1 — TEMË IDENTIKE"
        elif sim >= 0.70:
            level = "2 — TEMË E NGJASHME"
        else:
            level = "3 — TEMË E NDRYSHME"

        lines.append(f"**{i}. ⚖️ {cn}**")
        lines.append("")
        lines.append(f"**Ngjashmëria:** {sim_pct}%")
        lines.append("")

        if excerpt:
            lines.append("**Fragment:**")
            lines.append("")
            lines.append(f"> {excerpt[:400]}")
            lines.append("")

        lines.append(f"**Pse relevant:** {{PSE_RELEVANT_{i}}}")
        lines.append("")
        lines.append(f"**Niveli i relevancës:** {level}")
        lines.append("")
        lines.append("**Sipas bazës së Gjykatës Supreme**")

        if topic:
            lines.append("")
            lines.append(f"**Tema:** {topic}")

        if source:
            lines.append("")
            source_str = source
            if page:
                source_str += f", faqe {page}"
            lines.append(f"*Burimi: {source_str}*")

        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines), len(filtered)


def _strip_precedent_a_sections(text: str) -> str:
    if not text:
        return text

    pattern = re.compile(
        r'(?:^|\n)[ \t]*(?:#{1,4}\s*)?(?:[▸◆►•]\s*)?'
        r'A\.?\s*Precedent[ëe]t?\s+(?:e\s+)?identifikuar'
        r'.*?(?=\n[ \t]*(?:#{1,4}\s*)?(?:[▸◆►•]\s*)?B\.|\Z)',
        re.DOTALL | re.IGNORECASE,
    )

    cleaned = pattern.sub('\n', text)
    return cleaned.strip()


def _extract_pse_relevant_map(text: str, count: int) -> Dict[int, str]:
    result: Dict[int, str] = {}

    block = re.search(
        r'PSE_RELEVANT_START\s*\n(.*?)\n\s*PSE_RELEVANT_END',
        text,
        re.DOTALL | re.IGNORECASE,
    )
    if block:
        for raw in block.group(1).split("\n"):
            line = raw.strip()
            m = re.match(r'^(\d+)\s*[:.\-—]\s*(.+)$', line)
            if m:
                try:
                    result[int(m.group(1))] = m.group(2).strip()
                except ValueError:
                    pass
        if result:
            return result

    inline_matches = re.findall(
        r'(?:^|\n)\s*(?:[#*>\-]\s*)?(?:\*\*)?Pse relevant[^\n:]*[:.]\s*(.+?)(?=\n|$)',
        text,
        re.IGNORECASE,
    )
    for i, val in enumerate(inline_matches[:count], 1):
        if val.strip() and val.strip() != "[Nuk u gjenerua nga LLM-ja]":
            result[i] = val.strip()

    return result


def post_process_precedents_section(
    llm_output: str,
    precedents: List[Dict[str, Any]],
) -> str:
    facts_block, count = build_precedents_facts_skeleton(precedents)

    if count == 0:
        return facts_block

    text = llm_output or ""

    text_clean = _strip_precedent_a_sections(text)

    pse_map = _extract_pse_relevant_map(text, count)
    if not pse_map:
        pse_map = _extract_pse_relevant_map(text_clean, count)

    if not pse_map:
        logger.warning(
            f"⚠️ [V1.2] Nuk u nxorën Pse relevant për {count} precedentë. "
            f"Output LLM fillon: {text[:200]}"
        )

    rest = re.sub(
        r'PSE_RELEVANT_START.*?PSE_RELEVANT_END\s*',
        '',
        text_clean,
        count=1,
        flags=re.DOTALL | re.IGNORECASE,
    ).strip()

    rest = re.sub(
        r'^#{1,4}\s*3\.?\s*PRECEDENT[ËE]?\s+MB[ËE]SHTET[ËE]S\s*\n+',
        '',
        rest,
        count=1,
        flags=re.IGNORECASE,
    )
    rest = re.sub(
        r'^#{1,4}\s*PRECEDENT[ËE]?\s+MB[ËE]SHTET[ËE]S\s*\n+',
        '',
        rest,
        count=1,
        flags=re.IGNORECASE,
    )

    for i in range(1, count + 1):
        txt = pse_map.get(i) or "_[Nuk u gjenerua nga LLM-ja]_"
        facts_block = facts_block.replace(f"{{PSE_RELEVANT_{i}}}", txt)

    if rest:
        return facts_block + "\n" + rest
    return facts_block


# ═══════════════════════════════════════════════════════════════════════════
# POST-PROCESS DISPATCH
# ═══════════════════════════════════════════════════════════════════════════

def post_process_section(
    section_key: str,
    llm_content: str,
    verification_report: Dict[str, Any],
    precedents: Optional[List[Dict[str, Any]]] = None,
) -> str:
    if section_key == "legal_quality":
        block_a = build_verified_articles_block(verification_report)
        return block_a + "\n" + (llm_content or "")

    if section_key == "supporting_precedents":
        return post_process_precedents_section(
            llm_content or "",
            precedents or [],
        )

    return llm_content or ""