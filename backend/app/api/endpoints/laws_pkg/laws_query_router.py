# FILE: backend/app/api/endpoints/laws_pkg/laws_query_router.py
# PHOENIX PROTOCOL - LAWS QUERY ROUTER V80.0 (INTEGRATED AI SEMANTIC REASONING & TRI-SOURCE MATCHING)

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import Set, List, Optional, Dict, Any
import logging
import os
import re
import json

from app.services import vector_store_service, storage_service
from app.api.endpoints.dependencies import get_current_user
from app.api.endpoints.laws_pkg.laws_dictionary import _normalize_hallucinated_title, _natural_sort_key
from app.api.endpoints.laws_pkg.laws_search_service import find_documents_by_title, find_law_documents, _generate_source_info

logger = logging.getLogger(__name__)
router = APIRouter()

CASE_NO_REGEX = re.compile(r'(REV|PML|PA1|A|CP|PKR|P|KMLP|ANR)\s*\.?\s*NR', re.IGNORECASE)

LAW_ACRONYMS = {
    "lmd": "Ligji për Marrëdhëniet e Detyrimeve",
    "lpk": "Ligji për Procedurën Kontestimore",
    "kpk": "Kodi Penal i Republikës së Kosovës",
    "kprk": "Kodi Penal i Republikës së Kosovës",
    "kpprk": "Kodi i Procedurës Penale",
    "lfk": "Ligji për Familjen i Kosovës",
    "lsht": "Ligji për Shoqëritë Tregtare",
    "lp": "Ligji i Punës",
}


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


@router.post("/ai-semantic-search")
@router.get("/ai-semantic-search")
async def ai_semantic_law_search(
    query: str = Query(None),
    payload: Optional[Dict[str, Any]] = Body(None),
    current_user = Depends(get_current_user)
):
    """
    PHOENIX PROTOCOL - AI-POWERED LEGAL SEMANTIC REASONING & QUALIFICATION ENGINE.
    Analyzes any layperson query or legal scenario, diagnoses the exact law & articles,
    and returns matches across Statutes, Academia, and Supreme Court Decisions.
    """
    user_query = query or (payload.get("query") if payload else "")
    if not user_query or not user_query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    clean_q = user_query.strip()
    
    try:
        from app.core.db import get_db_instance
        db = get_db_instance()
        
        # 1. Kërkim i shpejtë në Vector Store për kontekst relevant
        vector_results = []
        try:
            vector_results = vector_store_service.query_global_knowledge_base(clean_q, n_results=5)
        except Exception as v_err:
            logger.warning(f"Vector search fallback: {v_err}")

        # 2. Analizë me LLM (DeepSeek / LLM Client)
        ai_qualification = {
            "legal_institute": "Kualifikim i Përgjithshëm Juridik",
            "plain_explanation": f"Analizë juridike mbi çështjen: '{clean_q}'",
            "matched_statutes": [],
            "suggested_actions": []
        }

        try:
            from app.services.llm.llm_client import get_llm_client
            llm = get_llm_client()
            
            system_prompt = (
                "Ti je Krye-Eksperti Juridik i Republikës së Kosovës. Detyra jote është të analizosh pyetjen "
                "e përdoruesit (e cila mund të jetë me fjalë të thjeshta popullore ose raste praktike) dhe të "
                "kthesh një JSON me kualifikimin e saktë ligjor bazuar në ligjet e Kosovës (LPK, LMD, KPK, KPPRK, LP, LSHT).\n\n"
                "Formati i detyrueshëm i përgjigjes (VETËM JSON):\n"
                "{\n"
                '  "legal_institute": "Emri i institutit juridik (p.sh. Masat e Sigurimit / Të Metat e Fshehura)",\n'
                '  "plain_explanation": "Shpjegim me 1-2 fjali të thjeshta popullore për qytetarët",\n'
                '  "target_law": "LPK / LMD / Kodi Penal / Ligji i Punës",\n'
                '  "articles": ["Numri i nenit, p.sh. 297", "298", "304.3"],\n'
                '  "explanation": "Pse këto nene janë relevante"\n'
                "}"
            )
            
            llm_response = await llm.generate_response(
                prompt=f"Analizo këtë pyetje/situatë juridike të Kosovës: \"{clean_q}\"",
                system_prompt=system_prompt,
                temperature=0.1
            )
            
            # Nxirr JSON-in nga përgjigja
            json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(0))
                ai_qualification["legal_institute"] = parsed.get("legal_institute", "Kualifikim Juridik")
                ai_qualification["plain_explanation"] = parsed.get("plain_explanation", "")
                
                target_law = parsed.get("target_law", "LPK")
                target_articles = parsed.get("articles", [])
                
                for art in target_articles:
                    ai_qualification["matched_statutes"].append({
                        "law_title": target_law,
                        "article_number": str(art),
                        "explanation": parsed.get("explanation", ""),
                        "confidence": 0.98
                    })
        except Exception as llm_err:
            logger.warning(f"LLM diagnostic fallback to rule matrix: {llm_err}")

        # 3. Kërkim i Aktgjykimeve dhe Manualeve përkatëse në DB
        caselaw_matches = list(db.legal_knowledge_base.find({
            "$or": [
                {"law_title": {"$regex": re.escape(clean_q), "$options": "i"}},
                {"source": {"$regex": re.escape(clean_q), "$options": "i"}},
                {"text": {"$regex": re.escape(clean_q), "$options": "i"}}
            ],
            "$or": [
                {"category": "caselaw"},
                {"is_case_law": True},
                {"source": {"$regex": "case_law|supreme", "$options": "i"}}
            ]
        }).limit(5))

        clean_caselaw = []
        for c in caselaw_matches:
            clean_caselaw.append({
                "title": c.get("law_title") or c.get("source", "Aktgjykim"),
                "source": c.get("source", ""),
                "page": c.get("page") or c.get("page_number") or 1
            })

        return {
            "query": clean_q,
            "ai_diagnostic": ai_qualification,
            "vector_context": vector_results[:3] if vector_results else [],
            "caselaw_precedents": clean_caselaw,
            "success": True
        }

    except Exception as e:
        logger.error(f"Error in ai_semantic_law_search: {e}")
        raise HTTPException(status_code=500, detail=f"AI Search error: {str(e)}")


