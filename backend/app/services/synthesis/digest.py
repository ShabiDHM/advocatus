# FILE: backend/app/services/synthesis/digest.py
# PHOENIX PROTOCOL - DIGEST BUILDER V1.0
# Ekstraktuar nga synthesis_service.py V3.8 — ZERO ndryshim funksional.

import re
from typing import Any, Dict, List, Optional

from .constants import MAX_DIGEST_CHARS


# ═══════════════════════════════════════════════════════════════════════════
# PUBLIC — build digest
# ═══════════════════════════════════════════════════════════════════════════

def build_digest(
    case: Dict[str, Any],
    extractions: List[Dict[str, Any]],
    xrefs: Dict[str, Any],
    defendants_groups: List[Dict[str, Any]],
    articles_by_law: Dict[str, Dict[str, str]],
    case_type: Optional[str] = None,
    verified_citations: Optional[Dict[str, Any]] = None,
) -> str:
    lines: List[str] = []

    lines.append("=" * 70)
    lines.append("TË DHËNAT E LËNDËS")
    lines.append("=" * 70)
    lines.append(f"Titulli: {case.get('title') or case.get('case_name') or 'N/A'}")
    lines.append(f"Klienti: {case.get('client_name') or 'N/A'}")
    lines.append(f"Numri i dokumenteve: {len(extractions)}")
    lines.append("")

    if verified_citations:
        _append_verified_citations(lines, verified_citations)

    if case_type:
        lines.append("=" * 70)
        lines.append("🎯 LLOJI I LËNDËS")
        lines.append("=" * 70)
        lines.append(f"**{case_type}**")
        if "→" in case_type:
            lines.append(
                "Ky është një rast i DYFISHTË që ka evoluar nga "
                "procedura civile (urdhër mbrojtjeje) në procedurë penale."
            )
        lines.append("")

    primary_doc = find_primary_document(extractions)
    if primary_doc:
        lines.append("=" * 70)
        lines.append(f"📄 DOKUMENTI KRYESOR: {primary_doc.get('file_name', 'N/A')}")
        lines.append("=" * 70)
        lines.append("")

    lines.append("=" * 70)
    lines.append("INDEKSI I DOKUMENTEVE")
    lines.append("=" * 70)
    for i, ext in enumerate(extractions, 1):
        marker = " ⭐ [KRYESOR]" if ext is primary_doc else ""
        lines.append(
            f"{i}. {ext.get('file_name', 'N/A')} "
            f"[{ext.get('document_type', 'N/A')}] "
            f"({ext.get('text_length', 0):,} chars){marker}"
        )
    lines.append("")

    if defendants_groups:
        _append_defendants_groups(lines, defendants_groups)

    _append_parties_excluding_defendants(lines, extractions, defendants_groups)

    if articles_by_law:
        _append_articles_by_law(lines, articles_by_law)

    sc_decisions = extract_supreme_court_decisions(extractions)
    if sc_decisions:
        lines.append("=" * 70)
        lines.append("🏛️ AKTGJYKIMET E GJYKATËS SUPREME")
        lines.append("=" * 70)
        for d in sc_decisions:
            lines.append(f"  • {d}")
        lines.append("")

    if xrefs:
        _append_cross_references(lines, xrefs)

    digest = "\n".join(lines)

    if len(digest) > MAX_DIGEST_CHARS:
        digest = digest[:MAX_DIGEST_CHARS] + "\n\n[...digest truncated...]"

    return digest


# ═══════════════════════════════════════════════════════════════════════════
# VERIFIED CITATIONS BLOCK
# ═══════════════════════════════════════════════════════════════════════════

def _append_verified_citations(
    lines: List[str],
    verified_citations: Dict[str, Any],
) -> None:
    lines.append("=" * 70)
    lines.append("🔒 CITIMET E VËRTETUARA NGA DOKUMENTET (REGEX EXTRACTION)")
    lines.append("=" * 70)
    lines.append(
        "⚠️ KY ËSHTË BURIMI I VETËM I SË VËRTETËS. "
        "NUK LEJOHET TË SHPIKËSH LIGJE APO NENE QË NUK SHFAQEN KËTU."
    )
    lines.append("")

    lines.append(f"LIGJET E CITUARA ({verified_citations['total_laws']}):")
    if verified_citations["laws"]:
        for law in verified_citations["laws"]:
            lines.append(f"  • {law}")
    else:
        lines.append("  (asnjë ligj i cituar në dokumente)")
    lines.append("")

    lines.append(f"NENET E CITUARA ({verified_citations['total_articles']}):")
    if verified_citations["articles"]:
        shown = set()
        for art in verified_citations["articles"][:60]:
            par = f", par. {art['paragraph']}" if art.get("paragraph") else ""
            doc_name = art.get("doc_name", "")
            key = f"{art['number']}{par}"
            if key in shown:
                continue
            shown.add(key)
            lines.append(f"  • Neni {art['number']}{par}  [në: {doc_name}]")
    else:
        lines.append("  (asnjë nen i cituar në dokumente)")
    lines.append("")

    if verified_citations.get("article_law_pairs"):
        lines.append(f"ÇIFTET E VËRTETA (Neni X i Ligji) ({verified_citations['total_pairs']}):")
        for art, law in verified_citations["article_law_pairs"][:60]:
            lines.append(f"  • Neni {art} i {law}")
        lines.append("")

    lines.append(
        "⚠️ RREGULL ABSOLUT: Përdor VETËM ligjet dhe nenet e mësipërme. "
        "ÇDO ligj/nen që nuk është në këtë listë KONSIDEROHET HALUDINACION."
    )
    lines.append("")


