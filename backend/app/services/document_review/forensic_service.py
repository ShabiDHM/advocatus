# FILE: backend/app/services/document_review/forensic_service.py
# PHOENIX PROTOCOL - FORENSIC SERVICE V1.4
# V1.4: DELETED FILTER + REDUNDANT OR —
#       - Query-t i shtuar `status: {"$ne": "DELETED"}` për konsistencë me
#         case_profile V1.1 / albanian_rag_service. Përpara, dokumentet e
#         fshira kontribuonin në ForensicFlag → konstatime të analizës me
#         gjetje nga dokumente që nuk ekzistojnë më.
#       - Hequr klauzola e tretë OR `{"case_id": str(case_oid)}` — gjithmonë
#         redundant me `{"case_id": case_id}`.
# V1.3: PROFESSIONAL LANGUAGE + TAG FIX —
#       - Tag blloku: "[FLAMUJT_FORENSIK]" → "[KONSTATIMET_E_ANALIZËS]"
#         (përputhet me prompts.py V4.25 / FORENSIC_FINDINGS_RULE).
#       - _SEVERITY_LABEL_SQ: "LARTË" → "E rëndësishme" (përputhet me
#         FORENSIC_FINDINGS_RULE). Title case për të gjitha shkallët.
#       - Të gjitha stringjet në _format_flags_block: "flamuj" → "konstatime".
#       - Logger messages: "flamuj" → "konstatime" (konsistencë).
# V1.2: EXTRACT ALLOWED VALUES (P1 fix).
# V1.1: Filtri MIN_SEVERITY_FOR_BLOCK.
# V1.0: Versioni fillestar.

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from bson import ObjectId

from .constants import EXTRACTION_COLLECTION
from .forensic_extractor import extract_forensic_data, DocumentForensicData
from .forensic_engine import (
    ForensicFlag,
    run_forensic_detectors,
    load_forensic_config,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════

MAX_PER_DOC_TEXT_CHARS = 200_000
MIN_DOC_TEXT_LENGTH = 200
MAX_FLAGS_IN_BLOCK = 40
MAX_EVIDENCE_ITEMS = 3

MIN_SEVERITY_FOR_BLOCK: frozenset = frozenset({"critical", "high"})

_SEVERITY_ORDER = ("critical", "high", "medium", "low")

# V1.3: Label-t përputhen me FORENSIC_FINDINGS_RULE.
_SEVERITY_LABEL_SQ = {
    "critical": "Kritike",
    "high": "E rëndësishme",
    "medium": "Mesme",
    "low": "E ulët",
}


# ═══════════════════════════════════════════════════════════════════════════
# REGEX PËR EKSTRAKTIM VLERASH NGA FLAMUJT (V1.2)
# ═══════════════════════════════════════════════════════════════════════════

_RE_CASE_NUM_IN_TEXT = re.compile(
    r'\b([A-Z]+)\.nr\.\s*(\d+)\s*/\s*(\d{2,4})\b',
    re.UNICODE,
)
_RE_DATE_ISO = re.compile(r'\b(\d{4})-(\d{2})-(\d{2})\b')
_RE_ARTICLE_IN_TEXT = re.compile(r'\bNeni\s+(\d+)\b', re.UNICODE)


# ═══════════════════════════════════════════════════════════════════════════
# RESULT
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ForensicAnalysisResult:
    has_findings: bool = False
    profile_used: str = "generic"
    flags: List[ForensicFlag] = field(default_factory=list)
    documents_scanned: int = 0
    block: str = ""
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "has_findings": self.has_findings,
            "profile_used": self.profile_used,
            "flags": [f.to_dict() for f in self.flags],
            "documents_scanned": self.documents_scanned,
            "block": self.block,
            "stats": self.stats,
        }


# ═══════════════════════════════════════════════════════════════════════════
# V1.2: EXTRACT ALLOWED VALUES (P1 fix)
# ═══════════════════════════════════════════════════════════════════════════

