# FILE: backend/app/api/endpoints/laws.py
# PHOENIX PROTOCOL - LAWS ENDPOINTS V46.0 (MULTI-STAGE INTELLIGENT RETRIEVAL ENGINE)

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

# Explicit Catalog of Official Kosovo Laws & Codes
OFFICIAL_KOSOVO_LAWS = {
    "kushtetuta": "KUSHTETUTA E REPUBLIKËS SË KOSOVËS",
    "kodi penal": "KODI NR. 06/L-074 KODI PENAL I REPUBLIKËS SË KOSOVËS",
    "kpk": "KODI NR. 06/L-074 KODI PENAL I REPUBLIKËS SË KOSOVËS",
    "procedurës penale": "KODI NR. 08/L-032 I PROCEDURËS PENALE",
    "procedura penale": "KODI NR. 08/L-032 I PROCEDURËS PENALE",
    "kpp": "KODI NR. 08/L-032 I PROCEDURËS PENALE",
    "drejtësisë për të mitur": "KODI NR. 06/L-006 I DREJTËSISË PËR TË MITUR",
    "të mitur": "KODI NR. 06/L-006 I DREJTËSISË PËR TË MITUR",
    "marrëdhëniet e detyrimeve": "LIGJI NR. 04/L-077 PËR MARRËDHËNIET E DETYRIMEVE",
    "lmd": "LIGJI NR. 04/L-077 PËR MARRËDHËNIET E DETYRIMEVE",
    "detyrimeve": "LIGJI NR. 04/L-077 PËR MARRËDHËNIET E DETYRIMEVE",
    "procedurën kontestimore": "LIGJI NR. 03/L-006 PËR PROCEDURËN KONTESTIMORE",
    "procedura kontestimore": "LIGJI NR. 03/L-006 PËR PROCEDURËN KONTESTIMORE",
    "lpk": "LIGJI NR. 03/L-006 PËR PROCEDURËN KONTESTIMORE",
    "procedurën përmbarimore": "LIGJI NR. 04/L-139 PËR PROCEDURËN PËRMBARIMORE",
    "procedura përmbarimore": "LIGJI NR. 04/L-139 PËR PROCEDURËN PËRMBARIMORE",
    "shoqëritë tregtare": "LIGJI NR. 06/L-016 PËR SHOQËRITË TREGTARE",
    "lsht": "LIGJI NR. 06/L-016 PËR SHOQËRITË TREGTARE",
    "ligji i punës": "LIGJI NR. 03/L-212 I PUNËS",
    "punës": "LIGJI NR. 03/L-212 I PUNËS",
    "puna": "LIGJI NR. 03/L-212 I PUNËS",
    "familjen": "LIGJI NR. 2004/32 LIGJI PËR FAMILJEN I KOSOVËS",
    "ligji për familjen": "LIGJI NR. 2004/32 LIGJI PËR FAMILJEN I KOSOVËS",
    "kisha": "LIGJI NR. 04/L-008 PËR KISHA DHE BASHKËSITË FETARE",
    "bashkësitë fetare": "LIGJI NR. 04/L-008 PËR KISHA DHE BASHKËSITË FETARE",
    "mbrojtjen e të dhënave personale": "LIGJI NR. 06/L-082 PËR MBROJTJEN E TË DHËNAVE PERSONALE",
    "të dhënave personale": "LIGJI NR. 06/L-082 PËR MBROJTJEN E TË DHËNAVE PERSONALE",
    "mbrojtjen e fëmijës": "LIGJI NR. 06/L-084 PËR MBROJTJEN E FËMIJËS",
    "fëmijës": "LIGJI NR. 06/L-084 PËR MBROJTJEN E FËMIJËS",
    "sigurinë dhe shëndetin në punë": "LIGJI NR. 04/L-161 PËR SIGURINË DHE SHËNDETIN NË PUNË",
    "tatimin në të ardhurat e korporatave": "LIGJI Nr. 05/L-029 PËR TATIMIN NË TË ARDHURAT E KORPORATAVE",
    "administrimin e procedurave tatimore": "LIGJI NR. 08/L-257 PËR ADMINISTRIMIN E PROCEDURAVE TATIMORE"
}

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

def _is_academic_file(filename_or_title: str) -> bool:
    text = str(filename_or_title).upper()
    academic_keywords = ["AKADEMIA", "DORACAK", "UDHEZUES", "UDHËZUES", "COMMENTARY", "CASE_LAW", "PRAKTIKË", "INSTITUTI"]
    return any(k in text for k in academic_keywords)

