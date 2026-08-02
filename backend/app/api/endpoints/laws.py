# FILE: backend/app/api/endpoints/laws.py
# PHOENIX PROTOCOL - LAWS ENDPOINTS V42.0 (RESILIENT MULTI-TIER LAW RESOLVER)

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

def _normalize_hallucinated_title(raw_title: str, article: str) -> str:
    """
    SMART ROUTER: Maps AI legal concepts or shorthand codes to official Kosovo Law designations.
    """
    title_lower = raw_title.lower()
    
    if any(k in title_lower for k in ["penal", "krim", "vjedhj", "mashtrim", "uzurp", "kpk"]):
        return "Kodi Penal"
    if any(k in title_lower for k in ["shoqëri", "tregtar", "lsht", "biznes", "ortak"]):
        return "Shoqëritë Tregtare"
    if any(k in title_lower for k in ["detyrim", "dëm", "pasurim", "kamat", "lmd", "përgjithshëm"]):
        return "Marrëdhëniet e Detyrimeve"
    if any(k in title_lower for k in ["procedur", "kontestim", "siguris", "padi", "lpk"]):
        return "Procedurën Kontestimore"
    if any(k in title_lower for k in ["punë", "kontratë pune", "puna"]):
        return "Punës"
    if any(k in title_lower for k in ["familj", "martes", "divorc"]):
        return "Familjen"
    if any(k in title_lower for k in ["ekzekutiv", "lpe"]):
        return "Procedurën Ekzekutive"
    if any(k in title_lower for k in ["administrativ", "lpa"]):
        return "Procedurën Administrative"

    return raw_title

def _generate_source_info(doc: dict, metadata: dict, original_law_title: str, original_article: str) -> dict:
    confidence_level = metadata.get("confidence", {}).get("level", "HIGH")
    confidence_score = metadata.get("confidence", {}).get("score", 0.95)
    
    return {
        "confidence": {
            "level": confidence_level,
            "label": "E verifikuar",
            "icon": "✅",
            "color": "success",
            "description": "Ky dokument u gjet me saktësi në bazën e njohurive.",
            "score": confidence_score
        },
        "matched_law": doc.get("law_title", original_law_title),
        "matched_article": doc.get("article_number", original_article),
        "source_file": doc.get("source", ""),
        "was_mapped": metadata.get("was_mapped", False),
        "multiple_matches": metadata.get("multiple_matches", False),
        "verification_hint": f"✅ Burimi: {metadata.get('strategy_used', 'exact_match')}",
        "match_count": 1
    }

