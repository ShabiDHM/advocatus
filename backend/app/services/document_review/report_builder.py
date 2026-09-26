# FILE: backend/app/services/document_review/report_builder.py
# PHOENIX PROTOCOL - REPORT BUILDER V1.1
# V1.1: ANALIZA_E_THELLUAR + LOOP REFACTOR —
#       - Shtuar seksioni i 7-të "analiza_e_thelluar" në montim
#         (V4.14 e prompts.py e kishte shtuar në prompts por jo në raport).
#       - Refactor: 7 blloqe if të përsëritura → 1 loop mbi
#         SECTION_ORDER. Ndryshimi i ardhshëm i prompts.py
#         (shtim/heqje seksioni) mbetet në sinkron automatikisht.
# V1.0: Monton raportin final duke kombinuar:
#       - Seksionet narrative (nga LLM)
#       - Kontekstin e verifikuar (nga Python)
#       - Statistikat përfundimtare

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# V1.1: SECTION ORDER — i vetmi vend për të shtuar/hequr seksione
# ═══════════════════════════════════════════════════════════════════════════

SECTION_ORDER: List[str] = [
    "document_summary",
    "article_verification",
    "supreme_court_precedents",
    "drafting_quality",
    "errors_corrections",
    "action_steps",
    "analiza_e_thelluar",   # V1.1: V4.14 e shtoi në prompts.py, tani edhe këtu
]


# ═══════════════════════════════════════════════════════════════════════════
# BUILD REPORT
# ═══════════════════════════════════════════════════════════════════════════

def build_full_report(
    sections: Dict[str, Dict[str, Any]],
    citation_profile: Dict[str, Any],
    fact_profile: Dict[str, Any],
    verification_report: Dict[str, Any],
    document_meta: Dict[str, Any],
) -> str:
    """
    Monton raportin e plotë në markdown.

    Args:
        sections: {"document_summary": {"title": "...", "content": "..."}, ...}
        citation_profile: output nga build_citation_profile
        fact_profile: output nga build_fact_profile
        verification_report: output nga verify_all
        document_meta: {"file_name": "...", "document_type": "..."}

    Returns:
        String markdown me raportin e plotë.
    """
    file_name = document_meta.get("file_name", "Dokument")
    document_type = document_meta.get("document_type", "Dokument")

    lines: List[str] = []

    # ═══ HEADER ═══
    lines.append(f"# RAPORT VERIFIKIMI — {document_type.upper()}")
    lines.append("")
    lines.append(f"**Dokumenti:** {file_name}")
    lines.append(f"**Lloji:** {document_type}")
    lines.append(f"**Data e verifikimit:** {datetime.now(timezone.utc).strftime('%d.%m.%Y %H:%M')}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ═══ SEKSIONET NARRATIVE (V1.1: loop) ═══
    for key in SECTION_ORDER:
        sec = sections.get(key)
        if not sec:
            continue
        title = sec.get("title") or key
        content = sec.get("content") or ""
        if not content.strip():
            continue

        lines.append(f"## {title}")
        lines.append("")
        lines.append(content)
        lines.append("")
        lines.append("---")
        lines.append("")

    # ═══ APPENDIX — Statistikat ═══
    lines.append("## 📊 STATISTIKAT E VERIFIKIMIT")
    lines.append("")
    lines.extend(_build_stats_section(citation_profile, fact_profile, verification_report))
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*Ky raport është gjeneruar automatikisht. Verifikimi final mbetet përgjegjësi e avokatit.*")

    return "\n".join(lines)


def _build_stats_section(
    citation_profile: Dict[str, Any],
    fact_profile: Dict[str, Any],
    verification_report: Dict[str, Any],
) -> List[str]:
    """Ndërton seksionin e statistikave."""
    lines: List[str] = []

    stats = verification_report.get("stats", {})

    # Nenet
    articles_total = stats.get("articles_total", 0)
    articles_verified = stats.get("articles_verified", 0)
    articles_not_found = stats.get("articles_not_found", 0)
    lines.append(f"**Nenet:**")
    lines.append(f"- Gjithsej të nxjerra: {articles_total}")
    lines.append(f"- ✅ Verifikuar: {articles_verified}")
    if articles_not_found > 0:
        lines.append(f"- ❌ Nuk u gjetën: {articles_not_found}")
    lines.append("")

    # Ligjet
    laws_total = stats.get("laws_total", 0)
    laws_verified = stats.get("laws_verified", 0)
    lines.append(f"**Ligjet:**")
    lines.append(f"- Gjithsej të nxjerra: {laws_total}")
    lines.append(f"- ✅ Verifikuar: {laws_verified}")
    lines.append("")

    # Lëndët
    cases_total = stats.get("case_numbers_total", 0)
    cases_cited = stats.get("case_numbers_cited", 0)
    precedents_verified = stats.get("precedents_verified", 0)
    lines.append(f"**Numrat e lëndëve:**")
    lines.append(f"- Gjithsej: {cases_total}")
    lines.append(f"- Të cituar (jo own): {cases_cited}")
    lines.append(f"- Precedentë të verifikuar: {precedents_verified}")
    lines.append("")

    # Faktet
    dates_count = fact_profile.get("stats", {}).get("total_dates", 0)
    deadlines_count = fact_profile.get("stats", {}).get("legal_deadlines", 0)
    parties_count = fact_profile.get("stats", {}).get("total_parties", 0)
    lines.append(f"**Faktet:**")
    lines.append(f"- Data të nxjerra: {dates_count}")
    lines.append(f"- Afate procedurale: {deadlines_count}")
    lines.append(f"- Palë: {parties_count}")
    lines.append("")

    return lines