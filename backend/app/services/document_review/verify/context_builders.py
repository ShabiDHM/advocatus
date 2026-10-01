# FILE: backend/app/services/document_review/verify/context_builders.py
# PHOENIX PROTOCOL - VERIFY CONTEXT BUILDERS V1.3
# V1.3: `_truncate_draft` MAX_CHARS FIX —
#       - Parametri `max_chars` përdorej vetëm në kontrollin `len(doc_text)
#         <= max_chars`, ndërsa slicing përdorte konstantet DRAFT_HEAD_CHARS
#         dhe DRAFT_TAIL_CHARS (45000 / 10000). Nëse dikush thirrte me
#         max_chars < 55000, do prodhonte head+tail > teksti origjinal
#         (dyfishim + omitted negativ). Tani head/tail kufizohen me
#         min(DRAFT_HEAD_CHARS, max_chars) dhe min(DRAFT_TAIL_CHARS,
#         max_chars - head_chars). Sjellja default (max_chars=60000)
#         mbetet IDENTIKE: head=45000, tail=10000.
# V1.2: PROFESSIONAL LANGUAGE (SHQIP në bllokun [PRECEDENTE]).
# V1.1: CASE CONTEXT.
# V1.0: Ekstraktuar nga verify_prompts.py V1.14.

from typing import Any, Dict, List, Optional

from ..constants import MAX_CONTEXT_CHARS
from .prompt_constants import (
    DEFAULT_MAX_DRAFT_CHARS,
    DRAFT_HEAD_CHARS,
    DRAFT_TAIL_CHARS,
    MIN_PRECEDENT_SIMILARITY,
    PRECEDENT_LLM_EXCERPT_CHARS,
)
from .prompt_doc_types import VERIFY_DOC_TYPES
from .prompt_checklists import DOC_TYPE_CHECKLISTS
from .prompt_sections import VERIFY_SECTION_PROMPTS


def _truncate_draft(doc_text: str, max_chars: int = DEFAULT_MAX_DRAFT_CHARS) -> str:
    if not doc_text:
        return ""
    if len(doc_text) <= max_chars:
        return doc_text

    # V1.3: Kufizo head/tail sipas max_chars
    head_chars = min(DRAFT_HEAD_CHARS, max_chars)
    tail_chars = min(DRAFT_TAIL_CHARS, max(0, max_chars - head_chars))

    head = doc_text[:head_chars]
    tail = doc_text[-tail_chars:] if tail_chars > 0 else ""
    omitted = len(doc_text) - head_chars - tail_chars
    return (
        head
        + f"\n\n[...{omitted} karaktere të hequr për gjatësi — kontrollo fundin e draftit...]\n\n"
        + tail
    )


def _block_draft_header(doc_type: str, file_name: str) -> List[str]:
    label = VERIFY_DOC_TYPES.get(doc_type, "Dokument")
    return [
        "=" * 70,
        f"VERIFIKIM DRAFTI — LLOJI: {label}",
        f"FILE: {file_name}",
        "=" * 70,
        "",
        "ℹ️ KY ËSHTË VERIFIKIM I DRAFTIT — JO audit i fashikullit.",
        "Nuk ka kontekst rasti. Vetëm drafti + lloji + precedentët realë.",
        "",
    ]


def _block_draft_text(doc_text: str) -> List[str]:
    if not doc_text or not doc_text.strip():
        return [
            "=" * 70,
            "[DRAFT] TEKSTI I DRAFTIT",
            "=" * 70,
            "",
            "⚠️ Drafti është bosh ose i palexueshëm.",
            "",
        ]

    truncated = _truncate_draft(doc_text)
    was_truncated = len(doc_text) > DEFAULT_MAX_DRAFT_CHARS

    header_lines = [
        "=" * 70,
        f"[DRAFT] TEKSTI I PLOTË I DRAFTIT ({len(truncated)} chars"
        + (f", i truncuar nga {len(doc_text)})" if was_truncated else ")"),
        "=" * 70,
        "",
    ]

    if was_truncated:
        header_lines.extend([
            "⚠️ DRAFT I GJATË — u ruajt koka (45K chars) + fundi (10K chars).",
            "   Kontrollo ME KUJDES të dyja pjesët para se të deklarosh mungesa.",
            "",
        ])

    return header_lines + [truncated, ""]


