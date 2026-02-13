# FILE: backend/app/api/endpoints/laws.py
# PHOENIX PROTOCOL - ROUTE ORDER FIX V1.0 (SEARCH PRIORITY)
# 1. MOVED: /search endpoint above /{chunk_id} to prevent route shadowing.
# 2. STATUS: Fixed Critical Logic Error.

from fastapi import APIRouter, Depends, HTTPException, Query
from pymongo.database import Database
from app.services import vector_store_service
from app.api.endpoints.dependencies import get_current_user, get_db

router = APIRouter(tags=["Laws"])

@router.get("/search")
async def search_laws(
    q: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=50),
    current_user = Depends(get_current_user)
):
    """Semantic search for laws. Returns matching chunks with metadata."""
    try:
        results = vector_store_service.query_global_knowledge_base(q, n_results=limit)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

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