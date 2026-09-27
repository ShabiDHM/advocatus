# FILE: backend/app/services/rag/block_builders.py
# PHOENIX PROTOCOL - RAG BLOCK BUILDERS V1.3
# V1.3: VERIFIKIM NË GLOBAL KB —
#       - Funksion i ri _batch_check_in_legal_kb: kontrollon nëse një numër
#         lënde ekziston në legal_knowledge_base (një query me $or).
#       - _build_cited_precedents_block tani ndan në DY kategori:
#         1. TË VERIFIKUAR (ekzistojnë në bazën e Gjykatës Supreme)
#         2. VETËM TË CITUAR (nuk ekzistojnë në bazë)
#       - Arsye: kontrolli me scripts/check_precedent.py zbuloi që 7/13
#         precedentë të cituar në kallëzim EKZISTOJNË në legal_knowledge_base.
#         V1.2 i trajtonte të gjithë si "të pabesueshëm".
# V1.2: FORCE-SOURCE REMINDER.
# V1.1: FORCE-FULL SUSPECTS LIST.

import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def _format_alternative_laws(v: Dict[str, Any]) -> str:
    alts = v.get("alternative_laws", [])
    if not alts:
        return ""

    titles: List[str] = []
    for a in alts:
        if isinstance(a, dict):
            t = a.get("law_title") or a.get("title") or ""
            if t:
                titles.append(t)
        else:
            titles.append(str(a))

    if not titles:
        return "(ligje të panjohura)"
    return "; ".join(titles[:5]) + (" ..." if len(titles) > 5 else "")


def _build_contradictions_block(
    internal: List[Dict[str, Any]],
    reported: List[Dict[str, Any]],
) -> str:
    if not internal and not reported:
        return ""

    parts: List[str] = []

    if internal:
        parts.append("\n\n═══════════════════════════════════════════════════════════════════════════")
        parts.append("⚠️ KONTRADIKTA TË BRENDSHME TË DOKUMENTEVE (zbuluar automatikisht)")
        parts.append("═══════════════════════════════════════════════════════════════════════════")
        parts.append("")
        parts.append("⚠️ Këto janë mosputhje FAKTIKE brenda TË NJËJTIT dokument. DUHET PËRMENDUR.")
        parts.append("")
        for c in internal:
            values = " vs ".join(str(v) for v in c.get("values", []))
            src = c.get("_source_file", "?")
            zone = c.get("zone_label", "?")
            parts.append(f"📌 [{src}] {c.get('type', '?')}")
            parts.append(f"   Zona: {zone}")
            parts.append(f"   Vlerat kontradiktore: **{values} {c.get('unit', '')}**")
            for ex in c.get("examples", [])[:3]:
                parts.append(f"   Shembull: {ex[:250]}")
            parts.append("")
        parts.append("⚠️ KËTO JANË FAKTE KRITIKE — DUHET TË PËRMENDEN NË PËRGJIGJE.")

    if reported:
        parts.append("\n\n═══════════════════════════════════════════════════════════════════════════")
        parts.append("ℹ️ KONTRADIKTA TË RAPORTUARA (jo të vetë dokumenteve tona)")
        parts.append("═══════════════════════════════════════════════════════════════════════════")
        parts.append("")
        for c in reported:
            values = " vs ".join(str(v) for v in c.get("values", []))
            src = c.get("_source_file", "?")
            parts.append(f"📌 [{src}] {c.get('type', '?')}")
            parts.append(f"   Vlerat: **{values} {c.get('unit', '')}**")
            parts.append("")

    return "\n".join(parts)


