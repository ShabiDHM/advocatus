# FILE: backend/app/api/endpoints/laws_pkg/laws_query_router.py
# PHOENIX PROTOCOL - LAWS QUERY ROUTER V68.0 (STRICT THREE-TAB DISCOVERY & CASE STARTING PAGE ENDPOINT)

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Set, List
import logging
import os
import re

from app.services import vector_store_service, storage_service
from app.api.endpoints.dependencies import get_current_user
from app.api.endpoints.laws_pkg.laws_dictionary import _normalize_hallucinated_title, _natural_sort_key
from app.api.endpoints.laws_pkg.laws_search_service import find_documents_by_title, find_law_documents, _generate_source_info

logger = logging.getLogger(__name__)
router = APIRouter()

CASE_NO_REGEX = re.compile(r'(REV|PML|PA1|A|CP|PKR|P|KMLP|ANR)\s*\.?\s*NR', re.IGNORECASE)


def _get_b2_filenames(prefix: str) -> List[str]:
    """Helper to list PDF files from a specific Backblaze B2 directory prefix."""
    filenames = []
    try:
        s3 = storage_service.get_s3_client()
        bucket = storage_service.B2_BUCKET_NAME
        b2_response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
        for obj in b2_response.get('Contents', []):
            key = obj.get('Key', '')
            fname = os.path.basename(key)
            if fname and fname.lower().endswith('.pdf'):
                filenames.append(fname)
    except Exception as e:
        logger.warning(f"B2 list failed for prefix '{prefix}': {e}")
    return filenames


@router.get("/case-page")
async def get_case_starting_page(law_title: str = Query(...), current_user = Depends(get_current_user)):
    """Returns the exact starting page number for a selected court decision or statute."""
    try:
        from app.core.db import get_db_instance
        db = get_db_instance()
        clean_title = law_title.strip()

        # Find earliest page number stored in MongoDB for this title
        doc = db.legal_knowledge_base.find_one(
            {"$or": [
                {"law_title": clean_title},
                {"law_title": {"$regex": re.escape(clean_title), "$options": "i"}},
                {"source": {"$regex": re.escape(clean_title), "$options": "i"}}
            ]},
            sort=[("page", 1)]
        )
        if doc and doc.get("page"):
            return {"page": int(doc.get("page")), "law_title": clean_title}
        return {"page": 1, "law_title": clean_title}
    except Exception as e:
        logger.warning(f"Error fetching starting page: {e}")
        return {"page": 1, "law_title": law_title}


@router.get("/titles")
async def get_law_titles(current_user = Depends(get_current_user)):
    try:
        from app.core.db import get_db_instance
        db = get_db_instance()
        
        # 1. TAB 2: ACADEMIA - Query ONLY actual PDF filenames (source + b2_academic)
        academic_db_sources = db.legal_knowledge_base.distinct("source", {"category": "academic"})
        b2_academic = _get_b2_filenames("academic/")
        
        raw_academic_sources = set([
            s.strip() for s in (academic_db_sources + b2_academic) 
            if s and s.strip() and s.lower().endswith('.pdf')
        ])
        clean_academic = sorted(list(raw_academic_sources))

        # 2. TAB 3: CASELAW - Query ONLY category='caselaw' distinct titles
        caselaw_db_titles = db.legal_knowledge_base.distinct("law_title", {"category": "caselaw"})
        caselaw_db_sources = db.legal_knowledge_base.distinct("source", {"category": "caselaw"})
        b2_caselaw = _get_b2_filenames("case_law/")

        raw_caselaw = set([t.strip() for t in (caselaw_db_titles + caselaw_db_sources + b2_caselaw) if t and t.strip()])
        clean_caselaw = sorted(list(raw_caselaw))

        # 3. TAB 1: STATUTES - Query non-academic, non-caselaw items
        all_titles = db.legal_knowledge_base.distinct("law_title", {"category": {"$nin": ["academic", "caselaw"]}})
        all_sources = db.legal_knowledge_base.distinct("source", {"category": {"$nin": ["academic", "caselaw"]}})
        raw_statutes = [t.strip() for t in (all_titles + all_sources) if t and t.strip() and not t.lower().endswith('.pdf')]
        clean_statutes = sorted(list(set(raw_statutes)))

        return {
            "statutes": clean_statutes,
            "academic_manuals": clean_academic,
            "case_law": clean_caselaw,
            "all_titles": sorted(list(set(clean_statutes + clean_academic + clean_caselaw)))
        }
    except Exception as e:
        logger.error(f"Error fetching law titles: {e}")
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
            fields={"law_title": 1, "article_number": 1, "source": 1, "chunk_index": 1, "page": 1, "text": 1}
        )

        if not docs:
            raise HTTPException(status_code=404, detail=f"Ligji '{law_title}' nuk u gjet në bazën e të dhënave.")
        
        canonical_title = docs[0].get("law_title", mapped_title if mapped_title else law_title)

        articles: Set[str] = {str(d.get("article_number")) for d in docs if d.get("article_number") and str(d.get("article_number")) != ""}
        sorted_articles = sorted(list(articles), key=_natural_sort_key)
        
        return {
            "law_title": canonical_title,
            "source": str(docs[0].get("source", "")),
            "is_official_statute": True,
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
        
        clean_law_title = law_title.strip()

        # --- SMART RECOVERY FOR HALLUCINATED TITLES (e.g. "Neni 258", "Neni 423") ---
        if clean_law_title.lower().startswith("neni") or clean_law_title == article_number:
            fallback_doc = db.legal_knowledge_base.find_one({
                "article_number": str(article_number),
                "category": {"$nin": ["academic", "caselaw"]}
            })
            if fallback_doc and fallback_doc.get("law_title"):
                clean_law_title = fallback_doc.get("law_title")
                logger.info(f"Resolved hallucinated title '{law_title}' -> '{clean_law_title}' for Neni {article_number}")

        statute_docs, academic_doc, metadata = find_law_documents(db, clean_law_title, article_number)
        
        # Fallback query if find_law_documents missed
        if not statute_docs or not statute_docs[0]:
            fallback_docs = list(db.legal_knowledge_base.find({
                "article_number": str(article_number),
                "category": {"$nin": ["academic", "caselaw"]}
            }).limit(5))
            if fallback_docs:
                statute_docs = fallback_docs

        if not statute_docs or not statute_docs[0]: 
            raise HTTPException(status_code=404, detail=f"Dokumenti ({law_title}, Neni {article_number}) nuk u gjet në bazën e të dhënave.")

        primary_doc = statute_docs[0]
        source_info = _generate_source_info(primary_doc, metadata if 'metadata' in locals() else {}, clean_law_title, article_number)

        response_data = {
            "law_title": primary_doc.get("law_title", clean_law_title),
            "article_number": primary_doc.get("article_number", article_number),
            "source": primary_doc.get("source", ""),
            "text": "\n\n".join([doc.get("text", "") for doc in statute_docs if doc and doc.get("text")]),
            "source_info": source_info
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