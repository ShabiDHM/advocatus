from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from services.rerank_manager import rerank_manager

router = APIRouter()

class RerankRequest(BaseModel):
    query: str
    documents: List[str]

class RerankResponse(BaseModel):
    reranked_documents: List[str]

@router.post("/sort", response_model=RerankResponse)
async def sort_documents(request: RerankRequest):
    """
    Re-ranks a list of documents based on semantic similarity to the query.
    """
    try:
        sorted_docs = rerank_manager.rank_documents(request.query, request.documents)
        return RerankResponse(reranked_documents=sorted_docs)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))