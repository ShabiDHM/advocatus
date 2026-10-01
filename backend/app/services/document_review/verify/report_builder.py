# FILE: backend/app/services/document_review/verify/report_builder.py
# PHOENIX PROTOCOL - VERIFY REPORT BUILDER V1.2
# V1.2: SINGLE SOURCE OF TRUTH —
#       - Importet kalojnë nga shimi `..verify_prompts` (backward-compat
#         external për case_analysis_router) në modulet modulare `.prompt_*`.
#         Eliminon rrezikun e divergjencës në një sesion të ardhshëm:
#         çdo ndryshim në modulet modulare aplikohet menjëherë, pa pritur
#         sinkronizim manual me shimin.
#       - `VERIFY_SECTION_PROMPTS[key]["title"]` → `.get("title", key)`.
#         Robustness nëse një section ekziston në `sections` por mungon në
#         `VERIFY_SECTION_PROMPTS` (defensive; nuk ndodh me kod aktual).
# V1.1: VERSION BUMP.
# V1.0: Ekstraktuar nga draft_verifier.py V1.17 (pa ndryshim logjike).

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .config import READINESS_LABELS_SQ
from .prompt_constants import VERIFY_SECTION_KEYS
from .prompt_doc_types import VERIFY_DOC_TYPES
from .prompt_sections import VERIFY_SECTION_PROMPTS


def empty_verify_result(
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


def build_full_report(
    sections: Dict[str, Dict[str, Any]],
    doc_type_label: str,
    file_name: str,
    readiness: str,
) -> str:
    built_at = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M")
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
        # V1.2: .get() fallback për robustness
        title = sec.get("title") or VERIFY_SECTION_PROMPTS.get(key, {}).get("title", key)
        content = sec.get("content") or "_(pa përmbajtje)_"
        lines.append(f"## {title}")
        lines.append("")
        lines.append(content)
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines).strip()