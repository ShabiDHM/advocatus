# FILE: ai-core-service/routers/embeddings.py
# PHOENIX PROTOCOL - AI CORE ROUTER V2.0 (CONTRACT FIX)
# 1. FIX: Added 'language' field to EmbeddingRequest to match Backend payload.
# 2. RESULT: Prevents 422 Validation Errors when Backend sends language hints.

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from services.embedding_manager import embedding_manager

router = APIRouter()

class EmbeddingRequest(BaseModel):
    text_content: str
    # PHOENIX FIX: Accept the language parameter (default to standard)
    language: Optional[str] = "standard"

class EmbeddingResponse(BaseModel):
    embedding: List[float]

@router.post("/generate", response_model=EmbeddingResponse)
async def generate_embedding(request: EmbeddingRequest):
    """
    Generates vector embeddings for the provided text.
    Now accepts 'language' context to align with Backend architecture.
    """
    try:
        # Pass the language down to the manager
        vector = embedding_manager.generate_embedding(
            text=request.text_content, 
            language=request.language
        )
        return EmbeddingResponse(embedding=vector)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))