@router.get("/case-page")
async def get_case_starting_page(law_title: str = Query(...), current_user = Depends(get_current_user)):
    """Returns the exact starting page number for a selected court decision or statute."""
    try:
        from app.core.db import get_db_instance
        db = get_db_instance()
        clean_title = law_title.strip()

        doc = db.legal_knowledge_base.find_one(
            {"$or": [
                {"law_title": clean_title},
                {"law_title": {"$regex": re.escape(clean_title), "$options": "i"}},
                {"source": {"$regex": re.escape(clean_title), "$options": "i"}}
            ]},
            sort=[("page", 1)]
        )
        if doc:
            raw_page = doc.get("page") or doc.get("page_number") or 1
            try:
                page_val = int(raw_page)
            except Exception:
                page_val = 1
            return {"page": page_val, "page_number": page_val, "law_title": clean_title}
        return {"page": 1, "page_number": 1, "law_title": clean_title}
    except Exception as e:
        logger.warning(f"Error fetching starting page: {e}")
        return {"page": 1, "page_number": 1, "law_title": law_title}


@router.get("/titles")
async def get_law_titles(current_user = Depends(get_current_user)):
    try:
        from app.core.db import get_db_instance
        db = get_db_instance()
        
        # 1. AKADEMIA JURIDIKE
        academic_filter = {
            "$or": [
                {"category": "academic"},
                {"is_academic": True},
                {"source": {"$regex": "akademia|doracak|komentar", "$options": "i"}}
            ]
        }
        academic_db_sources = db.legal_knowledge_base.distinct("source", academic_filter)
        academic_db_titles = db.legal_knowledge_base.distinct("law_title", academic_filter)
        b2_academic = _get_b2_filenames("academic/")
        
        raw_academic_sources = set([
            s.strip() for s in (academic_db_sources + academic_db_titles + b2_academic) 
            if s and s.strip()
        ])
        clean_academic = sorted(list(raw_academic_sources))

        # 2. AKTGJYKIMET E GJYKATËS SUPREME
        caselaw_filter = {
            "$or": [
                {"category": "caselaw"},
                {"is_case_law": True},
                {"case_number": {"$exists": True, "$ne": None, "$ne": ""}},
                {"law_title": {"$regex": r"Gjykata\s+Supreme|PML|REV|PA1|PKR", "$options": "i"}}
            ]
        }
        caselaw_db_titles = db.legal_knowledge_base.distinct("law_title", caselaw_filter)
        caselaw_db_sources = db.legal_knowledge_base.distinct("source", caselaw_filter)
        b2_caselaw = _get_b2_filenames("case_law/")

        raw_caselaw = set([t.strip() for t in (caselaw_db_titles + caselaw_db_sources + b2_caselaw) if t and t.strip()])
        clean_caselaw = sorted(list(raw_caselaw))

        # 3. KODET DHE LIGJET STATUTORE (19 LIGJET E KOSOVËS)
        statutes_filter = {
            "is_article": True,
            "$nor": [
                {"category": "caselaw"},
                {"is_case_law": True},
                {"category": "academic"},
                {"is_academic": True},
                {"law_title": {"$regex": r"Gjykata\s+Supreme|PML|REV|PA1|PKR", "$options": "i"}}
            ]
        }
        all_statute_titles = db.legal_knowledge_base.distinct("law_title", statutes_filter)
        
        raw_statutes = []
        for t in all_statute_titles:
            t_clean = t.strip()
            if t_clean and not t_clean.lower().endswith('.pdf') and not CASE_NO_REGEX.search(t_clean) and "supreme" not in t_clean.lower():
                raw_statutes.append(t_clean)

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


