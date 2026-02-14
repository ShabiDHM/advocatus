# FILE: backend/app/api/endpoints/laws.py
# PHOENIX PROTOCOL - ADDED ARTICLE FETCH ENDPOINT V1.1
# 1. ADDED: /article endpoint to retrieve all chunks of a specific article.
# 2. RETAINED: Existing search and chunk-by-id endpoints.
# 3. STATUS: Ready for frontend integration.

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
        # Query with metadata filter: both law_title and article_number must match
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

    # Sort chunks by chunk_index if available, otherwise assume order is correct
    # If chunk_index is stored in metadata, use it to sort.
    # Since our ingestion script (V4.0) does not yet include chunk_index, we skip sorting.
    # If you have chunk_index, you can uncomment the sorting block.
    # sorted_data = sorted(zip(documents, metadatas), key=lambda x: x[1].get('chunk_index', 0))
    # documents = [d for d, _ in sorted_data]
    # metadatas = [m for _, m in sorted_data]

    # Combine all chunks with double newline as separator
    full_text = "\n\n".join(documents)

    # Use metadata from the first chunk for law_title, article_number, source
    meta = metadatas[0] if metadatas else {}
    return {
        "law_title": meta.get("law_title", law_title),
        "article_number": meta.get("article_number", article_number),
        "source": meta.get("source", ""),
        "text": full_text
    }

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