# FILE: backend/app/services/document_review/case_profile.py
# PHOENIX PROTOCOL - CASE PROFILE V1.1
# V1.1: DELETED FILTER + REDUNDANT OR —
#       - Query-t i shtuar `status: {"$ne": "DELETED"}`. Përpara, dokumentet
#         e fshira kontribuonin në dates_set/cases_set/articles_set (vlera
#         të lejuara për anti-hallucination) dhe në bllokun [FASHIKULLI]
#         (kontekst LLM). Konsistencë me albanian_rag_service.py.
#       - Hequr klauzola e tretë OR `{"case_id": str(case_oid)}` — ishte
#         gjithmonë redundant me `{"case_id": case_id}`.
# V1.0: Ndërton profilin e fashikullit.

import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from bson import ObjectId

from .constants import EXTRACTION_COLLECTION
from .citation_extractor import build_citation_profile
from .fact_extractor import build_fact_profile

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# LIMITS (për të mbajtur bllokun nën ~20k chars)
# ═══════════════════════════════════════════════════════════════════════════

MAX_SUBJECTS = 50
MAX_EVIDENCES = 30
MAX_DATES = 40
MAX_ARTICLES = 80
MAX_LAWS = 20
MAX_CASE_NUMBERS = 30
MAX_CROSS_DOC_CONTRADICTIONS = 15
MAX_PER_DOC_TEXT_CHARS = 200_000
MIN_DOC_TEXT_LENGTH = 200


# ═══════════════════════════════════════════════════════════════════════════
# LOAD DOCUMENT TEXT
# ═══════════════════════════════════════════════════════════════════════════

def _load_doc_text(db, case_id: str, doc: Dict[str, Any]) -> str:
    """
    Kthen tekstin e një dokumenti: preferon extraction.text (status=completed),
    pastaj document.content / extracted_text / text.
    """
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
        logger.warning(f"⚠️ [CASE_PROFILE] extraction lookup failed for {doc_id}: {e}")

    for key in ("content", "extracted_text", "text"):
        v = doc.get(key)
        if v and isinstance(v, str):
            return v[:MAX_PER_DOC_TEXT_CHARS] if len(v) > MAX_PER_DOC_TEXT_CHARS else v

    return ""


# ═══════════════════════════════════════════════════════════════════════════
# AGGREGATORS
# ═══════════════════════════════════════════════════════════════════════════

