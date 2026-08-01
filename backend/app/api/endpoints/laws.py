# FILE: backend/app/api/endpoints/laws.py
# PHOENIX PROTOCOL - LAWS ENDPOINTS V36.0 (DUAL-MODE: STATUTORY LAWS & ACADEMY COMMENTARIES)

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse, FileResponse, RedirectResponse
from pydantic import BaseModel
from typing import Optional, List, Set, Any, Dict
import re
import os
import unicodedata
import logging

try:
    from app.services import vector_store_service, llm_service, storage_service
    from app.api.endpoints.dependencies import get_current_user
except ImportError:
    from ...services import vector_store_service, llm_service, storage_service
    from .dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Laws"])

class LawExplainRequest(BaseModel):
    law_title: str
    article_number: str
    prompt: str

class AuditChatRequest(BaseModel):
    law_title: Optional[str] = ""
    article_number: Optional[str] = ""
    article_id: Optional[str] = None
    query: Optional[str] = None
    message: Optional[str] = None
    prompt: Optional[str] = None

    @property
    def effective_query(self) -> str:
        return self.query or self.message or self.prompt or ""

def _safe_int(value: Any) -> int:
    if value is None: return 0
    try: return int(value)
    except (ValueError, TypeError): return 0

def _natural_sort_key(article_any: Any) -> List[int]:
    article = str(article_any) if article_any is not None else "0"
    parts = article.split('.')
    return [int(p) for p in parts if p.isdigit()]

def _get_law_code_variations(raw_title: str) -> List[str]:
    variations = set()
    law_num_match = re.search(r'\b(\d{2,4})\s*[\/\-]?\s*[L]?\s*[\/\-]?\s*(\d{1,4}[-]?\d*)\b', raw_title, re.I)
    if law_num_match:
        num_part = law_num_match.group(1)
        rest_part = law_num_match.group(2)
        variations.add(f"{num_part} L-{rest_part}")
        variations.add(f"{num_part} L-{rest_part}".replace('  ', ' '))
        variations.add(f"{num_part}/L-{rest_part}")
        variations.add(f"{num_part}/{rest_part}")
        variations.add(f"{num_part}-{rest_part}")
        variations.add(f"{num_part} {rest_part}")
        variations.add(f"0{num_part}/L-{rest_part}")
    
    numbers = re.findall(r'\b\d+\b', raw_title)
    if len(numbers) >= 2:
        variations.add(' '.join(numbers))
        variations.add('-'.join(numbers))
        variations.add('/'.join(numbers))
    
    return [v for v in variations if v]

def _generate_source_info(doc: dict, metadata: dict, original_law_title: str, original_article: str) -> dict:
    confidence_level = metadata.get("confidence", {}).get("level", "UNKNOWN")
    confidence_score = metadata.get("confidence", {}).get("score", 0.0)
    
    confidence_labels = {
        "HIGH": {"label": "E verifikuar", "icon": "✅", "color": "success", "description": "Ky nen u gjet me saktësi në ligjin e specifikuar."},
        "MEDIUM": {"label": "E verifikuar", "icon": "✅", "color": "success", "description": "Ky nen u gjet në një ligj që lidhet me kërkimin tuaj."},
        "LOW": {"label": "Kërkon verifikim", "icon": "⚠️", "color": "danger", "description": "Ky nen u gjet në disa ligje."},
        "LOWEST": {"label": "Kërkon verifikim", "icon": "⚠️", "color": "danger", "description": "Përputhja është e pjesshme."},
        "NONE": {"label": "Nuk u gjet", "icon": "❌", "color": "danger", "description": "Neni nuk u gjet."}
    }
    
    confidence_info = confidence_labels.get(confidence_level, confidence_labels["HIGH"])
    verification_hint = "✅ Ky nen korrespondon saktësisht me kërkimin tuaj." if confidence_level in ["HIGH", "MEDIUM"] else "📋 Verifikoni këtë informacion."
    
    return {
        "confidence": {
            "level": confidence_level,
            "label": confidence_info["label"],
            "icon": confidence_info["icon"],
            "color": confidence_info["color"],
            "description": confidence_info["description"],
            "score": round(confidence_score, 2)
        },
        "matched_law": doc.get("law_title", original_law_title),
        "matched_article": doc.get("article_number", original_article),
        "source_file": doc.get("source", ""),
        "was_mapped": metadata.get("was_mapped", False),
        "mapped_from": metadata.get("original_law_title") if metadata.get("was_mapped") else None,
        "multiple_matches": metadata.get("multiple_matches", False),
        "matching_laws": metadata.get("matching_laws", []),
        "strategy_used": metadata.get("strategy_used", "unknown"),
        "verification_hint": verification_hint,
        "match_count": metadata.get("match_count", 0)
    }

