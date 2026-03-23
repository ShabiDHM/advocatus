# FILE: backend/app/api/endpoints/laws.py
# PHOENIX PROTOCOL - LAWS ENDPOINTS V8.1 (SEPARATOR CONFLICT FIX)
# 1. FIXED: Uses [NDARJA] separator to avoid collision with llm_service disclaimer.
# 2. RETAINED: 100% of retrieval, search, title, and chunk logic. No omissions.

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Set, Any
from app.services import vector_store_service, llm_service
from app.api.endpoints.dependencies import get_current_user

router = APIRouter(tags=["Laws"])

class LawExplainRequest(BaseModel):
    law_title: str
    article_number: str
    prompt: str

def _safe_int(value: Any) -> int:
    if value is None: return 0
    try: return int(value)
    except (ValueError, TypeError): return 0

def _natural_sort_key(article_any: Any) -> List[int]:
    article = str(article_any) if article_any is not None else "0"
    parts = article.split('.')
    return [int(p) for p in parts if p.isdigit()]

# --- AI ANALYSIS ENDPOINT ---

@router.post("/explain")
async def explain_law_article(
    request: LawExplainRequest,
    current_user = Depends(get_current_user)
):
    """
    PHOENIX: Streams a dual-layered AI explanation.
    Uses the strict [NDARJA] marker to ensure the frontend splits the tabs perfectly,
    without colliding with the backend's automatic disclaimer.
    """
    system_prompt = (
        "DETYRA: Analizo këtë nen ligjor nga dy perspektiva të ndryshme.\n\n"
        "PJESA 1: Perspektiva e 'Senior Legal Partner'\n"
        "- Toni: Autoritar, teknik, doktrinar.\n"
        "- Fokusohu: Lidhja me Kushtetutën e Kosovës, Konventën Evropiane për të Drejtat e Njeriut (KEDNJ), "
        "parimet e procedurës dhe rreziqet statutore.\n\n"
        "FORMATI I DETYRUESHËM: Pasi të mbarosh Pjesën 1, shkruaj SAKTËSISHT fjalën [NDARJA] në një rresht të ri.\n\n"
        "PJESA 2: Perspektiva e Qytetarit të Thjeshtë\n"
        "- Toni: Miqësor, i qartë, pa zhargon juridik.\n"
        "- Fokusohu: Çfarë do të thotë kjo për qytetarin? Cilat janë të drejtat apo detyrimet e tij "
        "në jetën e përditshme? Jep një shembull praktik.\n\n"
        "GJUHA: Përgjigju VETËM në gjuhën SHQIPE."
    )
    
    try:
        generator = llm_service.stream_text_async(
            sys_p=system_prompt,
            user_p=request.prompt,
            temp=0.2
        )
        return StreamingResponse(generator, media_type="text/plain")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Synthesis failed: {str(e)}")

# --- DATA RETRIEVAL ENDPOINTS ---

@router.get("/search")
async def search_laws(
    q: str = Query(..., description="Search query"),
    limit: int = Query(50, ge=1, le=200),
    current_user = Depends(get_current_user)
):
    try:
        results = vector_store_service.query_global_knowledge_base(q, n_results=limit)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/titles")
async def get_law_titles(current_user = Depends(get_current_user)):
    try:
        collection = vector_store_service.get_global_collection()
        results = collection.get(include=["metadatas"], limit=10000)
        metadatas = results.get("metadatas") or []
        titles: Set[str] = set()
        for m in metadatas:
            title = m.get("law_title")
            if isinstance(title, str): titles.add(title)
        return sorted(list(titles))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching titles: {str(e)}")

@router.get("/article")
async def get_law_article(
    law_title: str = Query(...),
    article_number: str = Query(...),
    current_user = Depends(get_current_user)
):
    try:
        collection = vector_store_service.get_global_collection()
        results = collection.get(
            where={"$and": [{"law_title": {"$eq": law_title}}, {"article_number": {"$eq": article_number}}]},
            include=["documents", "metadatas"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    documents = results.get("documents") or []
    metadatas = results.get("metadatas") or []
    if not documents: raise HTTPException(status_code=404, detail="Article not found")

    if metadatas and all("chunk_index" in m for m in metadatas):
        pairs = list(zip(documents, metadatas))
        pairs.sort(key=lambda x: _safe_int(x[1].get("chunk_index")))
        documents = [d for d, _ in pairs]

    return {
        "law_title": str(metadatas[0].get("law_title", law_title)) if metadatas else law_title,
        "article_number": str(metadatas[0].get("article_number", article_number)) if metadatas else article_number,
        "source": str(metadatas[0].get("source", "")) if metadatas else "",
        "text": "\n\n".join(documents)
    }

@router.get("/by-title")
async def get_law_articles(
    law_title: str = Query(...),
    current_user = Depends(get_current_user)
):
    try:
        collection = vector_store_service.get_global_collection()
        results = collection.get(
            where={"law_title": {"$eq": law_title}},
            include=["metadatas"],
            limit=1000
        )
        metadatas = results.get("metadatas") or []
        if not metadatas: raise HTTPException(status_code=404, detail="Law not found")
        articles: Set[str] = {str(m.get("article_number")) for m in metadatas if m.get("article_number") is not None}
        sorted_articles = sorted(list(articles), key=_natural_sort_key)
        first_m = metadatas[0] if metadatas else {}
        return {
            "law_title": str(first_m.get("law_title", law_title)),
            "source": str(first_m.get("source", "")),
            "article_count": len(sorted_articles),
            "articles": sorted_articles
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@router.get("/{chunk_id}")
async def get_law_chunk(chunk_id: str, current_user = Depends(get_current_user)):
    try:
        collection = vector_store_service.get_global_collection()
        result = collection.get(ids=[chunk_id], include=["documents", "metadatas"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    docs = result.get("documents") or []
    metas = result.get("metadatas") or []
    if not docs: raise HTTPException(status_code=404, detail="Law chunk not found")

    m = metas[0] if metas else {}
    return {
        "law_title": str(m.get("law_title", "Ligji i panjohur")),
        "article_number": str(m.get("article_number", "")),
        "source": str(m.get("source", "")),
        "text": docs[0]
    }