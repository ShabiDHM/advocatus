# FILE: backend/app/api/endpoints/laws.py
# PHOENIX PROTOCOL - LAWS ENDPOINTS V2.2 (FIXED OPTIONAL ITERABLE)
# 1. FIXED: In get_law_titles, handle None metadatas by defaulting to empty list.
# 2. ENHANCED: Search limit increased to 50 (max 200).
# 3. RETAINED: All existing functionality.

from fastapi import APIRouter, Depends, HTTPException, Query
from pymongo.database import Database
from app.services import vector_store_service
from app.api.endpoints.dependencies import get_current_user, get_db

router = APIRouter(tags=["Laws"])

def _safe_int(value) -> int:
    """Convert metadata value to int safely; return 0 if not possible."""
    if value is None:
        return 0
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0

def _natural_sort_key(article: str):
    """Split article number into parts for natural sorting (e.g., 5.1 -> [5,1])."""
    parts = article.split('.')
    return [int(p) for p in parts if p.isdigit()]

@router.get("/search")
async def search_laws(
    q: str = Query(..., description="Search query"),
    limit: int = Query(50, ge=1, le=200),
    current_user = Depends(get_current_user)
):
    """Semantic search for laws. Returns matching chunks with metadata."""
    try:
        results = vector_store_service.query_global_knowledge_base(q, n_results=limit)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/titles")
async def get_law_titles(
    current_user = Depends(get_current_user)
):
    """Get all distinct law titles, sorted alphabetically."""
    try:
        collection = vector_store_service.get_global_collection()
        # Fetch up to 10000 chunks (should cover all laws)
        results = collection.get(include=["metadatas"], limit=10000)
        metadatas = results.get("metadatas") or []  # ensure it's a list
        titles = set()
        for m in metadatas:
            title = m.get("law_title")
            if title:
                titles.add(title)
        sorted_titles = sorted(titles)
        return sorted_titles
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching titles: {str(e)}")

@router.get("/article")
async def get_law_article(
    law_title: str = Query(..., description="Law title"),
    article_number: str = Query(..., description="Article number"),
    current_user = Depends(get_current_user)
):
    """
    Retrieve all chunks belonging to a specific article.
    This combines multiple chunks (if the article was split) into one full text.
    """
    try:
        collection = vector_store_service.get_global_collection()
        results = collection.get(
            where={
                "$and": [
                    {"law_title": {"$eq": law_title}},
                    {"article_number": {"$eq": article_number}}
                ]
            },
            include=["documents", "metadatas"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    documents = results.get("documents", [])
    metadatas = results.get("metadatas", [])
    if not documents:
        raise HTTPException(status_code=404, detail="Article not found")

    # Sort chunks by chunk_index if present, otherwise assume order.
    if metadatas and all("chunk_index" in m for m in metadatas):
        pairs = list(zip(documents, metadatas))
        pairs.sort(key=lambda x: _safe_int(x[1].get("chunk_index")))
        documents = [d for d, _ in pairs]
        metadatas = [m for _, m in pairs]

    # Combine all chunks with double newline as separator
    full_text = "\n\n".join(documents)

    meta = metadatas[0] if metadatas else {}
    return {
        "law_title": meta.get("law_title", law_title),
        "article_number": meta.get("article_number", article_number),
        "source": meta.get("source", ""),
        "text": full_text
    }

@router.get("/by-title")
async def get_law_articles(
    law_title: str = Query(..., description="Law title"),
    current_user = Depends(get_current_user)
):
    """
    Retrieve all articles for a given law title, returning a sorted list of article numbers.
    Used for table of contents.
    """
    try:
        collection = vector_store_service.get_global_collection()
        # Get up to 1000 chunks (should cover any law)
        results = collection.get(
            where={"law_title": {"$eq": law_title}},
            include=["metadatas"],
            limit=1000
        )
        metadatas = results.get("metadatas", [])
        if not metadatas:
            raise HTTPException(status_code=404, detail="Law not found")

        # Collect unique article numbers
        articles = set()
        for m in metadatas:
            art = m.get("article_number")
            if art:
                articles.add(art)

        # Sort naturally
        sorted_articles = sorted(articles, key=_natural_sort_key)

        first = metadatas[0]
        return {
            "law_title": first.get("law_title", law_title),
            "source": first.get("source", ""),
            "article_count": len(sorted_articles),
            "articles": sorted_articles
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@router.get("/{chunk_id}")
async def get_law_chunk(
    chunk_id: str,
    current_user = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """Retrieve a specific law chunk by its ID."""
    try:
        collection = vector_store_service.get_global_collection()
        result = collection.get(ids=[chunk_id], include=["documents", "metadatas"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    if result is None:
        raise HTTPException(status_code=404, detail="Law chunk not found")

    documents = result.get("documents")
    metadatas = result.get("metadatas")

    if not documents or len(documents) == 0:
        raise HTTPException(status_code=404, detail="Law chunk not found")

    law_text = documents[0]
    metadata = metadatas[0] if metadatas and len(metadatas) > 0 else {}

    return {
        "law_title": metadata.get("law_title", "Ligji i panjohur"),
        "article_number": metadata.get("article_number"),
        "source": metadata.get("source"),
        "text": law_text
    }