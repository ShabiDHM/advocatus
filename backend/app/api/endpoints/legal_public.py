from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
import logging

from app.services.albanian_rag_service import AlbanianRAGService
from app.core.db import get_db
from pymongo.database import Database

router = APIRouter(prefix="/legal/public", tags=["legal-public"])

logger = logging.getLogger(__name__)

class RAGSearchRequest(BaseModel):
    query: str
    top_k: int = 5

class RAGSearchResponse(BaseModel):
    results: List[dict]
    context: str

@router.post("/rag/search", response_model=RAGSearchResponse)
async def search_legal_knowledge(
    request: RAGSearchRequest,
    db: Database = Depends(get_db)
):
    """
    Public endpoint for legal knowledge retrieval.
    No authentication required.
    Searches Kosovo laws and legal documents.
    """
    try:
        # Initialize RAG service with database session
        rag_service = AlbanianRAGService(db)
        
        # Use fast_rag to get legal context
        context = await rag_service.fast_rag(
            query=request.query,
            user_id="public",
            case_id=None
        )
        
        # Return empty results list since we're just getting context
        return RAGSearchResponse(
            results=[],
            context=context
        )
        
    except Exception as e:
        logger.error(f"RAG search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))