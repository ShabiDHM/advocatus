from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from services.embedding_manager import embedding_manager

router = APIRouter()

class EmbeddingRequest(BaseModel):
    text_content: str

class EmbeddingResponse(BaseModel):
    embedding: List[float]

@router.post("/generate", response_model=EmbeddingResponse)
async def generate_embedding(request: EmbeddingRequest):
    """
    Generates vector embeddings for the provided text.
    Compatible with legacy embedding_service.
    """
    try:
        vector = embedding_manager.generate_embedding(request.text_content)
        return EmbeddingResponse(embedding=vector)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))