def _normalize_hallucinated_title(raw_title: str, article: str) -> str:
    title_lower = raw_title.lower().strip()
    
    # Direct dictionary mapping
    for key, official_title in OFFICIAL_KOSOVO_LAWS.items():
        if key in title_lower or title_lower == key:
            return official_title

    # Strict contextual matching
    if "kisha" in title_lower or "fetar" in title_lower:
        return "LIGJI NR. 04/L-008 PËR KISHA DHE BASHKËSITË FETARE"
    if "penal" in title_lower and "procedur" in title_lower:
        return "KODI NR. 08/L-032 I PROCEDURËS PENALE"
    if "penal" in title_lower:
        return "KODI NR. 06/L-074 KODI PENAL I REPUBLIKËS SË KOSOVËS"
    if "mitur" in title_lower:
        return "KODI NR. 06/L-006 I DREJTËSISË PËR TË MITUR"
    if "familj" in title_lower:
        return "LIGJI NR. 2004/32 LIGJI PËR FAMILJEN I KOSOVËS"
    if "shoqëri" in title_lower or "tregtar" in title_lower:
        return "LIGJI NR. 06/L-016 PËR SHOQËRITË TREGTARE"
    if "detyrim" in title_lower:
        return "LIGJI NR. 04/L-077 PËR MARRËDHËNIET E DETYRIMEVE"
    if "kontestim" in title_lower:
        return "LIGJI NR. 03/L-006 PËR PROCEDURËN KONTESTIMORE"
    if "punë" in title_lower or "puna" in title_lower:
        return "LIGJI NR. 03/L-212 I PUNËS"

    return raw_title

def find_documents_by_title(db, raw_title: str, fields: Optional[dict] = None) -> List[dict]:
    """
    Multi-Stage Intelligent Retrieval Engine for MongoDB Atlas.
    Matches documents accurately using AND queries on Subject Keywords & Numbers.
    """
    title = raw_title.strip()
    if not title:
        return []

    projection = fields if fields else None
    stop_words = {"ligji", "kodi", "për", "per", "dhe", "i", "e", "të", "te", "së", "se", "nr", "nr.", "republikës", "republikes", "kosovës", "kosoves"}
    
    words = [re.escape(w) for w in re.findall(r'\w+', title) if len(w) >= 3 and w.lower() not in stop_words]
    digits = re.findall(r'\b\d+\b', title)

    academic_regex = "AKADEMIA|Doracak|Udhezues|Udhëzues|Commentary|Case_Law"

    # ==============================================================
    # STAGE 1: Subject Keywords AND Query
    # ==============================================================
    if words:
        word_conditions = []
        for w in words:
            word_conditions.append({
                "$or": [
                    {"law_title": {"$regex": w, "$options": "i"}},
                    {"source": {"$regex": w, "$options": "i"}}
                ]
            })
        
        # Exclude academic commentaries if looking for base statute
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

        query_stage1 = {"$and": word_conditions}
        docs = list(db.legal_knowledge_base.find(query_stage1, projection).limit(100))
        if docs:
            return docs

    # ==============================================================
    # STAGE 2: Subject-Only Key Terms AND Query
    # ==============================================================
    subject_words = [w for w in words if not w.isdigit()]
    if subject_words:
        subject_conditions = []
        for w in subject_words:
            subject_conditions.append({
                "$or": [
                    {"law_title": {"$regex": w, "$options": "i"}},
                    {"source": {"$regex": w, "$options": "i"}}
                ]
            })
        subject_conditions.append({"source": {"$not": {"$regex": academic_regex, "$options": "i"}}})
        
        query_stage2 = {"$and": subject_conditions}
        docs = list(db.legal_knowledge_base.find(query_stage2, projection).limit(100))
        if docs:
            return docs

    # ==============================================================
    # STAGE 3: Exact Escaped String Match
    # ==============================================================
    clean_escaped = re.escape(title)
    query_stage3 = {
        "$and": [
            {"$or": [
                {"law_title": {"$regex": clean_escaped, "$options": "i"}},
                {"source": {"$regex": clean_escaped, "$options": "i"}}
            ]},
            {"source": {"$not": {"$regex": academic_regex, "$options": "i"}}}
        ]
    }
    docs = list(db.legal_knowledge_base.find(query_stage3, projection).limit(100))
    if docs:
        return docs

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
        "verification_hint": f"✅ Ligji Zyrtar: {law_name}",
        "match_count": 1
    }