def _block_case_context(case_profile: Optional[Dict[str, Any]]) -> List[str]:
    if not case_profile or not case_profile.get("has_context"):
        return []
    block = case_profile.get("block") or ""
    if not block.strip():
        return []
    return [block, ""]


def _block_checklist(doc_type: str) -> List[str]:
    checklist = DOC_TYPE_CHECKLISTS.get(doc_type)
    if not checklist:
        return [
            "=" * 70,
            "[CHECKLIST] PJESËT E DETYRUESHME",
            "=" * 70,
            "",
            "⚠️ Nuk ka checklist specifik për këtë lloj dokumenti.",
            "",
        ]

    lines: List[str] = [
        "=" * 70,
        f"[CHECKLIST] PJESËT E DETYRUESHME PËR: {checklist['label']}",
        "=" * 70,
        "",
    ]

    for i, part in enumerate(checklist["required_parts"], 1):
        lines.append(f"  {i}. {part}")

    lines.append("")
    return lines


def _block_cited_articles(
    verification_report: Optional[Dict[str, Any]],
) -> List[str]:
    if not verification_report:
        return [
            "=" * 70,
            "[NENE] NENET E CITUARA NË DRAFT",
            "=" * 70,
            "",
            "⚠️ Nuk ka verifikim të neneve (baza ligjore e paaksesueshme).",
            "",
        ]

    articles = verification_report.get("articles", [])
    if not articles:
        return [
            "=" * 70,
            "[NENE] NENET E CITUARA NË DRAFT",
            "=" * 70,
            "",
            "Nuk u identifikuan nene të cituara në draft.",
            "",
        ]

    lines: List[str] = [
        "=" * 70,
        f"[NENE] NENET E CITUARA ({len(articles)})",
        "=" * 70,
        "",
        "🛑 RREGULL ABSOLUT PËR ATRIBIMIN E LIGJIT:",
        "   * 'Ligji i cituar' POSHTË është i vetmi që mund të atribuohet nenit.",
        "   * NËSE 'Ligji i cituar: -' / bosh → SHKRUAJ 'NUK U VERIFIKUA'.",
        "   * KURRË mos zëvendëso ligjin e cituar me një ligj tjetër në draft.",
        "",
    ]

    for a in articles:
        status = "[OK] EKZISTON" if a.get("exists") else "[X] NUK U GJET"
        law_hint = a.get("law_hint", "") or "-"
        para = f" par. {a['paragraph']}" if a.get("paragraph") else ""
        lines.append(f"* Neni {a.get('article_number', '?')}{para}")
        lines.append(f"  Ligji i cituar: {law_hint}")
        lines.append(f"  Statusi: {status}")
        if a.get("match_reason"):
            lines.append(f"  Arsyeja: {a['match_reason']}")
        if a.get("exists") and a.get("matched_doc"):
            doc = a["matched_doc"]
            lines.append(f"  Ligji në bazë: {doc.get('law_title', '-')}")

        if a.get("alternative_laws"):
            alts = a["alternative_laws"]
            if alts and isinstance(alts[0], dict):
                lines.append(f"  → Ekziston në ligje të tjera:")
                for alt in alts[:5]:
                    lines.append(f"     - {alt.get('law_title', '')[:100]}")
            elif alts and isinstance(alts[0], str):
                lines.append(f"  → Ekziston në ligje të tjera:")
                for alt in alts[:5]:
                    lines.append(f"     - {alt[:100]}")

        if a.get("context"):
            lines.append(f"  Cituar në draft: {a['context'][:MAX_CONTEXT_CHARS]}")
        lines.append("")

    return lines


