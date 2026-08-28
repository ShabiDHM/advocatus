# FILE: backend/app/api/endpoints/laws_pkg/laws_search_service.py
# PHOENIX PROTOCOL - LAWS SEARCH SERVICE V20.0 (REMOVED 100-ARTICLE CAP - FULL EXHAUSTIVE RETRIEVAL)

import re
import os
from typing import List, Optional, Tuple, Dict, Any
from app.api.endpoints.laws_pkg.laws_dictionary import _is_academic_file, _normalize_hallucinated_title, _strip_alpha

MAX_STATUTE_ARTICLES = 3000

def find_documents_by_title(db, raw_title: str, fields: Optional[dict] = None) -> List[dict]:
    title = raw_title.strip()
    if not title:
        return []

    projection = fields if fields else None
    stop_words = {"ligji", "kodi", "për", "per", "dhe", "i", "e", "të", "te", "së", "se", "nr", "nr.", "republikës", "republikes", "kosovës", "kosoves", "web", "pdf"}
    
    words = [re.escape(w) for w in re.findall(r'\w+', title) if len(w) >= 3 and w.lower() not in stop_words]
    digits = re.findall(r'\b\d+\b', title)

    academic_regex = "AKADEMIA|Doracak|Udhezues|Udhëzues|Commentary|Case_Law|LËNDËSH|LENDESH"
    is_acad = _is_academic_file(title)

    if is_acad:
        acad_conditions = []
        for w in words:
            if w.lower() not in ["akademia", "drejt", "drejtësisë"]:
                acad_conditions.append({
                    "$or": [
                        {"law_title": {"$regex": w, "$options": "i"}},
                        {"source": {"$regex": w, "$options": "i"}}
                    ]
                })
        if acad_conditions:
            docs = list(db.legal_knowledge_base.find({"$and": acad_conditions}, projection).limit(MAX_STATUTE_ARTICLES))
            if docs: return docs

        docs = list(db.legal_knowledge_base.find({
            "$or": [
                {"source": {"$regex": "AKADEMIA|Case_Law|Udhezues", "$options": "i"}},
                {"law_title": {"$regex": "AKADEMIA|Case_Law|Udhezues", "$options": "i"}}
            ]
        }, projection).limit(MAX_STATUTE_ARTICLES))
        if docs: return docs

    if words:
        word_conditions = []
        for w in words:
            word_conditions.append({
                "$or": [
                    {"law_title": {"$regex": w, "$options": "i"}},
                    {"source": {"$regex": w, "$options": "i"}}
                ]
            })
        word_conditions.append({"source": {"$not": {"$regex": academic_regex, "$options": "i"}}})

        if digits:
            digit_patterns = [d for d in digits if len(d) >= 2 or d != '0']
            for d in digit_patterns:
                clean_d = str(int(d)) if d.isdigit() else d
                d_regex = f"(?:0*{clean_d}\\b|{d})"
                word_conditions.append({
                    "$or": [
                        {"law_title": {"$regex": d_regex, "$options": "i"}},
                        {"source": {"$regex": d_regex, "$options": "i"}}
                    ]
                })

        docs = list(db.legal_knowledge_base.find({"$and": word_conditions}, projection).limit(MAX_STATUTE_ARTICLES))
        if docs: return docs

    clean_escaped = re.escape(title)
    docs = list(db.legal_knowledge_base.find({
        "$or": [
            {"law_title": {"$regex": clean_escaped, "$options": "i"}},
            {"source": {"$regex": clean_escaped, "$options": "i"}}
        ]
    }, projection).limit(MAX_STATUTE_ARTICLES))
    if docs: return docs

    return []

def _generate_source_info(doc: dict, metadata: dict, original_law_title: str, original_article: str) -> dict:
    confidence_level = metadata.get("confidence", {}).get("level", "HIGH")
    confidence_score = metadata.get("confidence", {}).get("score", 0.98)
    
    law_name = doc.get("law_title", original_law_title)
    is_academic = _is_academic_file(doc.get("source", "")) or _is_academic_file(law_name)

    return {
        "confidence": {
            "level": confidence_level,
            "label": "Tekst Zyrtar i Verifikuar (100%)" if not is_academic else "Udhëzues i Praktikës Gjyqësore",
            "icon": "📜" if not is_academic else "📚",
            "color": "success" if not is_academic else "info",
            "description": "Nen i nxjerrë direkt nga Kodi / Ligji Zyrtar i Kosovës." if not is_academic else "Analizë dhe udhëzues nga Akademia e Drejtësisë.",
            "score": confidence_score
        },
        "matched_law": law_name,
        "matched_article": doc.get("article_number", original_article),
        "source_file": doc.get("source", ""),
        "was_mapped": metadata.get("was_mapped", False),
        "is_official_statute": not is_academic,
        "verification_hint": f"✅ Ligji Zyrtar: {law_name}" if not is_academic else f"📚 Akademia e Drejtësisë: {law_name}",
        "match_count": 1
    }