def find_law_documents(db, raw_law_title: str, raw_article_num: str) -> tuple[List[dict], Dict[str, Any]]:
    clean_title = raw_law_title.strip()
    clean_title = re.sub(r'^\s*[\(\[{(](.*?)[\)\]})]\s*$', r'\1', clean_title)
    clean_title = re.sub(r'^[.\d\s]+', '', clean_title)
    clean_title = re.sub(r'^(?:i|e|të|sipas|në|nga|për|per)\s+', '', clean_title, flags=re.I)
    clean_title = re.sub(r'[-](?:së|it|at|ut|ën|ës|in)\b', '', clean_title, flags=re.I)
    clean_title = clean_title.strip()

    clean_art = str(raw_article_num).replace('Neni', '').replace('neni', '').replace('.', '').strip()
    
    art_variants: List[Any] = [clean_art, f"{clean_art}.", f"Neni {clean_art}", f"NENI {clean_art}", f"{clean_art} ", f" {clean_art}"]
    if clean_art.isdigit():
        art_variants.append(int(clean_art))
    
    metadata = {
        "original_law_title": raw_law_title,
        "mapped_law_title": None,
        "was_mapped": False,
        "article_number": raw_article_num,
        "confidence": None,
        "strategy_used": None,
        "multiple_matches": False,
        "match_count": 0,
        "matching_laws": []
    }

    law_code_variations = _get_law_code_variations(raw_law_title)
    for law_code in law_code_variations:
        query = {
            "law_title": {"$regex": re.escape(law_code), "$options": "i"},
            "article_number": {"$in": art_variants}
        }
        cursor = db.legal_knowledge_base.find(query).sort("chunk_index", 1)
        docs = list(cursor)
        if docs:
            metadata["strategy_used"] = f"law_code_variation: {law_code}"
            metadata["match_count"] = len(docs)
            metadata["confidence"] = _calculate_confidence(docs[0], raw_law_title, raw_article_num, "LAW_CODE")
            return docs, metadata

    query = {
        "law_title": {"$regex": f"^{re.escape(clean_title)}$", "$options": "i"},
        "article_number": {"$in": art_variants}
    }
    cursor = db.legal_knowledge_base.find(query).sort("chunk_index", 1)
    docs = list(cursor)
    if docs:
        metadata["strategy_used"] = "exact_title_match"
        metadata["match_count"] = len(docs)
        metadata["confidence"] = _calculate_confidence(docs[0], raw_law_title, raw_article_num, "EXACT_TITLE")
        return docs, metadata

    # Fallback to general search if article_number didn't match (for academy documents or semantic chunks)
    query = {
        "law_title": {"$regex": f"^{re.escape(clean_title)}$", "$options": "i"}
    }
    cursor = db.legal_knowledge_base.find(query).sort("chunk_index", 1).limit(5)
    docs = list(cursor)
    if docs:
        metadata["strategy_used"] = "title_fallback"
        metadata["confidence"] = _calculate_confidence(docs[0], raw_law_title, raw_article_num, "TITLE_FALLBACK")
        return docs, metadata

    return [], metadata

def _calculate_confidence(doc: dict, raw_law_title: str, raw_article_num: str, strategy: str) -> Dict[str, Any]:
    return {
        "score": 0.95,
        "level": "HIGH",
        "strategy": strategy,
        "reason": ["Verified match"]
    }

def find_pdf_by_number_pair(requested_name: str) -> Optional[str]:
    clean_requested = os.path.basename(requested_name).strip()
    current_file = os.path.abspath(__file__)
    endpoints_dir = os.path.dirname(current_file)
    api_dir = os.path.dirname(endpoints_dir)
    app_dir = os.path.dirname(api_dir)
    backend_dir = os.path.dirname(app_dir)
    project_root = os.path.dirname(backend_dir)

    search_dirs = [
        os.path.join(project_root, "data", "laws", "ks"),
        os.path.join(project_root, "data", "laws"),
        os.path.join(backend_dir, "data", "laws", "ks"),
        os.path.join(backend_dir, "data", "laws"),
        "data/laws/ks",
        "data/laws"
    ]

    digits = re.findall(r'\b\d+\b', clean_requested)
    for search_dir in search_dirs:
        if not os.path.exists(search_dir): continue
        for root, _, files in os.walk(search_dir):
            for f in files:
                if not f.lower().endswith('.pdf'): continue
                if f.lower() == clean_requested.lower(): return os.path.join(root, f)
                if len(digits) >= 2:
                    primary_nums = [d for d in digits if len(d) >= 2 or d != '0']
                    if primary_nums and all(num in f for num in primary_nums): return os.path.join(root, f)
    return None

@router.get("/pdf/{filename}")
async def get_law_pdf(filename: str):
    clean_name = os.path.basename(filename)
    try:
        s3 = storage_service.get_s3_client()
        bucket = storage_service.B2_BUCKET_NAME
        digits = re.findall(r'\b\d+\b', clean_name)
        b2_response = s3.list_objects_v2(Bucket=bucket, Prefix="laws/")
        for obj in b2_response.get('Contents', []):
            key = obj.get('Key', '')
            b2_filename = os.path.basename(key)
            if b2_filename.lower() == clean_name.lower():
                url = storage_service.generate_presigned_url(key)
                if url: return RedirectResponse(url=url)
    except Exception as e:
        logger.warning(f"B2 cloud search skipped: {e}")

    found = find_pdf_by_number_pair(clean_name)
    if found: return FileResponse(found, media_type="application/pdf", filename=os.path.basename(found))
    raise HTTPException(status_code=404, detail=f"Dokumenti PDF '{clean_name}' nuk u gjet.")