def _block_precedents(
    precedents: Optional[List[Dict[str, Any]]],
) -> List[str]:
    lines: List[str] = [
        "=" * 70,
        "[PRECEDENTE] REZULTATET NGA BAZA E GJYKATËS SUPREME",
        "=" * 70,
        "",
    ]

    if not precedents:
        lines.extend([
            "Nuk u identifikuan precedentë relevantë në bazën e Gjykatës Supreme për këtë çështje.",
            "",
            "⚠️ SHKRUAJ SAKTËSISHT KËTË FRAZË në raport. MOS shpik precedentë.",
            "",
        ])
        return lines

    filtered = []
    excluded = []
    for p in precedents:
        sim = p.get("similarity")
        try:
            sim_f = float(sim) if sim is not None else 0.0
        except (TypeError, ValueError):
            sim_f = 0.0
        if sim_f >= MIN_PRECEDENT_SIMILARITY:
            filtered.append(p)
        else:
            excluded.append((p.get("case_number", "?"), sim_f))

    if excluded:
        lines.append(
            f"⚠️ U FILTRUAN {len(excluded)} precedentë me ngjashmëri < "
            f"{MIN_PRECEDENT_SIMILARITY:.2f}:"
        )
        for cn, sim in excluded[:5]:
            lines.append(f"     - [{cn}] ngjashmëri={sim:.2f} (i përjashtuar)")
        lines.append("")

    if not filtered:
        lines.extend([
            "Nuk u identifikuan precedentë relevantë në bazën e Gjykatës Supreme për këtë çështje.",
            "",
            "⚠️ SHKRUAJ SAKTËSISHT KËTË FRAZË në raport. MOS shpik precedentë.",
            "",
        ])
        return lines

    lines.append(f"Gjithsej: {len(filtered)} precedentë relevantë të verifikuar.")
    lines.append("")
    lines.append(
        "🛑 BURIMI I DETYRUAR (Rule 19): Çdo precedent i cituar në raport "
        "DUHET të ketë 'Sipas bazës së Gjykatës Supreme'."
    )
    lines.append("")

    for i, p in enumerate(filtered, 1):
        cn = str(p.get("case_number", "?")).strip()
        sim = p.get("similarity", 0.0) or 0.0
        excerpt = (p.get("text_excerpt") or "").strip()
        source = p.get("source", "?")
        page = p.get("page", "?")
        topic = p.get("topic_label")
        rerank = p.get("rerank_score")

        lines.append(f"  {i}. [{cn}] — ngjashmëri={sim:.2f}")
        if rerank is not None:
            lines.append(f"     Pikësimi i renditjes: {rerank:.2f}")
        if topic:
            lines.append(f"     Tema: {topic}")
        if excerpt:
            lines.append(f'     Fragment: "{excerpt[:PRECEDENT_LLM_EXCERPT_CHARS]}"')
        lines.append(f"     Burimi: {source}, faqe {page}")
        lines.append("")

    lines.append("⚠️ RREGULL: Paraqit VETËM këta precedentë. NUK LEJOHET të shpikësh asnjë.")
    lines.append("")
    return lines


def build_verify_context(
    doc_type: str,
    doc_text: str,
    file_name: str,
    section_key: str,
    precedents: Optional[List[Dict[str, Any]]] = None,
    verification_report: Optional[Dict[str, Any]] = None,
    case_profile: Optional[Dict[str, Any]] = None,
) -> str:
    section_cfg = VERIFY_SECTION_PROMPTS.get(section_key)
    needs: List[str] = section_cfg.get("needs", []) if section_cfg else []

    lines: List[str] = []

    lines.extend(_block_draft_header(doc_type, file_name))

    if "draft" in needs:
        lines.extend(_block_draft_text(doc_text))

    if "case_context" in needs:
        lines.extend(_block_case_context(case_profile))

    if "checklist" in needs:
        lines.extend(_block_checklist(doc_type))

    if "articles" in needs:
        lines.extend(_block_cited_articles(verification_report))

    if "precedents" in needs:
        lines.extend(_block_precedents(precedents))

    return "\n".join(lines).strip()


def get_verify_section_keys() -> List[str]:
    from .prompt_constants import VERIFY_SECTION_KEYS
    return list(VERIFY_SECTION_KEYS)


def get_verify_doc_types() -> Dict[str, str]:
    return dict(VERIFY_DOC_TYPES)


def get_checklist(doc_type: str) -> Optional[Dict[str, Any]]:
    return DOC_TYPE_CHECKLISTS.get(doc_type)