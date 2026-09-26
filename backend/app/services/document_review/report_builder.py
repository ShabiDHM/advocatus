# FILE: backend/app/services/document_review/report_builder.py
# PHOENIX PROTOCOL - REPORT BUILDER V1.2
# V1.2: STATS TRANSPARENCY — Breakdown i plotë i neneve:
#       verified + via_alias + in_successor + international_treaty +
#       exist_elsewhere + not_found = articles_total. Eliminon kontradiktën
#       "59 vs 52" ku 7 nene 'exist elsewhere' nuk raportoheshin.
# V1.1: ANALIZA_E_THELLUAR + LOOP REFACTOR.
# V1.0: Monton raportin final.

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


SECTION_ORDER: List[str] = [
    "document_summary",
    "article_verification",
    "supreme_court_precedents",
    "drafting_quality",
    "errors_corrections",
    "action_steps",
    "analiza_e_thelluar",
]


def build_full_report(
    sections: Dict[str, Dict[str, Any]],
    citation_profile: Dict[str, Any],
    fact_profile: Dict[str, Any],
    verification_report: Dict[str, Any],
    document_meta: Dict[str, Any],
) -> str:
    file_name = document_meta.get("file_name", "Dokument")
    document_type = document_meta.get("document_type", "Dokument")

    lines: List[str] = []

    lines.append(f"# RAPORT VERIFIKIMI — {document_type.upper()}")
    lines.append("")
    lines.append(f"**Dokumenti:** {file_name}")
    lines.append(f"**Lloji:** {document_type}")
    lines.append(f"**Data e verifikimit:** {datetime.now(timezone.utc).strftime('%d.%m.%Y %H:%M')}")
    lines.append("")
    lines.append("---")
    lines.append("")

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
    """
    V1.2: Breakdown i plotë — garanton që shuma e kategorive = total.
    """
    lines: List[str] = []

    stats = verification_report.get("stats", {})

    # ─── NENET — V1.2 breakdown i plotë ───
    articles_total = stats.get("articles_total", 0)
    articles_verified = stats.get("articles_verified", 0)
    articles_not_found = stats.get("articles_not_found", 0)
    articles_exist_elsewhere = stats.get("articles_exist_elsewhere", 0)
    articles_in_successor_laws = stats.get("articles_in_successor_laws", 0)
    articles_via_alias = stats.get("articles_via_alias", 0)
    articles_via_treaty = stats.get("articles_via_international_treaty", 0)

    lines.append(f"**Nenet:**")
    lines.append(f"- Gjithsej të nxjerra: {articles_total}")
    lines.append(f"- ✅ Verifikuar direkt në KB: {articles_verified}")
    if articles_via_treaty > 0:
        lines.append(f"  - (nga këto, {articles_via_treaty} janë konventa ndërkombëtare — Neni 22 i Kushtetutës)")
    if articles_via_alias > 0:
        lines.append(f"  - (nga këto, {articles_via_alias} u verifikuan përmes alias-it të akronimit)")
    if articles_in_successor_laws > 0:
        lines.append(f"  - (nga këto, {articles_in_successor_laws} u gjetën në ligjin pasardhës)")
    if articles_exist_elsewhere > 0:
        lines.append(f"- ⚠️ Ekzistojnë në ligje të tjera (hint i gabuar në dokument): {articles_exist_elsewhere}")
    if articles_not_found > 0:
        lines.append(f"- ❌ Nuk u gjetën: {articles_not_found}")
    lines.append("")

    # ─── LIGJET ───
    laws_total = stats.get("laws_total", 0)
    laws_verified = stats.get("laws_verified", 0)
    laws_replaced = stats.get("laws_replaced", 0)
    lines.append(f"**Ligjet:**")
    lines.append(f"- Gjithsej të nxjerra: {laws_total}")
    lines.append(f"- ✅ Verifikuar: {laws_verified}")
    if laws_replaced > 0:
        lines.append(f"- 🔄 Zëvendësuar me version të ri: {laws_replaced}")
    lines.append("")

    # ─── NUMRAT E LËNDËVE ───
    cases_total = stats.get("case_numbers_total", 0)
    cases_cited = stats.get("case_numbers_cited", 0)
    precedents_verified = stats.get("precedents_verified", 0)
    lines.append(f"**Numrat e lëndëve:**")
    lines.append(f"- Gjithsej të nxjerra: {cases_total}")
    lines.append(f"- Të cituar në dokument (jo të vetë dokumentit): {cases_cited}")
    lines.append(f"- Precedentë të verifikuar në KB: {precedents_verified}")
    if cases_cited > 0:
        lines.append(f"  - Të cituar por jo në KB: {cases_cited - precedents_verified}")
    lines.append("")

    # ─── FAKTET ───
    fp_stats = fact_profile.get("stats", {})
    dates_count = fp_stats.get("total_dates", 0)
    deadlines_count = fp_stats.get("legal_deadlines", 0)
    parties_count = fp_stats.get("total_parties", 0)
    suspects_count = fp_stats.get("total_suspects", 0)
    lines.append(f"**Faktet:**")
    lines.append(f"- Data të nxjerra: {dates_count}")
    lines.append(f"- Afate procedurale: {deadlines_count}")
    lines.append(f"- Palë: {parties_count}")
    if suspects_count > 0:
        lines.append(f"- Persona të dyshuar (nga strukturat e dokumentit): {suspects_count}")
    lines.append("")

    return lines