def _aggregate_subjects(profiles: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    seen: Set[str] = set()
    out: List[Dict[str, str]] = []
    for p in profiles:
        file_name = p["file_name"]
        for s in (p["fact"].get("suspects") or []):
            name = str(s.get("name", "")).strip()
            if not name:
                continue
            key = name.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append({
                "name": name,
                "role_hint": str(s.get("position_hint", "")).strip(),
                "source_doc": file_name,
            })
            if len(out) >= MAX_SUBJECTS:
                return out
    return out


def _aggregate_evidences(profiles: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    seen: Set[str] = set()
    out: List[Dict[str, str]] = []
    for p in profiles:
        file_name = p["file_name"]
        fact = p["fact"]

        for t in (fact.get("medical_tests") or []):
            label = f"{t.get('test_type', '?')} ({t.get('result', 'unknown')})"
            key = f"test::{label.lower()}"
            if key in seen:
                continue
            seen.add(key)
            out.append({"type": "medical_test", "label": label, "source_doc": file_name})
            if len(out) >= MAX_EVIDENCES:
                return out

        for f in (fact.get("medical_findings") or []):
            label = f.get("code") or f.get("keyword") or "finding"
            key = f"finding::{str(label).lower()}"
            if key in seen:
                continue
            seen.add(key)
            out.append({"type": "medical_finding", "label": str(label), "source_doc": file_name})
            if len(out) >= MAX_EVIDENCES:
                return out

    return out


def _aggregate_dates(profiles: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    seen: Set[str] = set()
    rows: List[Dict[str, str]] = []
    for p in profiles:
        file_name = p["file_name"]
        for d in (p["fact"].get("dates") or []):
            iso = str(d.get("iso", "")).strip()
            if not iso or iso in seen:
                continue
            seen.add(iso)
            rows.append({
                "iso": iso,
                "display": str(d.get("display", iso)),
                "source_doc": file_name,
            })
    rows.sort(key=lambda r: r["iso"])
    return rows[:MAX_DATES]


def _aggregate_articles(profiles: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    seen: Set[Tuple[str, str]] = set()
    out: List[Dict[str, str]] = []
    for p in profiles:
        file_name = p["file_name"]
        for a in (p["citation"].get("articles") or []):
            num = str(a.get("number", "")).strip()
            law = str(a.get("law_hint", "")).strip()
            if not num:
                continue
            key = (num, law.lower())
            if key in seen:
                continue
            seen.add(key)
            out.append({
                "number": num,
                "paragraph": str(a.get("paragraph", "") or "").strip(),
                "law_hint": law,
                "source_doc": file_name,
            })
            if len(out) >= MAX_ARTICLES:
                return out
    return out


def _aggregate_laws(profiles: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    seen: Set[str] = set()
    out: List[Dict[str, str]] = []
    for p in profiles:
        file_name = p["file_name"]
        for l in (p["citation"].get("laws_by_number") or []):
            num = str(l.get("number", "")).strip()
            if not num or num in seen:
                continue
            seen.add(num)
            out.append({
                "number": num,
                "name": str(l.get("name", "") or "").strip(),
                "source_doc": file_name,
            })
            if len(out) >= MAX_LAWS:
                return out
    return out


def _aggregate_case_numbers(profiles: List[Dict[str, Any]]) -> List[str]:
    seen: Set[str] = set()
    out: List[str] = []
    for p in profiles:
        for cn in (p["citation"].get("cited_case_numbers") or []):
            cn = str(cn).strip()
            if not cn or cn in seen:
                continue
            seen.add(cn)
            out.append(cn)
            if len(out) >= MAX_CASE_NUMBERS:
                return out
    return out


def _find_cross_doc_contradictions(profiles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Gjen kontradikta MIDIS dokumenteve të ndryshme:
      - Të njëjtat (type, unit) por vlera të ndryshme
      - Nga dokumente të ndryshme
    """
    by_key: Dict[Tuple[str, str], Dict[str, Set[str]]] = {}

    for p in profiles:
        file_name = p["file_name"]
        for c in (p["fact"].get("contradictions") or []):
            ctype = str(c.get("type", "")).strip()
            unit = str(c.get("unit", "")).strip()
            if not ctype or not unit:
                continue
            values = c.get("values") or []
            for v in values:
                key = (ctype, unit)
                by_key.setdefault(key, {}).setdefault(str(v), set()).add(file_name)

    out: List[Dict[str, Any]] = []
    for (ctype, unit), values_map in by_key.items():
        if len(values_map) < 2:
            continue
        docs_involved: Set[str] = set()
        for files in values_map.values():
            docs_involved.update(files)
        if len(docs_involved) < 2:
            continue
        out.append({
            "type": ctype,
            "unit": unit,
            "values": sorted(values_map.keys()),
            "docs": sorted(docs_involved),
        })
        if len(out) >= MAX_CROSS_DOC_CONTRADICTIONS:
            break

    return out


# ═══════════════════════════════════════════════════════════════════════════
# BLOCK FORMATTER
# ═══════════════════════════════════════════════════════════════════════════

def _format_block(profile: Dict[str, Any]) -> str:
    lines: List[str] = [
        "=" * 70,
        "[FASHIKULLI] KONTEKSTI I RASTIT (dokumentet e tjera përveç draftit)",
        "=" * 70,
        "",
        "⚠️ Ky është konteksti i fashikullit. Vlerat poshtë janë NGA DOKUMENTET E RASTIT.",
        "   Përdori për konsistencë draft-vs-fashikull. MOS shpik vlera jashtë tyre.",
        "",
    ]

    docs = profile.get("source_documents") or []
    if docs:
        lines.append(f"Dokumente të skanuar: {len(docs)}")
        for d in docs[:10]:
            lines.append(f"  - {d['file_name']} ({d['text_length']} chars)")
        lines.append("")

    subjects = profile.get("subjects") or []
    if subjects:
        lines.append(f"SUBJEKTET (të dyshuar / palë) — {len(subjects)} gjithsej:")
        for s in subjects:
            role = f" — {s['role_hint']}" if s.get("role_hint") else ""
            lines.append(f"  - {s['name']}{role}")
        lines.append("")

    evidences = profile.get("evidences") or []
    if evidences:
        lines.append(f"PROVAT / GJETJET E REFERUARA — {len(evidences)} gjithsej:")
        for e in evidences:
            lines.append(f"  - [{e['type']}] {e['label']}")
        lines.append("")

    dates = profile.get("dates") or []
    if dates:
        lines.append(f"KRONOLOGJIA (datat unike) — {len(dates)} gjithsej:")
        for d in dates:
            lines.append(f"  - {d['display']}")
        lines.append("")

    articles = profile.get("articles") or []
    if articles:
        lines.append(f"NENET E CITUARA NË FASHIKULL — {len(articles)} unike:")
        grouped: Dict[str, List[str]] = {}
        for a in articles:
            law = a.get("law_hint") or "?"
            num = a.get("number", "?")
            para = f" par. {a['paragraph']}" if a.get("paragraph") else ""
            grouped.setdefault(law, []).append(f"{num}{para}")
        for law, nums in grouped.items():
            lines.append(f"  - {law}: {', '.join(nums[:30])}"
                         + ("..." if len(nums) > 30 else ""))
        lines.append("")

    laws = profile.get("laws") or []
    if laws:
        lines.append(f"LIGJET E REFERUARA — {len(laws)} unike:")
        for l in laws:
            name = f" — {l['name'][:80]}" if l.get("name") else ""
            lines.append(f"  - {l['number']}{name}")
        lines.append("")

    cns = profile.get("case_numbers") or []
    if cns:
        lines.append(f"NUMRAT E LËNDËVE TË CITUARA NË FASHIKULL — {len(cns)}:")
        for cn in cns:
            lines.append(f"  - {cn}")
        lines.append("")

    contradictions = profile.get("cross_doc_contradictions") or []
    if contradictions:
        lines.append(f"KONTRADIKTA CROSS-DOKUMENT — {len(contradictions)} të gjetura:")
        for c in contradictions:
            vals = ", ".join(str(v) for v in c.get("values", []))
            docs_str = ", ".join(c.get("docs", []))
            lines.append(f"  - [{c['type']}] {c['unit']}: vlera {vals} (në: {docs_str})")
        lines.append("")

    lines.append("=" * 70)

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# EMPTY PROFILE
# ═══════════════════════════════════════════════════════════════════════════

def _empty_profile() -> Dict[str, Any]:
    return {
        "has_context": False,
        "subjects": [],
        "evidences": [],
        "dates": [],
        "articles": [],
        "laws": [],
        "case_numbers": [],
        "cross_doc_contradictions": [],
        "source_documents": [],
        "stats": {},
        "block": "",
        "dates_set": set(),
        "cases_set": set(),
        "articles_set": set(),
    }


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def build_case_profile(
    db,
    case_id: str,
    exclude_doc_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Ndërton profilin e fashikullit nga të gjitha dokumentet e rastit,
    duke përjashtuar draftin aktual (exclude_doc_id).

    V1.1: Filtron `status != DELETED` (konsistencë me albanian_rag_service).
    """
    if db is None:
        return _empty_profile()

    try:
        case_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id

        # V1.1: DELETED filter + hequr OR redundancy
        docs = list(db.documents.find({
            "$or": [
                {"case_id": case_id},
                {"case_id": case_oid},
            ],
            "status": {"$ne": "DELETED"},
        }))
    except Exception as e:
        logger.warning(f"⚠️ [CASE_PROFILE] Leximi i dokumenteve dështoi: {e}")
        return _empty_profile()

    if not docs:
        logger.info(f"ℹ️ [CASE_PROFILE] Rasti {case_id} nuk ka dokumente.")
        return _empty_profile()

    profiles: List[Dict[str, Any]] = []
    source_docs: List[Dict[str, Any]] = []

    for doc in docs:
        doc_id = str(doc.get("_id", ""))
        if exclude_doc_id and doc_id == str(exclude_doc_id):
            continue

        text = _load_doc_text(db, case_id, doc)
        if not text or len(text) < MIN_DOC_TEXT_LENGTH:
            continue

        try:
            citation = build_citation_profile(text)
            fact = build_fact_profile(
                text,
                source_document=doc.get("file_name", "?"),
            )
        except Exception as e:
            logger.warning(
                f"⚠️ [CASE_PROFILE] Profile build failed for {doc.get('file_name')}: {e}"
            )
            continue

        profiles.append({
            "document_id": doc_id,
            "file_name": doc.get("file_name", "?"),
            "text_length": len(text),
            "citation": citation,
            "fact": fact,
        })
        source_docs.append({
            "document_id": doc_id,
            "file_name": doc.get("file_name", "?"),
            "text_length": len(text),
        })

    if not profiles:
        logger.info(
            f"ℹ️ [CASE_PROFILE] Rasti {case_id}: 0 dokumente të tjera me tekst "
            f"(nga {len(docs)} total, pa draftin aktual)."
        )
        return _empty_profile()

    subjects = _aggregate_subjects(profiles)
    evidences = _aggregate_evidences(profiles)
    dates = _aggregate_dates(profiles)
    articles = _aggregate_articles(profiles)
    laws = _aggregate_laws(profiles)
    case_numbers = _aggregate_case_numbers(profiles)
    cross_doc_contradictions = _find_cross_doc_contradictions(profiles)

    profile: Dict[str, Any] = {
        "has_context": True,
        "subjects": subjects,
        "evidences": evidences,
        "dates": dates,
        "articles": articles,
        "laws": laws,
        "case_numbers": case_numbers,
        "cross_doc_contradictions": cross_doc_contradictions,
        "source_documents": source_docs,
        "stats": {
            "documents_scanned": len(profiles),
            "unique_subjects": len(subjects),
            "unique_evidences": len(evidences),
            "unique_dates": len(dates),
            "unique_articles": len(articles),
            "unique_laws": len(laws),
            "unique_case_numbers": len(case_numbers),
            "cross_doc_contradictions": len(cross_doc_contradictions),
        },
        "dates_set": {d["iso"] for d in dates},
        "cases_set": set(case_numbers),
        "articles_set": {a["number"] for a in articles},
    }

    profile["block"] = _format_block(profile)

    logger.info(
        f"📚 [CASE_PROFILE V1.1] Rasti {case_id}: "
        f"docs={profile['stats']['documents_scanned']}, "
        f"subjects={profile['stats']['unique_subjects']}, "
        f"evidences={profile['stats']['unique_evidences']}, "
        f"dates={profile['stats']['unique_dates']}, "
        f"articles={profile['stats']['unique_articles']}, "
        f"laws={profile['stats']['unique_laws']}, "
        f"cases={profile['stats']['unique_case_numbers']}, "
        f"cross_doc_contradictions={profile['stats']['cross_doc_contradictions']}, "
        f"block_chars={len(profile['block'])}"
    )

    return profile