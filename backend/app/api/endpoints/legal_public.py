# FILE: backend/app/api/endpoints/legal_public.py
# PHOENIX PROTOCOL - LEGAL PUBLIC ENDPOINTS V1.1 (STRICT EXPORT)
# 1. FIXED: Explicit router export to resolve Pylance 'unknown import symbol' in main.py.
# 2. ENHANCED: Type hints for RAG service initialization.
# 3. RETAINED: 100% of the public RAG search logic for Kosovo laws.

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Any
import logging

from app.services.albanian_rag_service import AlbanianRAGService
from app.core.db import get_db
from pymongo.database import Database

# Define the router with a specific prefix for public access
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
    Searches Kosovo laws and legal documents using the Albanian RAG engine.
    """
    try:
        # Initialize RAG service with the injected database session
        rag_service = AlbanianRAGService(db)
        
        # Use fast_rag to generate a comprehensive legal context string
        # user_id is set to "public" for unauthenticated tracking
        context = await rag_service.fast_rag(
            query=request.query,
            user_id="public",
            case_id=None
        )
        
        # Return structured response; results can be extended if document metadata is added later
        return RAGSearchResponse(
            results=[],
            context=context or "Nuk u gjet asnjë informacion për këtë kërkim."
        )
        
    except Exception as e:
        logger.error(f"Public RAG search failed: {str(e)}")
        # Provide a generic error to the public but log the specifics
        raise HTTPException(
            status_code=500, 
            detail="Një gabim i brendshëm ndodhi gjatë kërkimit juridik."
        )

# Phoenix: Explicitly export the router to ensure Pylance/FastAPI recognition
__all__ = ["router"]