@router.get("/library")
async def get_laws_library(
    q: Optional[str] = Query(None), 
    limit: int = Query(50, ge=1, le=200),
    current_user = Depends(get_current_user)
):
    """
    PHOENIX ENGINE: Unified Library Gateway.
    If 'q' is provided, searches case law & statutes across the 7,050 pages.
    Otherwise returns the complete library catalog.
    """
    try:
        if q and q.strip():
            return vector_store_service.query_global_knowledge_base(q.strip(), n_results=limit)
        return await get_law_titles(current_user=current_user)
    except Exception as e:
        logger.error(f"Error in /library endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Library error: {str(e)}")


@router.get("/by-title")
async def get_law_articles(law_title: str = Query(...), current_user = Depends(get_current_user)):
    try:
        from app.core.db import get_db_instance
        db = get_db_instance()
        
        clean_title = law_title.strip()
        clean_key = clean_title.lower()
        if clean_key in LAW_ACRONYMS:
            clean_title = LAW_ACRONYMS[clean_key]

        mapped_title = _normalize_hallucinated_title(clean_title, "")

        docs = find_documents_by_title(
            db, 
            mapped_title if mapped_title else clean_title, 
            fields={"law_title": 1, "article_number": 1, "source": 1, "chunk_index": 1, "page": 1, "page_number": 1, "text": 1}
        )

        if not docs:
            raise HTTPException(status_code=404, detail=f"Ligji '{law_title}' nuk u gjet në bazën e të dhënave.")
        
        canonical_title = docs[0].get("law_title", mapped_title if mapped_title else clean_title)

        articles: Set[str] = {str(d.get("article_number")) for d in docs if d.get("article_number") and str(d.get("article_number")) != ""}
        sorted_articles = sorted(list(articles), key=_natural_sort_key)
        
        raw_page = docs[0].get("page") or docs[0].get("page_number") or 1
        try:
            page_val = int(raw_page)
        except Exception:
            page_val = 1

        return {
            "law_title": canonical_title,
            "source": str(docs[0].get("source", "")),
            "page": page_val,
            "page_number": page_val,
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
        clean_art = str(article_number).strip()

        clean_key = clean_law_title.lower()
        if clean_key in LAW_ACRONYMS:
            clean_law_title = LAW_ACRONYMS[clean_key]

        if clean_law_title.lower().startswith("neni") or clean_law_title == clean_art or clean_law_title == "Ligji përkatës":
            fallback_doc = db.legal_knowledge_base.find_one({
                "article_number": clean_art,
                "is_article": True
            })
            if fallback_doc and fallback_doc.get("law_title"):
                clean_law_title = fallback_doc.get("law_title")

        try:
            statute_docs, academic_doc, metadata = find_law_documents(db, clean_law_title, clean_art)
        except Exception as find_err:
            logger.warning(f"find_law_documents warning: {find_err}")
            statute_docs, academic_doc, metadata = [], None, {}
        
        if not statute_docs or len(statute_docs) == 0:
            fallback_docs = list(db.legal_knowledge_base.find({
                "article_number": clean_art,
                "is_article": True
            }).limit(5))
            if fallback_docs:
                statute_docs = fallback_docs

        if not statute_docs or len(statute_docs) == 0 or not statute_docs[0]: 
            raise HTTPException(status_code=404, detail=f"Neni {clean_art} i ligjit '{clean_law_title}' nuk u gjet.")

        primary_doc = statute_docs[0]
        source_info = _generate_source_info(primary_doc, metadata or {}, clean_law_title, clean_art)

        raw_page = primary_doc.get("page") or primary_doc.get("page_number") or 1
        try:
            page_val = int(raw_page)
        except Exception:
            page_val = 1

        response_data = {
            "law_title": primary_doc.get("law_title", clean_law_title),
            "article_number": primary_doc.get("article_number", clean_art),
            "source": primary_doc.get("source", ""),
            "page": page_val,
            "page_number": page_val,
            "text": "\n\n".join([doc.get("text", "") for doc in statute_docs if doc and doc.get("text")]),
            "source_info": source_info
        }

        return response_data
    except HTTPException: raise
    except Exception as e: 
        logger.error(f"Article endpoint error handled: {e}")
        raise HTTPException(status_code=404, detail=f"Baza ligjore nuk u gjet: {str(e)}")


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
            
        raw_page = doc.get("page") or doc.get("page_number") or 1
        try:
            page_val = int(raw_page)
        except Exception:
            page_val = 1

        return {
            "law_title": str(doc.get("law_title", "Ligji")),
            "article_number": str(doc.get("article_number", "")),
            "source": str(doc.get("source", "")),
            "page": page_val,
            "page_number": page_val,
            "text": doc.get("text", "")
        }
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")