def extract_allowed_values_from_flags(
    flags: List[ForensicFlag],
) -> Dict[str, Set[str]]:
    """
    Nxjerr vlerat që duhen shtuar në extra_allowed_* të hallucination_checker
    për të shmangur false-positives kur LLM citon konstatimet e analizës.

    Kthen:
        {
          "cases": set(),
          "dates": set(),
          "articles": set(),
        }
    """
    cases: Set[str] = set()
    dates: Set[str] = set()
    articles: Set[str] = set()

    for flag in flags:
        # 1. Nga evidence
        for ev in (flag.evidence or []):
            if isinstance(ev, dict):
                if "case_number" in ev:
                    cases.add(str(ev["case_number"]))
                if "date" in ev:
                    dates.add(str(ev["date"]))
                if "value" in ev:
                    v = str(ev["value"])
                    m = re.match(r'^([A-Z]+)\.nr\.(\d+)/(\d{2,4})$', v)
                    if m:
                        y = m.group(3)
                        if len(y) == 2:
                            y = "20" + y
                        cases.add(f"{m.group(1)}.nr.{m.group(2)}/{y}")

        # 2. Nga message — case numbers
        for m in _RE_CASE_NUM_IN_TEXT.finditer(flag.message or ""):
            prefix, num, year = m.group(1), m.group(2), m.group(3)
            if len(year) == 2:
                year = "20" + year
            cases.add(f"{prefix}.nr.{num}/{year}")

        # 3. Nga message — datat ISO
        for m in _RE_DATE_ISO.finditer(flag.message or ""):
            dates.add(f"{m.group(1)}-{m.group(2)}-{m.group(3)}")

        # 4. Nga evidence — dates në formë ISO (listë "files" ose të tjera)
        for ev in (flag.evidence or []):
            if isinstance(ev, dict):
                for k, v in ev.items():
                    if isinstance(v, str):
                        for m in _RE_DATE_ISO.finditer(v):
                            dates.add(f"{m.group(1)}-{m.group(2)}-{m.group(3)}")
                    elif isinstance(v, list):
                        for item in v:
                            if isinstance(item, str):
                                for m in _RE_DATE_ISO.finditer(item):
                                    dates.add(f"{m.group(1)}-{m.group(2)}-{m.group(3)}")

        # 5. Nga legal_basis — nene
        for m in _RE_ARTICLE_IN_TEXT.finditer(flag.legal_basis or ""):
            articles.add(m.group(1))

        # 6. Nga message — nene (p.sh. "Neni 398 KPRK")
        for m in _RE_ARTICLE_IN_TEXT.finditer(flag.message or ""):
            articles.add(m.group(1))

    logger.info(
        f"📤 [FORENSIC V1.4] Allowed values extracted from flags: "
        f"cases={len(cases)}, dates={len(dates)}, articles={len(articles)}"
    )

    return {"cases": cases, "dates": dates, "articles": articles}


# ═══════════════════════════════════════════════════════════════════════════
# LOAD DOCUMENT TEXT
# ═══════════════════════════════════════════════════════════════════════════

def _load_doc_text(db, case_id: str, doc: Dict[str, Any]) -> str:
    doc_id = str(doc.get("_id", ""))
    if not doc_id:
        return ""

    try:
        ext = db[EXTRACTION_COLLECTION].find_one(
            {"case_id": str(case_id), "document_id": doc_id, "status": "completed"},
            {"text": 1},
        )
        if ext and ext.get("text"):
            text = str(ext["text"])
            return text[:MAX_PER_DOC_TEXT_CHARS] if len(text) > MAX_PER_DOC_TEXT_CHARS else text
    except Exception as e:
        logger.warning(f"⚠️ [FORENSIC] extraction lookup failed for {doc_id}: {e}")

    for key in ("content", "extracted_text", "text"):
        v = doc.get(key)
        if v and isinstance(v, str):
            return v[:MAX_PER_DOC_TEXT_CHARS] if len(v) > MAX_PER_DOC_TEXT_CHARS else v

    return ""