# ═══════════════════════════════════════════════════════════════════════════
# APPENDERS
# ═══════════════════════════════════════════════════════════════════════════

def _append_articles_by_law(
    lines: List[str],
    articles_by_law: Dict[str, Dict[str, str]],
) -> None:
    total = sum(len(v) for v in articles_by_law.values())

    lines.append("=" * 70)
    lines.append("📖 KONTEKSTI I NENEVE NË DOKUMENTE (JO PËRSHKRIME ZYRTARE)")
    lines.append("=" * 70)
    lines.append(
        f"Ky seksion përmban {total} nene me KONTEKST DOKUMENTI (jo përshkrime zyrtare)."
    )
    lines.append(
        "⚠️ KONTEKSTI ËSHTË JOZYRTAR. NËSE citon në raport → shkruaj "
        "VETËM 'Neni X i [Ligjit]' PA përshkrim."
    )
    lines.append("")

    for law_name in sorted(articles_by_law.keys()):
        articles = articles_by_law[law_name]
        if not articles:
            continue
        lines.append(f"**{law_name}:**")
        for article_key in sorted(articles.keys()):
            desc = articles[article_key]
            if desc:
                lines.append(f"  • {article_key} — [KONTEKST DOKUMENTI: {desc}]")
            else:
                lines.append(f"  • {article_key} (pa kontekst)")
        lines.append("")


def _append_parties_excluding_defendants(
    lines: List[str],
    extractions: List[Dict[str, Any]],
    defendants_groups: List[Dict[str, Any]],
) -> None:
    defendant_names = set()
    for group in defendants_groups:
        for d in group.get("defendants", []):
            name = (d.get("name") or "").strip().lower()
            if name:
                defendant_names.add(name)

    parties_raw: Dict[str, str] = {}
    for ext in extractions:
        ebt = ext.get("entities_by_type", {})
        for item in ebt.get("PARTY", []):
            text = (item.get("text") or "").strip()
            if not text:
                continue
            key = text.lower()
            if key not in parties_raw:
                parties_raw[key] = text

    filtered = [v for k, v in parties_raw.items() if k not in defendant_names]

    if filtered:
        lines.append("=" * 70)
        lines.append("👥 PALËT NDËRGYQËSE")
        lines.append("=" * 70)
        for p in sorted(filtered):
            lines.append(f"  • {p}")
        lines.append("")


def _append_defendants_groups(
    lines: List[str],
    defendants_groups: List[Dict[str, Any]],
) -> None:
    total = sum(len(g.get("defendants", [])) for g in defendants_groups)

    lines.append("=" * 70)
    lines.append("⚖️ GRUPET E TË PANDËHURVE")
    lines.append("=" * 70)
    lines.append(f"Total: {total} të pandehur në {len(defendants_groups)} grupe.")
    lines.append("")

    for group in defendants_groups:
        group_key = group.get("group", "?")
        title = group.get("title", "")
        lines.append(f"GRUPI {group_key}: {title}")
        for d in group.get("defendants", []):
            num = d.get("number", "")
            name = d.get("name", "")
            role = d.get("role", "")
            lines.append(f"  {num}. {name} — {role}")
        lines.append("")


def _append_cross_references(lines: List[str], xrefs: Dict[str, Any]) -> None:
    lines.append("=" * 70)
    lines.append("LIDHJET MIDIS DOKUMENTEVE")
    lines.append("=" * 70)
    doc_refs = xrefs.get("document_references", [])
    if doc_refs:
        for ref in doc_refs[:20]:
            lines.append(
                f"  • '{ref.get('source_file_name')}' → "
                f"'{ref.get('target_file_name')}'"
            )
    lines.append("")


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def find_primary_document(
    extractions: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    priorities = [
        ("kallëzim", "kallzim"),
        ("aktakuzë", "aktakuze"),
        ("padi", "kërkesëpadi"),
        ("aktgjykim", "aktvendim"),
    ]
    for keywords in priorities:
        for ext in extractions:
            doc_type = (ext.get("document_type") or "").lower()
            if any(kw in doc_type for kw in keywords):
                return ext
    if extractions:
        return max(extractions, key=lambda e: e.get("text_length", 0))
    return None


def extract_supreme_court_decisions(
    extractions: List[Dict[str, Any]],
) -> List[str]:
    decisions = set()
    for ext in extractions:
        ebt = ext.get("entities_by_type", {})
        for item in ebt.get("CASE_NUMBER", []):
            text = (item.get("text") or "").strip()
            if not text:
                continue
            if re.match(r'^(PML|Rev)\.?\s*[Nn]r', text, re.IGNORECASE):
                decisions.add(text)
    return sorted(decisions)