# FILE: backend/app/services/document_review/draft_verifier.py
# PHOENIX PROTOCOL - DRAFT VERIFIER V1.7
# V1.7: ANTI-HALLUCINATION GATE — shtuar kontroll i automatizuar i halluzinacioneve:
#       - build_fact_profile() ekstrakton datat/afatet/palët/konfliktet.
#       - check_all_sections() verifikon nëse LLM shpiku vlera që nuk
#         shfaqen në draft (nene, ligje, data, numra lëndësh).
#       - Nëse status="suspect": warning banner shtohet në krye të
#         full_report + hallucination_report ruhet në result.
#       - NUK bllokon seksionet (hybrid: Python A + LLM B/C/D; bllokimi
#         do humbte faktet e verifikuara).
# V1.6: PRECEDENT PARSER ROBUST +
#       - Heq çdo A-section nga output-i LLM (parandalon dublikim)
#       - Fallback për PSE_RELEVANT: provon bllok → rreshta numerik → fjalë kyçe
#       - Logger warnings për debug
#       - Nenet që NUK janë në DB (Konventa/KEDNJ) → shfaqen si
#         "Referenca ndërkombëtare" në vend të "Nuk u verifikua"
# V1.5.1: FIX heading i dyfishuar.
# V1.5: HYBRID SECTION 3.
# V1.4: HYBRID SECTION 2.
# V1.3: SCORE.

import os
import re
import time
import logging
import concurrent.futures
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Callable, Tuple, Set

from bson import ObjectId
from bson.errors import InvalidId

from .citation_extractor import build_citation_profile
from .fact_extractor import build_fact_profile
from .mongo_verifier import verify_all
from .streaming import synthesize_section_streaming
from .persistence import load_document, load_extraction
from .hallucination_checker import check_all_sections
from .precedent_search import (
    build_precedent_query,
    search_relevant_precedents,
    PRECEDENT_SIMILARITY_THRESHOLD,
    PRECEDENT_TOP_K,
)
from .verify_prompts import (
    VERIFY_SECTION_PROMPTS,
    VERIFY_SECTION_KEYS,
    VERIFY_DOC_TYPES,
    build_verify_context,
    MIN_PRECEDENT_SIMILARITY,
)

logger = logging.getLogger(__name__)

MAX_CONCURRENT_VERIFY_SECTIONS = int(
    os.getenv("VERIFY_MAX_WORKERS", os.getenv("DOC_REVIEW_MAX_WORKERS", "3"))
)

# V1.7: Flag për të mundësuar/çaktivizuar gate-in (default: ON)
HALLUCINATION_GATE_ENABLED = os.getenv(
    "VERIFY_HALLUCINATION_GATE", "true"
).lower() == "true"

READINESS_LABELS_SQ: Dict[str, str] = {
    "READY":       "GATI",
    "NEEDS WORK":  "KËRKON PUNË",
    "INCOMPLETE":  "I PËRPLOTË",
    "UNKNOWN":     "I PANJOHUR",
}

READINESS_SCORES: Dict[str, int] = {
    "READY":       100,
    "NEEDS WORK":  65,
    "INCOMPLETE":  30,
    "UNKNOWN":     0,
}


# V1.6: Nenet e ligjeve që nuk janë në MongoDB (Konventa, KEDNJ) —
# trajtohen si "Referenca ndërkombëtare" jo si "Nuk u verifikua".
INTERNATIONAL_LAW_KEYWORDS = [
    "konvent",
    "kednj",
    "gjednj",
    "okb",
    "kombet e bashkuara",
    "kombeve te bashkuara",
    "njeriut",
    "femijes",
]


def _is_international_law(law_hint: str) -> bool:
    """V1.6: Kontrollo nëse hint i referohet një ligji ndërkombëtar."""
    if not law_hint:
        return False
    h = law_hint.lower()
    return any(kw in h for kw in INTERNATIONAL_LAW_KEYWORDS)