def find_law_documents(db, raw_law_title: str, raw_article_num: str) -> tuple[List[dict], Dict[str, Any]]:
    mapped_title = _normalize_hallucinated_title(raw_law_title, str(raw_article_num))
    
    clean_title = mapped_title.strip()
    clean_title = re.sub(r'^\s*[\(\[{(](.*?)[\)\]})]\s*$', r'\1', clean_title)
    clean_title = re.sub(r'^[.\d\s]+', '', clean_title)
    clean_title = re.sub(r'^(?:i|e|të|sipas|në|nga|për|per)\s+', '', clean_title, flags=re.I)
    clean_title = clean_title.strip()

    clean_art = str(raw_article_num).replace('Neni', '').replace('neni', '').replace('.', '').strip()
    
    art_variants: List[Any] = [clean_art, f"{clean_art}.", f"Neni {clean_art}", f"NENI {clean_art}", f"{clean_art} ", f" {clean_art}"]
    if clean_art.isdigit():
        art_variants.append(int(clean_art))
    
    metadata = {
        "original_law_title": raw_law_title,
        "mapped_law_title": mapped_title,
        "article_number": raw_article_num,
        "confidence": {"level": "HIGH", "score": 0.95},
        "strategy_used": "exact_match",
        "was_mapped": (mapped_title != raw_law_title),
        "multiple_matches": False
    }

    # ==============================================================
    # TIER 1: Academy & Manuals logic ("Pjesa X")
    # ==============================================================
    if str(raw_article_num).startswith("Pjesa "):
        try:
            chunk_idx = int(raw_article_num.split()[-1]) - 1
            doc = db.legal_knowledge_base.find_one({
                "law_title": {"$regex": f"{re.escape(clean_title)}", "$options": "i"},
                "chunk_index": chunk_idx
            })
            if doc:
                metadata["strategy_used"] = "academy_match"
                return [doc], metadata
        except Exception:
            pass

    # ==============================================================
    # TIER 2: Match by Title Regex + Article Number
    # ==============================================================
    if clean_title:
        query = {
            "law_title": {"$regex": re.escape(clean_title), "$options": "i"},
            "article_number": {"$in": art_variants}
        }
        docs = list(db.legal_knowledge_base.find(query).sort("chunk_index", 1))
        if docs:
            return docs, metadata

        # Try raw title prefix regex
        raw_clean = re.escape(raw_law_title.strip()[:30])
        if raw_clean:
            query_raw = {
                "law_title": {"$regex": raw_clean, "$options": "i"},
                "article_number": {"$in": art_variants}
            }
            docs = list(db.legal_knowledge_base.find(query_raw).sort("chunk_index", 1))
            if docs:
                metadata["confidence"] = {"level": "HIGH", "score": 0.90}
                return docs, metadata

    # ==============================================================
    # TIER 3: Global Search across ALL Laws by Article Number + Relevance Rank
    # ==============================================================
    if clean_art:
        query_global_art = {"article_number": {"$in": art_variants}}
        global_docs = list(db.legal_knowledge_base.find(query_global_art))
        
        if global_docs:
            keywords = [w.lower() for w in re.findall(r'\w+', raw_law_title) if len(w) > 3]
            scored_docs = []
            for d in global_docs:
                text_content = (str(d.get("law_title", "")) + " " + str(d.get("text", ""))).lower()
                score = sum(1 for kw in keywords if kw in text_content)
                scored_docs.append((score, d))
            
            scored_docs.sort(key=lambda x: x[0], reverse=True)
            best_doc = scored_docs[0][1]
            
            matched_law = best_doc.get("law_title", "")
            all_chunks = list(db.legal_knowledge_base.find({
                "law_title": matched_law,
                "article_number": {"$in": art_variants}
            }).sort("chunk_index", 1))
            
            metadata["confidence"] = {"level": "MEDIUM", "score": 0.75}
            metadata["strategy_used"] = "global_article_match"
            return all_chunks if all_chunks else [best_doc], metadata

    # ==============================================================
    # TIER 4: Semantic / Vector Store Search Fallback
    # ==============================================================
    try:
        search_query = f"{raw_law_title} Neni {raw_article_num}"
        vector_results = vector_store_service.query_global_knowledge_base(search_query, n_results=3)
        if vector_results and isinstance(vector_results, list) and len(vector_results) > 0:
            top_res = vector_results[0]
            if top_res:
                doc_obj = {
                    "law_title": top_res.get("law_title") or top_res.get("metadata", {}).get("law_title") or raw_law_title,
                    "article_number": top_res.get("article_number") or top_res.get("metadata", {}).get("article_number") or raw_article_num,
                    "text": top_res.get("text") or top_res.get("document", ""),
                    "source": top_res.get("source") or top_res.get("metadata", {}).get("source", "")
                }
                metadata["confidence"] = {"level": "MEDIUM", "score": 0.65}
                metadata["strategy_used"] = "vector_semantic_search"
                return [doc_obj], metadata
    except Exception as vec_err:
        logger.warning(f"Vector search fallback skipped in laws endpoint: {vec_err}")

    # ==============================================================
    # TIER 5: Fallback - Search by just law_title
    # ==============================================================
    if clean_title:
        query = {"law_title": {"$regex": re.escape(clean_title), "$options": "i"}}
        docs = list(db.legal_knowledge_base.find(query).sort("chunk_index", 1).limit(3))
        if docs:
            metadata["confidence"] = {"level": "LOW", "score": 0.40}
            metadata["strategy_used"] = "fallback_general_title"
            return docs, metadata

    # ==============================================================
    # TIER 6: Safe Text Body Regex Fallback
    # ==============================================================
    try:
        safe_regex = re.escape(clean_art if clean_art else raw_law_title[:30])
        text_cursor = db.legal_knowledge_base.find(
            {"text": {"$regex": f"Neni\\s+{safe_regex}", "$options": "i"}}
        ).limit(1)
        docs = list(text_cursor)
        if docs:
            metadata["confidence"] = {"level": "LOW", "score": 0.30}
            metadata["strategy_used"] = "fallback_text_regex"
            return docs, metadata
    except Exception as e:
        logger.warning(f"Regex text fallback skipped safely: {e}")

    return [], metadata

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
        
        mapped_title = _normalize_hallucinated_title(law_title, "")
        clean_mapped = re.escape(mapped_title.strip())
        
        query = {"law_title": {"$regex": clean_mapped, "$options": "i"}}
        cursor = db.legal_knowledge_base.find(query, {"law_title": 1, "article_number": 1, "source": 1, "chunk_index": 1, "page": 1})
        docs = list(cursor)

        if not docs:
            words = [re.escape(w) for w in re.findall(r'\w+', law_title) if len(w) > 3]
            if words:
                keyword_regex = "|".join(words[:3])
                query_kw = {"law_title": {"$regex": keyword_regex, "$options": "i"}}
                docs = list(db.legal_knowledge_base.find(query_kw, {"law_title": 1, "article_number": 1, "source": 1, "chunk_index": 1, "page": 1}).limit(100))

        if not docs:
            raise HTTPException(status_code=404, detail="Ligji nuk u gjet")
        
        canonical_title = docs[0].get("law_title", mapped_title)
        source_filename = str(docs[0].get("source", "")).upper()
        is_academy = "AKADEMIA" in source_filename or "KOMMENTAR" in source_filename or "DORACAK" in source_filename

        if is_academy:
            sorted_articles = [f"Pjesa {i+1}" for i in range(len(docs))]
        else:
            articles: Set[str] = {str(d.get("article_number")) for d in docs if d.get("article_number") and str(d.get("article_number")) != ""}
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
        
        docs, metadata = find_law_documents(db, law_title, article_number)
        
        if not docs or not docs[0]: 
            raise HTTPException(status_code=404, detail=f"Dokumenti ({law_title}, Neni {article_number}) nuk u gjet në bazën e të dhënave.")

        source_info = _generate_source_info(docs[0], metadata, law_title, article_number)

        return {
            "law_title": docs[0].get("law_title", metadata["mapped_law_title"]),
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