def find_law_documents(db, raw_law_title: str, raw_article_num: str) -> Tuple[List[dict], Optional[dict], Dict[str, Any]]:
    mapped_title = _normalize_hallucinated_title(raw_law_title, str(raw_article_num))
    is_academic = _is_academic_file(raw_law_title) or _is_academic_file(mapped_title)
    clean_art = str(raw_article_num).replace('Neni', '').replace('neni', '').replace('.', '').strip()
    
    if is_academic:
        case_num_match = re.search(r'\d+', clean_art)
        if case_num_match:
            case_num = case_num_match.group(0)
            case_regex = f"LËNDA\\s+(?:NR\\.\\s*)?{case_num}\\b"
            case_docs = list(db.legal_knowledge_base.find({
                "$or": [
                    {"text": {"$regex": case_regex, "$options": "i"}},
                    {"article_number": {"$regex": f"{case_num}\\b", "$options": "i"}}
                ],
                "source": {"$regex": "AKADEMIA|Case_Law", "$options": "i"}
            }).sort("chunk_index", 1).limit(20))

            if case_docs:
                return case_docs, None, {
                    "original_law_title": raw_law_title,
                    "mapped_law_title": mapped_title,
                    "article_number": f"Lënda Nr. {case_num}",
                    "confidence": {"level": "HIGH", "score": 0.98},
                    "strategy_used": "academic_case_number_match",
                    "was_mapped": False
                }

    art_variants: List[Any] = [clean_art, f"{clean_art}.", f"Neni {clean_art}", f"NENI {clean_art}", f"{clean_art} ", f" {clean_art}"]
    if clean_art.isdigit():
        art_variants.append(int(clean_art))

    metadata = {
        "original_law_title": raw_law_title,
        "mapped_law_title": mapped_title,
        "article_number": raw_article_num,
        "confidence": {"level": "HIGH", "score": 0.98},
        "strategy_used": "exact_statute_match",
        "was_mapped": (mapped_title != raw_law_title)
    }

    academic_regex = "AKADEMIA|Doracak|Udhezues|Udhëzues|Commentary|Case_Law|LËNDËSH|LENDESH"
    candidate_docs = find_documents_by_title(db, mapped_title if mapped_title else raw_law_title)
    
    if candidate_docs:
        matched_title = candidate_docs[0].get("law_title") or mapped_title
        statute_docs = list(db.legal_knowledge_base.find({
            "law_title": matched_title,
            "article_number": {"$in": art_variants}
        }).sort("chunk_index", 1))

        if statute_docs:
            academic_doc = db.legal_knowledge_base.find_one({
                "article_number": {"$in": art_variants},
                "source": {"$regex": academic_regex, "$options": "i"}
            })
            return statute_docs, academic_doc, metadata

    return candidate_docs[:3] if candidate_docs else ([], None, metadata)

def find_pdf_by_number_pair(requested_name: str) -> Optional[str]:
    target_clean = _strip_alpha(requested_name)
    
    current_file = os.path.abspath(__file__)
    endpoints_dir = os.path.dirname(current_file)
    laws_pkg_dir = os.path.dirname(endpoints_dir)
    api_dir = os.path.dirname(laws_pkg_dir)
    app_dir = os.path.dirname(api_dir)
    backend_dir = os.path.dirname(app_dir)
    project_root = os.path.dirname(backend_dir)

    search_dirs = [
        os.path.join(project_root, "data", "laws", "ks"),
        os.path.join(project_root, "data", "academic"),
        os.path.join(project_root, "data", "laws"),
        os.path.join(backend_dir, "data", "laws", "ks"),
        os.path.join(backend_dir, "data", "academic"),
        os.path.join(backend_dir, "data", "laws"),
        "data/laws/ks",
        "data/academic",
        "data/laws"
    ]

    for search_dir in search_dirs:
        if not os.path.exists(search_dir): continue
        for root, _, files in os.walk(search_dir):
            for f in files:
                if not f.lower().endswith('.pdf'): continue
                if _strip_alpha(f) == target_clean:
                    return os.path.join(root, f)

    return None