# ═══════════════════════════════════════════════════════════════════════════
# PROFILE RESOLUTION
# ═══════════════════════════════════════════════════════════════════════════

def resolve_profile(
    document_type: Optional[str],
    config: Optional[Dict[str, Any]] = None,
) -> str:
    if config is None:
        config = load_forensic_config()

    mapping = config.get("document_type_to_profile") or {}
    default = mapping.get("_default", "generic")

    if not document_type:
        return default

    if document_type in mapping:
        val = mapping[document_type]
        if isinstance(val, str) and not val.startswith("_"):
            return val

    dt_lower = document_type.strip().lower()
    for key, val in mapping.items():
        if key.startswith("_"):
            continue
        if key.lower() == dt_lower:
            return val

    return default


# ═══════════════════════════════════════════════════════════════════════════
# EVIDENCE FORMATTER
# ═══════════════════════════════════════════════════════════════════════════

def _format_evidence_item(ev: Any) -> str:
    if isinstance(ev, dict):
        parts = []
        for k, v in list(ev.items())[:6]:
            if isinstance(v, list):
                v_str = ", ".join(str(x) for x in v[:5])
            else:
                v_str = str(v)
            parts.append(f"{k}={v_str}")
        return "; ".join(parts)
    return str(ev)


# ═══════════════════════════════════════════════════════════════════════════
# BLOCK FORMATTER (V1.3)
# ═══════════════════════════════════════════════════════════════════════════

def _format_flags_block(flags: List[ForensicFlag], profile: str) -> str:
    if not flags:
        return ""

    relevant = [f for f in flags if f.severity in MIN_SEVERITY_FOR_BLOCK]
    if not relevant:
        return ""

    limited_flags = relevant[:MAX_FLAGS_IN_BLOCK]
    truncated = len(relevant) - len(limited_flags)

    lines: List[str] = [
        "=" * 70,
        "[KONSTATIMET_E_ANALIZËS] KONSTATIMET E ANALIZËS SË FASHIKULLIT",
        "=" * 70,
        "",
        f"Profili i detektimit: {profile}",
        f"Total konstatime (kritike + të rëndësishme): {len(relevant)}"
        + (f" (shfaqen {len(limited_flags)})" if truncated else ""),
        f"Total konstatime të rastit (përfshirë mesme/të ulëta): {len(flags)}",
        "",
        "⚠️ Këto janë konstatime të nxjerra nga analiza automatike.",
        "   MOS SHPIK. Cito SAKTËSISHT përmbajtjen dhe burimin.",
        "   Përdor SHQIP për shkallën: Kritike / E rëndësishme / Mesme / E ulët.",
        "",
    ]

    by_severity: Dict[str, List[ForensicFlag]] = {}
    for f in limited_flags:
        by_severity.setdefault(f.severity, []).append(f)

    for sev in _SEVERITY_ORDER:
        bucket = by_severity.get(sev)
        if not bucket:
            continue
        lines.append(f"── {_SEVERITY_LABEL_SQ.get(sev, sev.upper())} ({len(bucket)}) ──")
        for i, flag in enumerate(bucket, 1):
            lines.append(f"  {i}. [{flag.rule_id}] {flag.message}")
            if flag.legal_basis:
                lines.append(f"     Baza ligjore: {flag.legal_basis}")
            if flag.recommended_action:
                lines.append(f"     Veprimi: {flag.recommended_action}")
            for ev in (flag.evidence or [])[:MAX_EVIDENCE_ITEMS]:
                lines.append(f"     • {_format_evidence_item(ev)}")
            lines.append("")
        lines.append("")

    if truncated:
        lines.append(f"...dhe {truncated} konstatime të tjera (të shkurtuara për gjatësi).")
        lines.append("")

    lines.append("=" * 70)
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN API
# ═══════════════════════════════════════════════════════════════════════════

