# FILE: backend/app/api/endpoints/laws.py
# PHOENIX PROTOCOL - LAW VIEWER ENDPOINT (FIXED)
# 1. FIXED: Pylance errors – safe handling of None values.
# 2. PURPOSE: Serve law article text by chunk ID, authenticated.

from fastapi import APIRouter, Depends, HTTPException
from pymongo.database import Database
from app.services import vector_store_service
from app.api.endpoints.dependencies import get_current_user, get_db

router = APIRouter(prefix="/laws", tags=["laws"])

@router.get("/{chunk_id}")
async def get_law_chunk(
    chunk_id: str,
    current_user = Depends(get_current_user),  # require authentication
    db: Database = Depends(get_db)
):
    """
    Retrieve a law chunk by its ChromaDB ID.
    Returns the article text and metadata.
    """
    try:
        collection = vector_store_service.get_global_collection()
        # ChromaDB get() returns a dict with keys: ids, documents, metadatas
        result = collection.get(ids=[chunk_id], include=["documents", "metadatas"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    # Safety checks
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