def _build_suspects_block(
    suspects: List[Dict[str, Any]],
) -> str:
    """
    V1.1: Ndërton bllokun e personave të identifikuar për system_prompt.
    """
    if not suspects:
        return ""

    total = len(suspects)

    parts: List[str] = []
    parts.append("\n\n═══════════════════════════════════════════════════════════════════════════")
    parts.append(f"👥 PERSONA TË IDENTIFIKUAR NË DOKUMENTE ({total} TOTAL)")
    parts.append("═══════════════════════════════════════════════════════════════════════════")
    parts.append("")
    parts.append(f"🛑 LISTA E PLOTË PËRMBAN **{total} PERSONA** — NUMËROJI DHE LISTOJI TË GJITHË.")
    parts.append(f"🛑 KUR PYETET 'Kush janë të dyshuarit?', DETYRIMISHT listo TË GJITHË {total}.")
    parts.append(f"🛑 NUK LEJOHET të listosh më pak se {total}. NËSE LISTON VETËM DISA → E GABUAR.")
    parts.append(f"🛑 Fillo përgjigjen me numrin total: '{total} persona'.")
    parts.append("")
    parts.append("⚠️ Kjo listë është nxjerrë automatikisht nga strukturat e dokumenteve")
    parts.append("   (lista të numëruara, GRUPI I/II/III, sektorë të tjerë).")
    parts.append("")

    by_file: Dict[str, List[Dict[str, Any]]] = {}
    for s in suspects:
        src = s.get("_source_file", "?")
        by_file.setdefault(src, []).append(s)

    for src, items in by_file.items():
        parts.append(f"📄 Nga dokumenti: {src} ({len(items)} persona)")
        for s in items:
            name = s.get("name", "?")
            pos = s.get("position_hint", "") or "(pa rol të specifikuar)"
            parts.append(f"   • {name} — {pos[:120]}")
        parts.append("")

    parts.append(f"🛑 KUJTESË: {total} persona gjithsej. Listo TË GJITHË {total} në përgjigje.")
    parts.append("")

    return "\n".join(parts)


# ═══════════════════════════════════════════════════════════════════════════
# V1.3: VERIFIKIM NË GLOBAL KB
# ═══════════════════════════════════════════════════════════════════════════

def _build_tolerant_regex(case_number: str) -> str:
    """
    PML.Nr.185/2025 → PML[\.\s\-/]*Nr[\.\s\-/]*185[\.\s\-/]*2025
    """
    tokens = re.findall(r'[A-Za-z]+|\d+', case_number)
    if not tokens:
        return re.escape(case_number)
    return r'[\.\s\-_/]*'.join(re.escape(t) for t in tokens)


def _normalize_case_number(cn: str) -> str:
    """PML.Nr.185/2025 → PMLNR1852025"""
    if not cn:
        return ""
    return re.sub(r'[\s\.\-_/]+', '', cn.upper())


def _batch_check_in_legal_kb(
    db,
    case_numbers: List[str],
) -> Dict[str, bool]:
    """
    V1.3: Kontrollon nëse numrat ekzistojnë në legal_knowledge_base.
    Bën NJË query me $or për të gjithë numrat — jo N queries.

    Kthen: {case_number: bool}
    """
    if db is None or not case_numbers:
        return {cn: False for cn in case_numbers}

    or_conditions = []
    for cn in case_numbers:
        pattern = _build_tolerant_regex(cn)
        or_conditions.append({"case_number": {"$regex": pattern, "$options": "i"}})
        or_conditions.append({"title": {"$regex": pattern, "$options": "i"}})

    if not or_conditions:
        return {cn: False for cn in case_numbers}

    try:
        docs = list(db.legal_knowledge_base.find(
            {"$or": or_conditions},
            {"_id": 0, "case_number": 1, "title": 1},
        ).limit(500))
    except Exception as e:
        logger.warning(f"[_batch_check_in_legal_kb] Query failed: {e}")
        return {cn: False for cn in case_numbers}

    # Normalizo të dyja palët për krahasim
    results = {cn: False for cn in case_numbers}
    stored_values = []
    for doc in docs:
        for field in ("case_number", "title"):
            v = doc.get(field)
            if v:
                stored_values.append(_normalize_case_number(v))

    stored_set = set(stored_values)

    for cn in case_numbers:
        if _normalize_case_number(cn) in stored_set:
            results[cn] = True

    return results