# ═══════════════════════════════════════════════════════════════════════════
# V1.7: HALLUCINATION GATE HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _build_hallucination_warning(hallucination_report: Dict[str, Any]) -> str:
    """V1.7: Ndërton banner warning për t'u vendosur në krye të full_report."""
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
    lines.append("> ⚠️ **KY RAPORT PËRMban DYSHIME PËR HALLUZINACIONE**")
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


# ═══════════════════════════════════════════════════════════════════════════
# V1.4 + V1.6: HYBRID — PYTHON-GENERATED BLOCK A (NENET E VERIFIKUARA)
# ═══════════════════════════════════════════════════════════════════════════

def _build_verified_articles_block(verification_report: Dict[str, Any]) -> str:
    """
    V1.6: Ndërton bllokun "### A. Nenet e verifikuara" nga MongoDB.
    Ndan:
      - Nenet e verifikuara (në DB)
      - Referencat ndërkombëtare (nuk verifikohen nga DB)
    """
    articles = (verification_report or {}).get("articles", []) or []

    verified = [a for a in articles if a.get("exists")]
    # V1.6: Ndarje e neneve të huaja (Konventa/KEDNJ) nga ato që nuk u gjetën
    international = [
        a for a in articles
        if not a.get("exists") and _is_international_law(a.get("law_hint", ""))
    ]
    missing = [
        a for a in articles
        if not a.get("exists") and not _is_international_law(a.get("law_hint", ""))
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

    # V1.6: Referencat ndërkombëtare — nuk janë "problem", janë thjesht jashtë DB
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

    # V1.6: Vetëm nenet që vërtet mungojnë në DB (jo ndërkombëtare)
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
# V1.5 + V1.6: HYBRID — PYTHON-GENERATED SECTION 3.A (PRECEDENTËT)
# ═══════════════════════════════════════════════════════════════════════════

def _build_precedents_facts_skeleton(
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
    """
    V1.6: Hiq çdo 'A. Precedentët e identifikuar' bllok nga output-i LLM.
    LLM shpesh e shkruan përsëri edhe pse prompt-i e ndalon.
    """
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
    """
    V1.6: Nxjerr 'Pse relevant' për çdo precedent.
    """
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


def _post_process_precedents_section(
    llm_output: str,
    precedents: List[Dict[str, Any]],
) -> str:
    facts_block, count = _build_precedents_facts_skeleton(precedents)

    if count == 0:
        return facts_block

    text = llm_output or ""

    text_clean = _strip_precedent_a_sections(text)

    pse_map = _extract_pse_relevant_map(text, count)
    if not pse_map:
        pse_map = _extract_pse_relevant_map(text_clean, count)

    if not pse_map:
        logger.warning(
            f"⚠️ [V1.7] Nuk u nxorën Pse relevant për {count} precedentë. "
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

def _post_process_section(
    section_key: str,
    llm_content: str,
    verification_report: Dict[str, Any],
    precedents: Optional[List[Dict[str, Any]]] = None,
) -> str:
    if section_key == "legal_quality":
        block_a = _build_verified_articles_block(verification_report)
        return block_a + "\n" + (llm_content or "")

    if section_key == "supporting_precedents":
        return _post_process_precedents_section(
            llm_content or "",
            precedents or [],
        )

    return llm_content or ""


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _empty_verify_result(
    case_id: str,
    document_id: str,
    message: str,
    doc_type: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "case_id": case_id,
        "document_id": document_id,
        "doc_type": doc_type,
        "doc_type_label": VERIFY_DOC_TYPES.get(doc_type, "—") if doc_type else "—",
        "file_name": None,
        "built_at": datetime.now(timezone.utc).isoformat(),
        "sections": {},
        "stats": {
            "sections_generated": 0,
            "sections_total": len(VERIFY_SECTION_KEYS),
            "duration_sec": 0.0,
            "precedents_found": 0,
            "articles_total": 0,
            "articles_verified": 0,
            "execution_mode": "none",
            "formal_pct": 0.0,
            "legal_pct": 0.0,
            "readiness_score": 0,
        },
        "readiness": "UNKNOWN",
        "score": 0,
        "score_breakdown": {"formal": 0.0, "legal": 0.0, "readiness": 0},
        "full_report": f"# Raport Verifikimi\n\n⚠️ {message}\n",
        "status": "error",
        "error_message": message,
    }


def _parse_readiness(sections: Dict[str, Dict[str, Any]]) -> str:
    sec = sections.get("readiness")
    if not sec or not sec.get("content"):
        return "UNKNOWN"

    content_upper = sec["content"].upper()

    if (
        re.search(r'\bINCOMPLETE\b', content_upper)
        or re.search(r'\bI PËRPLOTË\b', content_upper)
        or re.search(r'\bI PERPLOTE\b', content_upper)
    ):
        return "INCOMPLETE"

    if (
        re.search(r'\bNEEDS WORK\b', content_upper)
        or re.search(r'\bNEEDS_WORK\b', content_upper)
        or re.search(r'\bKËRKON PUNË\b', content_upper)
        or re.search(r'\bKERKON PUNE\b', content_upper)
    ):
        return "NEEDS WORK"

    if (
        re.search(r'\bREADY\b', content_upper)
        or re.search(r'\bGATI\b', content_upper)
    ):
        return "READY"

    return "UNKNOWN"


def _extract_formal_pct(sections: Dict[str, Dict[str, Any]]) -> float:
    sec = sections.get("formal_completeness")
    if not sec:
        return 0.0

    content = sec.get("content") or ""

    m = re.search(
        r'(\d+)\s*/\s*(\d+)\s*pjes[ëe]?\s*(?:t[ëe]\s*)?pranishme\s*\(\s*(\d+(?:[.,]\d+)?)\s*%\s*\)',
        content,
        re.IGNORECASE,
    )
    if m:
        try:
            return float(m.group(3).replace(",", "."))
        except ValueError:
            pass

    m2 = re.search(r'\(\s*(\d+(?:[.,]\d+)?)\s*%\s*\)', content)
    if m2:
        try:
            return float(m2.group(1).replace(",", "."))
        except ValueError:
            pass

    return 0.0


def _calculate_score(
    sections: Dict[str, Dict[str, Any]],
    verification_report: Dict[str, Any],
    readiness: str,
) -> Tuple[int, Dict[str, float]]:
    formal_pct = _extract_formal_pct(sections)

    stats = verification_report.get("stats", {}) or {}
    articles_total = int(stats.get("articles_total", 0) or 0)
    articles_verified = int(stats.get("articles_verified", 0) or 0)

    if articles_total > 0:
        legal_pct = (articles_verified / articles_total) * 100.0
    else:
        legal_pct = 70.0

    readiness_pct = float(READINESS_SCORES.get(readiness, 0))

    score = formal_pct * 0.35 + legal_pct * 0.35 + readiness_pct * 0.30
    score_int = int(round(min(100.0, max(0.0, score))))

    breakdown = {
        "formal": round(formal_pct, 1),
        "legal": round(legal_pct, 1),
        "readiness": readiness_pct,
    }

    return score_int, breakdown


def _build_full_report(
    sections: Dict[str, Dict[str, Any]],
    doc_type_label: str,
    file_name: str,
    readiness: str,
) -> str:
    built_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    readiness_sq = READINESS_LABELS_SQ.get(readiness, readiness)

    lines: List[str] = []
    lines.append(f"# RAPORT VERIFIKIMI — {doc_type_label}")
    lines.append("")
    lines.append(f"**Dokumenti:** `{file_name}`  ")
    lines.append(f"**Data:** {built_at}  ")
    lines.append(f"**Gatishmëria:** **{readiness_sq}**")
    lines.append("")
    lines.append("---")
    lines.append("")

    for key in VERIFY_SECTION_KEYS:
        sec = sections.get(key)
        if not sec:
            continue
        title = sec.get("title") or VERIFY_SECTION_PROMPTS[key]["title"]
        content = sec.get("content") or "_(pa përmbajtje)_"
        lines.append(f"## {title}")
        lines.append("")
        lines.append(content)
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines).strip()


def _persist_verification(
    db,
    case_id: str,
    document_id: str,
    verification_entry: Dict[str, Any],
) -> bool:
    try:
        try:
            c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
        except InvalidId:
            c_oid = case_id

        minimal = {
            "doc_type": verification_entry.get("doc_type"),
            "doc_type_label": verification_entry.get("doc_type_label"),
            "file_name": verification_entry.get("file_name"),
            "built_at": verification_entry.get("built_at"),
            "readiness": verification_entry.get("readiness"),
            "score": verification_entry.get("score"),
            "score_breakdown": verification_entry.get("score_breakdown"),
            "full_report": verification_entry.get("full_report"),
            "stats": verification_entry.get("stats"),
            "status": verification_entry.get("status"),
        }

        result = db.cases.update_one(
            {"_id": c_oid},
            {"$set": {
                f"case_document_verifications.{document_id}": minimal,
            }},
            upsert=False,
        )

        if result.matched_count == 0:
            logger.warning(
                f"⚠️ [VERIFY PERSIST] Case nuk u gjet: case={case_id}, doc={document_id}"
            )
            return False

        logger.info(
            f"💾 [VERIFY PERSIST] Ruajtur: case={case_id}, doc={document_id}, "
            f"readiness={minimal['readiness']}, score={minimal['score']}, "
            f"report_chars={len(minimal['full_report'] or '')}"
        )
        return True

    except Exception as e:
        logger.error(f"❌ [VERIFY PERSIST] Dështoi: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════════════
# SERVICE
# ═══════════════════════════════════════════════════════════════════════════

class DraftVerifier:
    def __init__(self, db):
        self.db = db

    def verify(
        self,
        case_id: str,
        document_id: str,
        doc_type: str,
        user_id: Optional[str] = None,
        progress_callback: Optional[Callable] = None,
        section_stream_callback: Optional[Callable[[str, str], None]] = None,
    ) -> Dict[str, Any]:
        start = time.time()

        def _lap(label: str, t_start: float) -> float:
            elapsed = time.time() - t_start
            logger.warning(f"⏱️ [VERIFY TIMING] {label}: {elapsed:.2f}s")
            return elapsed

        if doc_type not in VERIFY_DOC_TYPES:
            msg = (
                f"Lloj dokumenti i panjohur: '{doc_type}'. "
                f"Të lejuara: {sorted(VERIFY_DOC_TYPES.keys())}"
            )
            logger.error(f"❌ [VERIFY] {msg}")
            return _empty_verify_result(case_id, document_id, msg, doc_type)

        doc_type_label = VERIFY_DOC_TYPES[doc_type]

        t0 = time.time()
        try:
            document = load_document(self.db, case_id, document_id)
            extraction = load_extraction(self.db, case_id, document_id)
        except Exception as e:
            logger.error(f"❌ [VERIFY] Load failed: {e}")
            return _empty_verify_result(
                case_id, document_id, f"Gabim gjatë leximit: {e}", doc_type
            )
        _lap("load_document+extraction", t0)

        if not document and not extraction:
            return _empty_verify_result(
                case_id, document_id, "Drafti nuk u gjet në bazë.", doc_type
            )

        doc_text = (
            (extraction or {}).get("text")
            or (document or {}).get("content")
            or (document or {}).get("extracted_text")
            or (document or {}).get("text")
            or ""
        )
        if not doc_text.strip():
            return _empty_verify_result(
                case_id, document_id, "Drafti nuk ka tekst për verifikim.", doc_type
            )

        file_name = (document or {}).get("file_name", "draft")

        logger.info(
            f"🔎 [VERIFY V1.7] Start: case={case_id}, doc={document_id}, "
            f"file={file_name}, doc_type={doc_type} ({doc_type_label}), "
            f"len={len(doc_text)} chars, user={user_id or '?'}, "
            f"parallel x{MAX_CONCURRENT_VERIFY_SECTIONS}, "
            f"hallucination_gate={HALLUCINATION_GATE_ENABLED}"
        )

        if progress_callback:
            try:
                progress_callback("step_started", {
                    "step_key": "extraction",
                    "step_title": "Duke nxjerrë citimet nga drafti...",
                })
            except Exception:
                pass

        t0 = time.time()
        try:
            citation_profile = build_citation_profile(doc_text)
        except Exception as e:
            logger.error(f"❌ [VERIFY] build_citation_profile failed: {e}")
            citation_profile = {"stats": {"total_articles": 0, "total_laws_by_number": 0}}
        _lap("build_citation_profile", t0)

        # V1.7: FACT PROFILE për hallucination check
        t0 = time.time()
        fact_profile: Dict[str, Any] = {}
        if HALLUCINATION_GATE_ENABLED:
            try:
                fact_profile = build_fact_profile(
                    doc_text, source_document=file_name
                )
                logger.info(
                    f"🔬 [VERIFY V1.7] Fact profile: "
                    f"dates={fact_profile.get('stats', {}).get('total_dates', 0)}, "
                    f"parties={fact_profile.get('stats', {}).get('total_parties', 0)}, "
                    f"deadlines={fact_profile.get('stats', {}).get('legal_deadlines', 0)}"
                )
            except Exception as e:
                logger.error(f"❌ [VERIFY] build_fact_profile failed: {e}")
                fact_profile = {}
        _lap("build_fact_profile", t0)

        t0 = time.time()
        try:
            verification_report = verify_all(self.db, citation_profile)
        except Exception as e:
            logger.error(f"❌ [VERIFY] verify_all failed: {e}")
            verification_report = {
                "articles": [],
                "laws_by_number": [],
                "case_numbers": [],
                "stats": {
                    "articles_total": 0, "articles_verified": 0,
                    "laws_total": 0, "laws_verified": 0,
                    "case_numbers_cited": 0, "precedents_verified": 0,
                },
            }
        _lap("verify_all (MongoDB)", t0)

        logger.info(
            f"📚 [VERIFY] Articles {verification_report['stats'].get('articles_verified', 0)}/"
            f"{verification_report['stats'].get('articles_total', 0)}"
        )

        if progress_callback:
            try:
                progress_callback("step_started", {
                    "step_key": "precedents",
                    "step_title": "Duke kërkuar precedentë në Gjykatën Supreme...",
                })
            except Exception:
                pass

        t0 = time.time()
        precedents: List[Dict[str, Any]] = []
        try:
            query = build_precedent_query(
                document_type=doc_type_label,
                file_name=file_name,
                doc_text=doc_text,
                case_type=None,
            )
            precedents = search_relevant_precedents(
                self.db, query,
                top_k=PRECEDENT_TOP_K,
                threshold=PRECEDENT_SIMILARITY_THRESHOLD,
            ) or []
            logger.info(
                f"🏛️ [VERIFY] Precedent search: {len(precedents)} rezultate "
                f"(top_k={PRECEDENT_TOP_K}, threshold={PRECEDENT_SIMILARITY_THRESHOLD})"
            )
        except Exception as e:
            logger.error(f"❌ [VERIFY] Precedent search failed: {e}")
            precedents = []
        _lap("search_relevant_precedents", t0)

        # V1.7: Nxjerr numrat e lëndëve të precedentëve (për extra_allowed_cases)
        found_precedent_cases: Set[str] = set()
        for p in precedents:
            cn = (p.get("case_number") or "").strip()
            if cn:
                found_precedent_cases.add(cn)

        sections: Dict[str, Dict[str, Any]] = {}
        section_stats: Dict[str, Any] = {}
        sections_start = time.time()

        logger.warning(
            f"🚀 [VERIFY PARALLEL V1.7] {len(VERIFY_SECTION_KEYS)} seksione, "
            f"max_workers={MAX_CONCURRENT_VERIFY_SECTIONS}"
        )

        import threading
        _callback_lock = threading.Lock()

        def _emit_progress(event: str, payload: Dict[str, Any]) -> None:
            if not progress_callback:
                return
            with _callback_lock:
                try:
                    progress_callback(event, payload)
                except Exception:
                    pass

        def _emit_section(section_key: str, content: str) -> None:
            if not section_stream_callback or not content:
                return
            with _callback_lock:
                try:
                    section_stream_callback(section_key, content)
                except Exception:
                    pass

        def _run_section(
            section_key: str,
        ) -> Tuple[str, Dict[str, Any], Dict[str, Any]]:
            section_start = time.time()
            section_cfg = VERIFY_SECTION_PROMPTS[section_key]
            section_title = section_cfg["title"]
            section_max_tokens = section_cfg.get("max_tokens", 2500)

            t_ctx = time.time()
            try:
                verified_context = build_verify_context(
                    doc_type=doc_type,
                    doc_text=doc_text,
                    file_name=file_name,
                    section_key=section_key,
                    precedents=precedents if "precedents" in section_cfg.get("needs", []) else None,
                    verification_report=(
                        verification_report
                        if "articles" in section_cfg.get("needs", [])
                        else None
                    ),
                )
            except Exception as e:
                logger.error(f"❌ [VERIFY {section_key}] Context build failed: {e}")
                return (
                    section_key,
                    {"title": section_title, "content": "", "error": f"context_build_failed: {e}"},
                    {"duration_sec": round(time.time() - section_start, 2), "error": str(e)},
                )
            ctx_build_time = time.time() - t_ctx

            logger.warning(
                f"▶️ [VERIFY {section_key}] start "
                f"(max_tokens={section_max_tokens}, ctx={len(verified_context)} chars, "
                f"ctx_build={ctx_build_time*1000:.0f}ms) — {section_title}"
            )

            _emit_progress("section_started", {
                "section_key": section_key,
                "section_title": section_title,
            })

            try:
                raw_llm_content = synthesize_section_streaming(
                    section_key=section_key,
                    section_cfg=section_cfg,
                    verified_context=verified_context,
                    file_name=file_name,
                    document_type=doc_type_label,
                    stream_callback=None,
                )

                content = _post_process_section(
                    section_key=section_key,
                    llm_content=raw_llm_content,
                    verification_report=verification_report,
                    precedents=precedents,
                )

                elapsed = round(time.time() - section_start, 2)

                logger.warning(
                    f"✅ [VERIFY {section_key}] done: {elapsed}s, "
                    f"{len(content)} chars (llm_raw={len(raw_llm_content)}, "
                    f"python_prefix={len(content) - len(raw_llm_content)})"
                )

                return (
                    section_key,
                    {"title": section_title, "content": content},
                    {
                        "duration_sec": elapsed,
                        "content_length": len(content),
                        "llm_raw_length": len(raw_llm_content),
                        "python_prefix_length": len(content) - len(raw_llm_content),
                        "context_chars": len(verified_context),
                        "max_tokens": section_max_tokens,
                    },
                )

            except Exception as e:
                elapsed = round(time.time() - section_start, 2)
                logger.error(f"❌ [VERIFY {section_key}] failed after {elapsed}s: {e}")
                return (
                    section_key,
                    {"title": section_title, "content": "", "error": str(e)},
                    {"duration_sec": elapsed, "error": str(e)},
                )

        try:
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=MAX_CONCURRENT_VERIFY_SECTIONS,
                thread_name_prefix="draft_verify",
            ) as executor:
                futures = {
                    executor.submit(_run_section, k): k
                    for k in VERIFY_SECTION_KEYS
                }
                for fut in concurrent.futures.as_completed(futures):
                    key = futures[fut]
                    try:
                        k, sec_entry, stat_entry = fut.result()
                        sections[k] = sec_entry
                        section_stats[k] = stat_entry
                        if sec_entry.get("content"):
                            _emit_section(k, sec_entry["content"])
                        if not sec_entry.get("error"):
                            _emit_progress("section_completed", {
                                "section_key": k,
                                "section_title": sec_entry["title"],
                                "content_length": stat_entry.get("content_length", 0),
                            })
                    except Exception as e:
                        logger.error(f"❌ [VERIFY PARALLEL] Future failed for {key}: {e}")

        except Exception as e:
            logger.error(f"❌ [VERIFY PARALLEL] ThreadPoolExecutor failed: {e}")
            logger.warning("🔄 [VERIFY] Fallback në sequential mode")
            for section_key in VERIFY_SECTION_KEYS:
                try:
                    k, sec_entry, stat_entry = _run_section(section_key)
                    sections[k] = sec_entry
                    section_stats[k] = stat_entry
                    if sec_entry.get("content"):
                        _emit_section(k, sec_entry["content"])
                except Exception as e2:
                    logger.error(f"❌ [VERIFY SEQUENTIAL] {section_key}: {e2}")

        sections = {k: sections[k] for k in VERIFY_SECTION_KEYS if k in sections}
        section_stats = {k: section_stats[k] for k in VERIFY_SECTION_KEYS if k in section_stats}

        sections_total_time = round(time.time() - sections_start, 2)
        logger.warning(
            f"⏱️ [VERIFY TIMING] sections_total (parallel x{MAX_CONCURRENT_VERIFY_SECTIONS}): "
            f"{sections_total_time}s"
        )

        # ═══════════════════════════════════════════════════════════════════
        # V1.7: ANTI-HALLUCINATION CHECK
        # ═══════════════════════════════════════════════════════════════════
        hallucination_report: Dict[str, Any] = {}
        if HALLUCINATION_GATE_ENABLED and fact_profile:
            if progress_callback:
                try:
                    progress_callback("step_started", {
                        "step_key": "hallucination_check",
                        "step_title": "Duke kontrolluar saktësinë e fakteve...",
                    })
                except Exception:
                    pass

            t0 = time.time()
            try:
                hallucination_report = check_all_sections(
                    sections=sections,
                    citation_profile=citation_profile,
                    fact_profile=fact_profile,
                    verification_report=verification_report,
                    extra_allowed_cases=found_precedent_cases,
                )
                logger.warning(
                    f"🧪 [VERIFY V1.7] Hallucination: "
                    f"status={hallucination_report.get('status')}, "
                    f"issues={hallucination_report.get('total_issues', 0)} "
                    f"(high={hallucination_report.get('severity_totals', {}).get('high', 0)}, "
                    f"medium={hallucination_report.get('severity_totals', {}).get('medium', 0)}, "
                    f"low={hallucination_report.get('severity_totals', {}).get('low', 0)}), "
                    f"suspicious={hallucination_report.get('suspicious_sections', [])}"
                )
            except Exception as e:
                logger.error(f"❌ [VERIFY] check_all_sections failed: {e}")
                hallucination_report = {}
            _lap("hallucination_check", t0)
        elif not HALLUCINATION_GATE_ENABLED:
            logger.info("ℹ️ [VERIFY V1.7] Hallucination gate çaktivizuar (env)")
        elif not fact_profile:
            logger.warning("⚠️ [VERIFY V1.7] Fact profile bosh — halluzinacioni nuk u kontrollua")

        readiness = _parse_readiness(sections)

        score, score_breakdown = _calculate_score(
            sections=sections,
            verification_report=verification_report,
            readiness=readiness,
        )

        full_report = _build_full_report(
            sections=sections,
            doc_type_label=doc_type_label,
            file_name=file_name,
            readiness=readiness,
        )

        # V1.7: Prepend hallucination warning në krye të full_report
        if hallucination_report.get("status") == "suspect":
            warning_banner = _build_hallucination_warning(hallucination_report)
            if warning_banner:
                full_report = warning_banner + full_report

        duration = round(time.time() - start, 2)

        vstats = verification_report.get("stats", {}) or {}
        articles_total = int(vstats.get("articles_total", 0) or 0)
        articles_verified = int(vstats.get("articles_verified", 0) or 0)
        legal_pct = score_breakdown.get("legal", 0.0)
        formal_pct = score_breakdown.get("formal", 0.0)
        readiness_score = int(score_breakdown.get("readiness", 0))

        h_sev = (hallucination_report or {}).get("severity_totals", {}) or {}

        result: Dict[str, Any] = {
            "case_id": case_id,
            "document_id": document_id,
            "doc_type": doc_type,
            "doc_type_label": doc_type_label,
            "file_name": file_name,
            "built_at": datetime.now(timezone.utc).isoformat(),
            "sections": sections,
            "stats": {
                "case_id": case_id,
                "document_id": document_id,
                "doc_type": doc_type,
                "doc_type_label": doc_type_label,
                "file_name": file_name,
                "text_length": len(doc_text),
                "sections_generated": len([s for s in sections.values() if s.get("content")]),
                "sections_total": len(VERIFY_SECTION_KEYS),
                "report_chars": len(full_report),
                "duration_sec": duration,
                "execution_mode": "verify_hybrid_v1.7",
                "precedents_found": len(precedents),
                "precedent_threshold": PRECEDENT_SIMILARITY_THRESHOLD,
                "precedent_top_k": PRECEDENT_TOP_K,
                "articles_total": articles_total,
                "articles_verified": articles_verified,
                "sections_total_sec": sections_total_time,
                "formal_pct": formal_pct,
                "legal_pct": legal_pct,
                "readiness_score": readiness_score,
                # V1.7: Hallucination stats
                "hallucination_status": hallucination_report.get("status", "not_checked"),
                "hallucination_issues": hallucination_report.get("total_issues", 0),
                "hallucination_high": h_sev.get("high", 0),
                "hallucination_medium": h_sev.get("medium", 0),
                "hallucination_low": h_sev.get("low", 0),
                "hallucination_suspicious_sections": hallucination_report.get("suspicious_sections", []),
                "hallucination_enabled": HALLUCINATION_GATE_ENABLED,
            },
            "readiness": readiness,
            "score": score,
            "score_breakdown": score_breakdown,
            "full_report": full_report,
            "section_stats": section_stats,
            "status": "completed",
        }

        # V1.7: Ruaj hallucination_report të plotë për konsum të ardhshëm
        if hallucination_report:
            result["hallucination_report"] = hallucination_report

        t0 = time.time()
        persisted = _persist_verification(
            self.db, case_id, document_id, result
        )
        _lap("persist_verification", t0)

        result["persisted"] = persisted

        logger.info(
            f"✅ [VERIFY V1.7] Complete: "
            f"sections={result['stats']['sections_generated']}/{result['stats']['sections_total']}, "
            f"readiness={readiness}, score={score} "
            f"(formal={formal_pct}%, legal={legal_pct}%, readiness={readiness_score}), "
            f"precedents={len(precedents)}, "
            f"articles={articles_verified}/{articles_total}, "
            f"hallucination={result['stats']['hallucination_status']} "
            f"({result['stats']['hallucination_issues']} issues), "
            f"report_chars={len(full_report)}, duration={duration}s, "
            f"persisted={persisted}"
        )

        return result


def get_draft_verifier(db) -> DraftVerifier:
    return DraftVerifier(db)