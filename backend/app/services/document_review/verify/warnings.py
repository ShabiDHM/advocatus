# FILE: backend/app/services/document_review/verify/warnings.py
# PHOENIX PROTOCOL - VERIFY WARNINGS V1.0
# Ekstraktuar nga draft_verifier.py V1.17 (pa ndryshim logjike).

from typing import Any, Dict, List


def build_cited_precedents_warning(summary: Dict[str, Any]) -> str:
    total = int(summary.get("total_cited", 0) or 0)
    unverified = summary.get("unverified", []) or []
    verified_count = int(summary.get("verified_count", 0) or 0)

    if total == 0 or not unverified:
        return ""

    lines: List[str] = []
    lines.append("> ⚠️ **PARALAJMËRIM — PRECEDENTË TË CITUAR TË PAVERIFIKUAR**")
    lines.append(">")
    lines.append(
        f"> Dokumenti citon **{total}** numra lëndësh. "
        f"**{verified_count}/{total}** ekzistojnë në bazën e Gjykatës Supreme."
    )
    lines.append(
        f"> **{len(unverified)}** numra NUK u gjetën në bazë — "
        f"nuk mund të konfirmohet vërtetësia e tyre."
    )
    lines.append(">")
    lines.append("> **Numrat e paverifikuar:**")
    for cn in unverified[:20]:
        lines.append(f">   - `{cn}`")
    if len(unverified) > 20:
        lines.append(f">   - ...dhe {len(unverified) - 20} të tjerë.")
    lines.append(">")
    lines.append(
        "> **Veprimi i rekomanduar:** verifikoni manualisht secilin numër "
        "para dorëzimit. Citimi i një lënde inekzistente në një akt "
        "procedural është rrezik i lartë ligjor."
    )
    return "\n".join(lines) + "\n\n---\n\n"


def build_hallucination_warning(hallucination_report: Dict[str, Any]) -> str:
    status = hallucination_report.get("status", "clean")
    if status == "clean":
        return ""

    total = hallucination_report.get("total_issues", 0)
    sev = hallucination_report.get("severity_totals", {}) or {}
    high = sev.get("high", 0)
    medium = sev.get("medium", 0)
    low = sev.get("low", 0)

    suspicious = hallucination_report.get("suspicious_sections", []) or []

    lines: List[str] = []
    lines.append("> ⚠️ **KY RAPORT PËRMBAN DYSHIME PËR HALLUZINACIONE**")
    lines.append(">")
    lines.append(
        f"> Sistemi anti-hallucination identifikoi **{total} vlera** "
        f"që NUK shfaqen në dokumentin origjinal:"
    )
    lines.append(f">   - Rrezik i lartë: **{high}**")
    lines.append(f">   - Rrezik i mesëm: **{medium}**")
    lines.append(f">   - Rrezik i ulët: **{low}**")
    lines.append(">")

    if suspicious:
        lines.append("> **Seksionet me dyshime:**")
        for key in suspicious[:7]:
            per_sec = (hallucination_report.get("per_section") or {}).get(key, {})
            sec_issues = per_sec.get("issues", []) or []
            high_i = sum(1 for i in sec_issues if i.get("severity") == "high")
            med_i = sum(1 for i in sec_issues if i.get("severity") == "medium")
            lines.append(
                f">   - `{key}` — {len(sec_issues)} dyshime "
                f"(high: {high_i}, medium: {med_i})"
            )
        lines.append(">")

    lines.append("> **Veprimi i rekomanduar:** verifikoni manualisht të gjitha")
    lines.append("> vlerat e listuara më sipër përpara se t'i besoni raportit.")

    return "\n".join(lines) + "\n\n---\n\n"