def _build_cited_precedents_block(
    db_documents: List[Dict[str, Any]],
    db=None,
) -> str:
    """
    V1.3: Ndan precedentët e cituar në dy kategori:

    1. ✅ TË VERIFIKUAR — ekzistojnë në legal_knowledge_base
       LLM-ja mund t'i citojë: "Sipas bazës së Gjykatës Supreme: ..."

    2. ⚠️ VETËM TË CITUAR — nuk ekzistojnë në bazë
       LLM-ja duhet: "Sipas [file_name]: ..."
    """
    from app.services.document_review.citation_extractor import extract_case_numbers

    if not db_documents:
        return ""

    cited_by_doc: Dict[str, List[str]] = {}
    all_cited: List[str] = []
    for doc in db_documents:
        text = doc.get("content") or doc.get("extracted_text") or doc.get("text") or ""
        if not text.strip():
            continue
        fname = doc.get("file_name") or doc.get("title") or "?"
        cases = extract_case_numbers(text)
        cited = [c["case_number"] for c in cases if not c.get("is_likely_own")]
        if cited:
            cited_by_doc[fname] = cited
            all_cited.extend(cited)

    if not cited_by_doc:
        return ""

    # V1.3: Verifiko në DB
    verification = _batch_check_in_legal_kb(db, all_cited) if db is not None else {}

    verified_by_doc: Dict[str, List[str]] = {}
    unverified_by_doc: Dict[str, List[str]] = {}
    for fname, cases in cited_by_doc.items():
        for cn in cases:
            if verification.get(cn, False):
                verified_by_doc.setdefault(fname, []).append(cn)
            else:
                unverified_by_doc.setdefault(fname, []).append(cn)

    total_verified = sum(len(v) for v in verified_by_doc.values())
    total_unverified = sum(len(v) for v in unverified_by_doc.values())

    logger.info(
        f"[CITED_PRECEDENTS V1.3] Total: {len(all_cited)} | "
        f"Verified in KB: {total_verified} | "
        f"Only cited: {total_unverified}"
    )

    parts: List[str] = [
        "\n\n═══════════════════════════════════════════════════════════════════════════",
        "📚 PRECEDENTË TË CITUAR NË DOKUMENTET E FASHIKULLIT",
        "═══════════════════════════════════════════════════════════════════════════",
        "",
    ]

    # ─── SEKSIONI 1: TË VERIFIKUAR NË BAZË ───
    if verified_by_doc:
        parts.append(f"✅ TË VERIFIKUAR NË BAZËN E GJYKATËS SUPREME ({total_verified}):")
        parts.append("")
        parts.append("🛑 KUR CITON këta precedentë, forma e saktë:")
        parts.append("   → \"Sipas bazës së Gjykatës Supreme: Në vendimin PML.Nr.X/YYYY, ...\"")
        parts.append("   ✅ Këto janë verifikuar në bazën zyrtare — mund t'i citosh drejtpërdrejt.")
        parts.append("")
        for fname, cases in verified_by_doc.items():
            parts.append(f"   📄 {fname}:")
            for cn in cases:
                parts.append(f"      • {cn}")
            parts.append("")

    # ─── SEKSIONI 2: VETËM TË CITUAR ───
    if unverified_by_doc:
        parts.append(f"\n⚠️ VETËM TË CITUAR — NUK EKZISTOJNË NË BAZË ({total_unverified}):")
        parts.append("")
        parts.append("🛑 KUR CITON këta, DUHET të deklarosh burimin (Rule 19):")
        parts.append("   → \"Sipas [emri_i_dokumentit]: Në vendimin X, Gjykata Supreme ...\"")
        parts.append("   ❌ NUK LEJOHET: \"Gjykata Supreme thotë...\" pa specifikuar burimin.")
        parts.append("   ⚠️ Këta NUK u verifikuan në bazën zyrtare. Vijnë vetëm nga dokumentet e fashikullit.")
        parts.append("")
        for fname, cases in unverified_by_doc.items():
            parts.append(f"   📄 {fname}:")
            for cn in cases:
                parts.append(f"      • {cn}")
            parts.append("")

    return "\n".join(parts)