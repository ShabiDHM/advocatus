# FILE: backend/app/api/endpoints/laws.py
# PHOENIX PROTOCOL - LAWS ENDPOINTS V3.1 (TYPE-SAFE AI ANALYST)
# 1. FIXED: Pylance 'Unhashable' errors by strictly casting metadata to strings.
# 2. FIXED: 'None subscriptable' errors using guarded collection access.
# 3. ADDED: POST /explain endpoint for streaming AI legal analysis.
# 4. RETAINED: 100% functionality and Senior Partner persona integration.

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Set, Any
from app.services import vector_store_service, llm_service
from app.api.endpoints.dependencies import get_current_user

router = APIRouter(tags=["Laws"])

# --- MODELS ---
class LawExplainRequest(BaseModel):
    law_title: str
    article_number: str
    prompt: str

# --- UTILS ---
def _safe_int(value: Any) -> int:
    """Safely convert metadata values to integer."""
    if value is None: return 0
    try: return int(value)
    except (ValueError, TypeError): return 0

def _natural_sort_key(article_any: Any) -> List[int]:
    """Sort article numbers (e.g., '5.1' -> [5, 1]) safely."""
    article = str(article_any) if article_any is not None else "0"
    parts = article.split('.')
    return [int(p) for p in parts if p.isdigit()]

# --- ENDPOINTS ---

@router.post("/explain")
async def explain_law_article(
    request: LawExplainRequest,
    current_user = Depends(get_current_user)
):
    """
    PHOENIX: Streams an AI-generated explanation of a specific law article.
    Uses llm_service.stream_text_async with mandatory disclaimer.
    """
    system_prompt = (
        "DETYRA: Ti je një Senior Legal Partner. Shpjego këtë nen ligjor në mënyrë të thjeshtë "
        "por profesionale. Fokusohu te zbatimi praktik në Kosovë dhe rreziqet potenciale. "
        "Përgjigju vetëm në gjuhën SHQIPE."
    )
    
    generator = llm_service.stream_text_async(
        sys_p=system_prompt,
        user_p=request.prompt,
        temp=0.3
    )
    
    return StreamingResponse(generator, media_type="text/plain")

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
    """Get all distinct law titles, sorted alphabetically."""
    try:
        collection = vector_store_service.get_global_collection()
        results = collection.get(include=["metadatas"], limit=10000)
        metadatas = results.get("metadatas")
        
        titles: Set[str] = set()
        if metadatas:
            for m in metadatas:
                title = m.get("law_title")
                if isinstance(title, str):
                    titles.add(title)
        return sorted(list(titles))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching titles: {str(e)}")

@router.get("/article")
async def get_law_article(
    law_title: str = Query(...),
    article_number: str = Query(...),
    current_user = Depends(get_current_user)
):
    """Retrieve all chunks belonging to a specific article and combine them."""
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

    documents = results.get("documents") or []
    metadatas = results.get("metadatas") or []
    
    if not documents:
        raise HTTPException(status_code=404, detail="Article not found")

    # Handle multi-chunk articles
    if metadatas and all("chunk_index" in m for m in metadatas):
        pairs = list(zip(documents, metadatas))
        pairs.sort(key=lambda x: _safe_int(x[1].get("chunk_index")))
        documents = [d for d, _ in pairs]

    full_text = "\n\n".join(documents)
    meta = metadatas[0] if metadatas else {}
    
    return {
        "law_title": str(meta.get("law_title", law_title)),
        "article_number": str(meta.get("article_number", article_number)),
        "source": str(meta.get("source", "")),
        "text": full_text
    }

@router.get("/by-title")
async def get_law_articles(
    law_title: str = Query(...),
    current_user = Depends(get_current_user)
):
    """Retrieve article numbers for a law (Table of Contents)."""
    try:
        collection = vector_store_service.get_global_collection()
        results = collection.get(
            where={"law_title": {"$eq": law_title}},
            include=["metadatas"],
            limit=1000
        )
        metadatas = results.get("metadatas")
        if not metadatas:
            raise HTTPException(status_code=404, detail="Law not found")

        # FIXED: Ensure only hashable strings enter the set
        articles: Set[str] = set()
        for m in metadatas:
            art = m.get("article_number")
            if art is not None:
                articles.add(str(art))

        sorted_articles = sorted(list(articles), key=_natural_sort_key)
        first_meta = metadatas[0] if metadatas else {}
        
        return {
            "law_title": str(first_meta.get("law_title", law_title)),
            "source": str(first_meta.get("source", "")),
            "article_count": len(sorted_articles),
            "articles": sorted_articles
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@router.get("/{chunk_id}")
async def get_law_chunk(chunk_id: str, current_user = Depends(get_current_user)):
    """Retrieve a specific law chunk by ID."""
    try:
        collection = vector_store_service.get_global_collection()
        result = collection.get(ids=[chunk_id], include=["documents", "metadatas"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    docs = result.get("documents")
    metas = result.get("metadatas")

    if not docs or len(docs) == 0:
        raise HTTPException(status_code=404, detail="Law chunk not found")

    # FIXED: Guarded access to prevent subscript errors
    law_text = docs[0]
    metadata = metas[0] if metas and len(metas) > 0 else {}

    return {
        "law_title": str(metadata.get("law_title", "Ligji i panjohur")),
        "article_number": str(metadata.get("article_number", "")),
        "source": str(metadata.get("source", "")),
        "text": law_text
    }