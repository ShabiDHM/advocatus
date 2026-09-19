# FILE: backend/app/services/document_review/report_builder.py
# PHOENIX PROTOCOL - REPORT BUILDER V1.0
# Monton raportin final duke kombinuar:
#   - Seksionet narrative (nga LLM)
#   - Kontekstin e verifikuar (nga Python)
#   - Statistikat përfundimtare

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


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

    lines = []

    # ═══ HEADER ═══
    lines.append(f"# RAPORT VERIFIKIMI — {document_type.upper()}")
    lines.append("")
    lines.append(f"**Dokumenti:** {file_name}")
    lines.append(f"**Lloji:** {document_type}")
    lines.append(f"**Data e verifikimit:** {datetime.now(timezone.utc).strftime('%d.%m.%Y %H:%M')}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ═══ 1. PËRMBLEDHJE EKZEKUTIVE ═══
    if "document_summary" in sections:
        lines.append(f"## {sections['document_summary']['title']}")
        lines.append("")
        lines.append(sections["document_summary"]["content"])
        lines.append("")
        lines.append("---")
        lines.append("")

    # ═══ 2. VERIFIKIMI I NENEVE ═══
    if "article_verification" in sections:
        lines.append(f"## {sections['article_verification']['title']}")
        lines.append("")
        lines.append(sections["article_verification"]["content"])
        lines.append("")
        lines.append("---")
        lines.append("")

    # ═══ 3. PRECEDENTËT ═══
    if "supreme_court_precedents" in sections:
        lines.append(f"## {sections['supreme_court_precedents']['title']}")
        lines.append("")
        lines.append(sections["supreme_court_precedents"]["content"])
        lines.append("")
        lines.append("---")
        lines.append("")

    # ═══ 4. CILËSIA E HARTIMIT ═══
    if "drafting_quality" in sections:
        lines.append(f"## {sections['drafting_quality']['title']}")
        lines.append("")
        lines.append(sections["drafting_quality"]["content"])
        lines.append("")
        lines.append("---")
        lines.append("")

    # ═══ 5. GABIME DHE KORRIGJIME ═══
    if "errors_corrections" in sections:
        lines.append(f"## {sections['errors_corrections']['title']}")
        lines.append("")
        lines.append(sections["errors_corrections"]["content"])
        lines.append("")
        lines.append("---")
        lines.append("")

    # ═══ 6. HAPAT KONKRET ═══
    if "action_steps" in sections:
        lines.append(f"## {sections['action_steps']['title']}")
        lines.append("")
        lines.append(sections["action_steps"]["content"])
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
    lines = []

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