# FILE: backend/app/api/endpoints/public_laws.py
# PHOENIX PROTOCOL - PUBLIC LAW ENDPOINTS V1.1 (TYPE SAFE)

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Set, Any
from app.services import vector_store_service
from app.core.db import get_db
from pymongo.database import Database
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/legal/public/laws", tags=["public-laws"])

def _safe_int(value: Any) -> int:
    if value is None: return 0
    try: return int(value)
    except (ValueError, TypeError): return 0

def _natural_sort_key(article_any: Any) -> List[int]:
    article = str(article_any) if article_any is not None else "0"
    parts = article.split('.')
    return [int(p) for p in parts if p.isdigit()]

def _safe_str(value: Any, default: str = "") -> str:
    """Safely convert a value to string, returning default if conversion fails."""
    if value is None:
        return default
    try:
        return str(value)
    except Exception:
        return default

class LawArticleResponse(BaseModel):
    law_title: str
    article_number: Optional[str] = None
    source: str
    text: str

class LawOverviewResponse(BaseModel):
    law_title: str
    source: str
    article_count: int
    articles: List[str]

class LawSearchResult(BaseModel):
    law_title: str
    article_number: Optional[str]
    source: str
    text: str
    chunk_id: str

@router.get("/search", response_model=List[LawSearchResult])
async def public_search_laws(
    q: str = Query(..., description="Search query"),
    limit: int = Query(50, ge=1, le=200)
):
    """
    Public endpoint for legal search. No authentication required.
    """
    try:
        results = vector_store_service.query_global_knowledge_base(q, n_results=limit)
        # Ensure results conform to the expected shape
        return results
    except Exception as e:
        logger.error(f"Public law search failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Search failed. Please try again later.")

@router.get("/titles", response_model=List[str])
async def public_get_law_titles():
    """
    Public endpoint to get all law titles. No authentication.
    """
    try:
        collection = vector_store_service.get_global_collection()
        results = collection.get(include=["metadatas"], limit=10000)
        metadatas = results.get("metadatas") or []
        titles: Set[str] = set()
        for m in metadatas:
            title = m.get("law_title")
            if isinstance(title, str):
                titles.add(title)
            else:
                # If not a string, attempt to convert safely
                titles.add(_safe_str(title))
        return sorted(list(titles))
    except Exception as e:
        logger.error(f"Public law titles fetch failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Could not retrieve law titles.")

@router.get("/article", response_model=LawArticleResponse)
async def public_get_law_article(
    law_title: str = Query(...),
    article_number: str = Query(...)
):
    """
    Public endpoint to get a specific law article.
    """
    try:
        collection = vector_store_service.get_global_collection()
        results = collection.get(
            where={"$and": [{"law_title": {"$eq": law_title}}, {"article_number": {"$eq": article_number}}]},
            include=["documents", "metadatas"]
        )
    except Exception as e:
        logger.error(f"Public law article fetch failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error.")

    documents = results.get("documents") or []
    metadatas = results.get("metadatas") or []
    if not documents:
        raise HTTPException(status_code=404, detail="Article not found")

    # Sort by chunk index if present
    if metadatas and all("chunk_index" in m for m in metadatas):
        pairs = list(zip(documents, metadatas))
        pairs.sort(key=lambda x: _safe_int(x[1].get("chunk_index")))
        documents = [d for d, _ in pairs]

    first_meta = metadatas[0] if metadatas else {}
    return LawArticleResponse(
        law_title=_safe_str(first_meta.get("law_title"), law_title),
        article_number=_safe_str(first_meta.get("article_number")) if first_meta.get("article_number") is not None else None,
        source=_safe_str(first_meta.get("source")),
        text="\n\n".join(documents)
    )

@router.get("/by-title", response_model=LawOverviewResponse)
async def public_get_law_articles_by_title(
    law_title: str = Query(...)
):
    """
    Public endpoint to get all articles of a law.
    """
    try:
        collection = vector_store_service.get_global_collection()
        results = collection.get(
            where={"law_title": {"$eq": law_title}},
            include=["metadatas"],
            limit=1000
        )
        metadatas = results.get("metadatas") or []
        if not metadatas:
            raise HTTPException(status_code=404, detail="Law not found")
        articles: Set[str] = set()
        for m in metadatas:
            article = m.get("article_number")
            if article is not None:
                articles.add(_safe_str(article))
        sorted_articles = sorted(list(articles), key=_natural_sort_key)
        first_m = metadatas[0] if metadatas else {}
        return LawOverviewResponse(
            law_title=_safe_str(first_m.get("law_title"), law_title),
            source=_safe_str(first_m.get("source")),
            article_count=len(sorted_articles),
            articles=sorted_articles
        )
    except Exception as e:
        logger.error(f"Public law by-title fetch failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching law overview.")

@router.get("/{chunk_id}", response_model=LawArticleResponse)
async def public_get_law_chunk(chunk_id: str):
    """
    Public endpoint to get a specific law chunk by its ID.
    """
    try:
        collection = vector_store_service.get_global_collection()
        result = collection.get(ids=[chunk_id], include=["documents", "metadatas"])
    except Exception as e:
        logger.error(f"Public law chunk fetch failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error.")

    docs = result.get("documents") or []
    metas = result.get("metadatas") or []
    if not docs:
        raise HTTPException(status_code=404, detail="Law chunk not found")

    m = metas[0] if metas else {}
    return LawArticleResponse(
        law_title=_safe_str(m.get("law_title"), "Ligji i panjohur"),
        article_number=_safe_str(m.get("article_number")) if m.get("article_number") is not None else None,
        source=_safe_str(m.get("source")),
        text=docs[0]
    )