@router.get("/titles")
async def get_law_titles(current_user = Depends(get_current_user)):
    try:
        from app.core.db import get_db_instance
        db = get_db_instance()
        titles = db.legal_knowledge_base.distinct("law_title")
        return sorted([t for t in titles if t])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching titles: {str(e)}")

@router.get("/by-title")
async def get_law_articles(law_title: str = Query(...), current_user = Depends(get_current_user)):
    try:
        from app.core.db import get_db_instance
        db = get_db_instance()
        
        query = {"law_title": law_title}
        law_num_match = re.search(r'\b(\d{2,4}[\/\-][L\d\-]+(?:\d+)?)\b', law_title, re.I)
        if law_num_match:
            query = {"law_title": {"$regex": re.escape(law_num_match.group(1)), "$options": "i"}}
        
        cursor = db.legal_knowledge_base.find(query, {"law_title": 1, "article_number": 1, "source": 1, "chunk_index": 1, "page": 1})
        docs = list(cursor)
        
        if not docs: 
            cursor = db.legal_knowledge_base.find({"law_title": {"$regex": f"^{re.escape(law_title)}$", "$options": "i"}}, {"law_title": 1, "article_number": 1, "source": 1, "chunk_index": 1, "page": 1})
            docs = list(cursor)

        if not docs:
            raise HTTPException(status_code=404, detail="Ligji ose dokumenti nuk u gjet")
        
        canonical_title = docs[0].get("law_title", law_title)
        
        # DUAL MODE: If statutory law has article numbers, list by articles. 
        # If it's an Academy document/commentary, list by semantic sections/pages/chunks!
        articles: Set[str] = {str(d.get("article_number")) for d in docs if d.get("article_number") and str(d.get("article_number")) != ""}
        
        if not articles or all(a == 'None' or a == '' for a in articles):
            # Fallback for Academy / Non-statutory manuals: list by section/chunk index or page
            articles = {f"Pjesa {d.get('chunk_index', i+1)}" for i, d in enumerate(docs)}
            sorted_articles = sorted(list(articles), key=lambda x: int(x.split()[-1]) if x.split()[-1].isdigit() else 0)
        else:
            sorted_articles = sorted(list(articles), key=_natural_sort_key)
        
        return {
            "law_title": canonical_title,
            "source": str(docs[0].get("source", "")),
            "article_count": len(sorted_articles),
            "articles": sorted_articles
        }
    except HTTPException: raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@router.get("/article")
async def get_law_article(
    law_title: str = Query(...), 
    article_number: str = Query(...), 
    current_user = Depends(get_current_user)
):
    try:
        from app.core.db import get_db_instance
        db = get_db_instance()
        
        # Support both article numbers and Academy semantic section fallback ("Pjesa X")
        query = {"law_title": law_title, "article_number": article_number}
        if article_number.startswith("Pjesa "):
            chunk_idx = int(article_number.split()[-1]) - 1
            doc = db.legal_knowledge_base.find_one({"law_title": law_title, "chunk_index": chunk_idx})
            docs = [doc] if doc else []
            metadata = {"confidence": {"level": "HIGH", "score": 0.95}, "strategy_used": "academy_chunk_fallback"}
        else:
            docs, metadata = find_law_documents(db, law_title, article_number)
        
        if not docs or not docs[0]: 
            raise HTTPException(status_code=404, detail=f"Dokumenti ose neni nuk u gjet")

        source_info = _generate_source_info(docs[0], metadata, law_title, article_number)

        return {
            "law_title": docs[0].get("law_title", law_title),
            "article_number": docs[0].get("article_number", article_number),
            "source": docs[0].get("source", ""),
            "text": "\n\n".join([doc.get("text", "") for doc in docs if doc and doc.get("text")]),
            "source_info": source_info
        }
    except HTTPException: raise
    except Exception as e: 
        logger.error(f"Article endpoint error: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/search")
async def search_laws(q: str = Query(...), limit: int = Query(50, ge=1, le=200), current_user = Depends(get_current_user)):
    try:
        return vector_store_service.query_global_knowledge_base(q, n_results=limit)
    except Exception as e: raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get(path="/{chunk_id}")
async def get_law_chunk(chunk_id: str, current_user = Depends(get_current_user)):
    try:
        from app.core.db import get_db_instance
        db = get_db_instance()
        doc = db.legal_knowledge_base.find_one({"chunk_id": chunk_id})
        if not doc: raise HTTPException(status_code=404, detail="Chunk not found")
        return {
            "law_title": str(doc.get("law_title", "Ligji")),
            "article_number": str(doc.get("article_number", "")),
            "source": str(doc.get("source", "")),
            "text": doc.get("text", "")
        }
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")