def run_forensic_analysis(
    db,
    case_id: str,
    exclude_doc_id: Optional[str] = None,
    document_type: Optional[str] = None,
    profile_override: Optional[str] = None,
) -> ForensicAnalysisResult:
    if db is None:
        return ForensicAnalysisResult(has_findings=False)

    config = load_forensic_config()
    profile = profile_override or resolve_profile(document_type, config)

    logger.info(
        f"🔬 [FORENSIC V1.4] Rasti {case_id}: profile='{profile}', "
        f"document_type='{document_type or 'N/A'}'"
    )

    try:
        case_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id

        # V1.4: DELETED filter + hequr OR redundancy
        docs = list(db.documents.find({
            "$or": [
                {"case_id": case_id},
                {"case_id": case_oid},
            ],
            "status": {"$ne": "DELETED"},
        }))
    except Exception as e:
        logger.warning(f"⚠️ [FORENSIC] Leximi i dokumenteve dështoi: {e}")
        return ForensicAnalysisResult(has_findings=False, profile_used=profile)

    if not docs:
        logger.info(f"ℹ️ [FORENSIC] Rasti {case_id} nuk ka dokumente.")
        return ForensicAnalysisResult(has_findings=False, profile_used=profile)

    structures: List[DocumentForensicData] = []
    for doc in docs:
        doc_id = str(doc.get("_id", ""))
        if exclude_doc_id and doc_id == str(exclude_doc_id):
            continue

        text = _load_doc_text(db, case_id, doc)
        if not text or len(text) < MIN_DOC_TEXT_LENGTH:
            continue

        try:
            data = extract_forensic_data(text, doc.get("file_name", "?"))
            structures.append(data)
        except Exception as e:
            logger.warning(
                f"⚠️ [FORENSIC] extract failed for {doc.get('file_name')}: {e}"
            )

    if not structures:
        logger.info(
            f"ℹ️ [FORENSIC] 0 dokumente të skanuara për rastin {case_id}."
        )
        return ForensicAnalysisResult(
            has_findings=False,
            profile_used=profile,
            documents_scanned=0,
        )

    try:
        flags = run_forensic_detectors(structures, profile=profile)
    except Exception as e:
        logger.error(f"❌ [FORENSIC] run_forensic_detectors dështoi: {e}")
        return ForensicAnalysisResult(
            has_findings=False,
            profile_used=profile,
            documents_scanned=len(structures),
        )

    block = _format_flags_block(flags, profile) if flags else ""

    stats = {
        "documents_scanned": len(structures),
        "flags_total": len(flags),
        "flags_critical": sum(1 for f in flags if f.severity == "critical"),
        "flags_high": sum(1 for f in flags if f.severity == "high"),
        "flags_medium": sum(1 for f in flags if f.severity == "medium"),
        "flags_low": sum(1 for f in flags if f.severity == "low"),
        "flags_in_block": sum(1 for f in flags if f.severity in MIN_SEVERITY_FOR_BLOCK),
        "block_chars": len(block),
        "profile_used": profile,
    }

    logger.info(
        f"✅ [FORENSIC V1.4] Rasti {case_id}: "
        f"{stats['flags_total']} konstatime "
        f"(critical={stats['flags_critical']}, "
        f"high={stats['flags_high']}, "
        f"medium={stats['flags_medium']}, "
        f"low={stats['flags_low']}), "
        f"in_block={stats['flags_in_block']}, "
        f"block_chars={stats['block_chars']}"
    )

    return ForensicAnalysisResult(
        has_findings=bool(flags),
        profile_used=profile,
        flags=flags,
        documents_scanned=len(structures),
        block=block,
        stats=stats,
    )


def get_forensic_summary(
    db, case_id: str, exclude_doc_id: Optional[str] = None,
    document_type: Optional[str] = None,
) -> Dict[str, Any]:
    result = run_forensic_analysis(
        db, case_id, exclude_doc_id=exclude_doc_id,
        document_type=document_type,
    )
    return result.stats