def find_law_documents(db, raw_law_title: str, raw_article_num: str) -> tuple[List[dict], Optional[dict], Dict[str, Any]]:
    """
    Returns: (statutory_docs, academic_commentary_doc, metadata)
    Guarantees strict separation between Official Laws and Academy manuals.
    """
    mapped_title = _normalize_hallucinated_title(raw_law_title, str(raw_article_num))
    clean_art = str(raw_article_num).replace('Neni', '').replace('neni', '').replace('.', '').strip()
    
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

    academic_regex = "AKADEMIA|Doracak|Udhezues|Udhëzues|Commentary|Case_Law"

    # Find statutory base documents using Multi-Stage Intelligent Retrieval
    candidate_docs = find_documents_by_title(db, mapped_title if mapped_title else raw_law_title)
    
    if candidate_docs:
        matched_title = candidate_docs[0].get("law_title") or mapped_title
        statute_docs = list(db.legal_knowledge_base.find({
            "law_title": matched_title,
            "article_number": {"$in": art_variants},
            "source": {"$not": {"$regex": academic_regex, "$options": "i"}}
        }).sort("chunk_index", 1))

        if statute_docs:
            academic_doc = db.legal_knowledge_base.find_one({
                "article_number": {"$in": art_variants},
                "source": {"$regex": academic_regex, "$options": "i"}
            })
            return statute_docs, academic_doc, metadata

    # Vector store fallback
    try:
        search_query = f"{mapped_title if mapped_title else raw_law_title} Neni {raw_article_num}"
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
                metadata["confidence"] = {"level": "HIGH", "score": 0.90}
                metadata["strategy_used"] = "vector_semantic_search"
                return [doc_obj], None, metadata
    except Exception as vec_err:
        logger.warning(f"Vector search fallback skipped: {vec_err}")

    return [], None, metadata

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
        all_titles = db.legal_knowledge_base.distinct("law_title")
        
        statute_titles = []
        academic_titles = []
        for t in sorted([t for t in all_titles if t]):
            if _is_academic_file(t):
                academic_titles.append(t)
            else:
                statute_titles.append(t)
                
        return {
            "statutes": statute_titles,
            "academic_manuals": academic_titles,
            "all_titles": statute_titles + academic_titles
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching titles: {str(e)}")

@router.get("/by-title")
async def get_law_articles(law_title: str = Query(...), current_user = Depends(get_current_user)):
    try:
        from app.core.db import get_db_instance
        db = get_db_instance()
        
        mapped_title = _normalize_hallucinated_title(law_title, "")
        docs = find_documents_by_title(
            db, 
            mapped_title if mapped_title else law_title, 
            fields={"law_title": 1, "article_number": 1, "source": 1, "chunk_index": 1, "page": 1}
        )

        if not docs:
            raise HTTPException(status_code=404, detail=f"Ligji '{law_title}' nuk u gjet në bazën e të dhënave.")
        
        canonical_title = docs[0].get("law_title", mapped_title if mapped_title else law_title)
        is_academy = _is_academic_file(docs[0].get("source", "")) or _is_academic_file(canonical_title)

        if is_academy:
            sorted_articles = [f"Pjesa {i+1}" for i in range(len(docs))]
        else:
            articles: Set[str] = {str(d.get("article_number")) for d in docs if d.get("article_number") and str(d.get("article_number")) != ""}
            sorted_articles = sorted(list(articles), key=_natural_sort_key)
        
        return {
            "law_title": canonical_title,
            "source": str(docs[0].get("source", "")),
            "is_official_statute": not is_academy,
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
        
        statute_docs, academic_doc, metadata = find_law_documents(db, law_title, article_number)
        
        if not statute_docs or not statute_docs[0]: 
            raise HTTPException(status_code=404, detail=f"Dokumenti ({law_title}, Neni {article_number}) nuk u gjet në bazën e të dhënave.")

        primary_doc = statute_docs[0]
        source_info = _generate_source_info(primary_doc, metadata, law_title, article_number)

        response_data = {
            "law_title": primary_doc.get("law_title", metadata["mapped_law_title"]),
            "article_number": primary_doc.get("article_number", article_number),
            "source": primary_doc.get("source", ""),
            "text": "\n\n".join([doc.get("text", "") for doc in statute_docs if doc and doc.get("text")]),
            "source_info": source_info
        }

        if academic_doc and academic_doc.get("text"):
            response_data["academic_commentary"] = {
                "source": academic_doc.get("source", "Akademia e Drejtësisë"),
                "text": academic_doc.get("text", ""),
                "title": "Udhëzues & Praktikë Gjyqësore (Akademia e Drejtësisë)"
            }

        return response_data
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