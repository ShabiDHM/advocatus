# rerank_service/main.py

import os
import logging
from contextlib import asynccontextmanager
from typing import List
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from sentence_transformers.cross_encoder import CrossEncoder

# --- Model & Application State ---
model_state = {}

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Lifespan Manager for Model Loading ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the CrossEncoder model on startup
    # This is a lightweight model, well-suited for re-ranking.
    model_name = os.getenv("MODEL_NAME", "cross-encoder/ms-marco-MiniLM-L-6-v2")
    
    logger.info(f"--- [Re-rank Service] Attempting to load model: {model_name} ---")
    
    try:
        model_state["rerank_model"] = CrossEncoder(model_name)
        model_state["model_name"] = model_name
        logger.info(f"--- [Re-rank Service] Model '{model_name}' loaded successfully. ---")
    except Exception as e:
        logger.error(f"--- [Re-rank Service] CRITICAL: Failed to load model '{model_name}'. Error: {e} ---")
    
    yield
    
    logger.info("--- [Re-rank Service] Shutting down... ---")
    model_state.clear()
    logger.info("--- [Re-rank Service] Shutdown complete. ---")

# --- FastAPI App Initialization ---
app = FastAPI(lifespan=lifespan)

# --- Pydantic Models for API ---
class RerankRequest(BaseModel):
    query: str
    documents: List[str]

class RerankResponse(BaseModel):
    reranked_documents: List[str]

# --- API Endpoints ---
@app.post("/rerank", response_model=RerankResponse)
def rerank_documents_endpoint(request: RerankRequest):
    model = model_state.get("rerank_model")
    if not model:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Re-ranking model is not available or failed to load."
        )
    
    try:
        # The cross-encoder needs pairs of [query, document]
        model_input = [[request.query, doc] for doc in request.documents]
        
        # Predict scores for each pair
        scores = model.predict(model_input)
        
        # Combine documents with their scores and sort
        doc_scores = list(zip(request.documents, scores))
        sorted_doc_scores = sorted(doc_scores, key=lambda x: x[1], reverse=True)
        
        # Return only the sorted documents
        reranked_docs = [doc for doc, score in sorted_doc_scores]
        
        return RerankResponse(reranked_documents=reranked_docs)
        
    except Exception as e:
        logger.error(f"Failed to re-rank documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while re-ranking: {str(e)}"
        )

@app.get("/health")
def health_check():
    """Health check endpoint to verify service status and loaded model."""
    model_name = model_state.get("model_name", "None")
    return {"status": "ok", "model_loaded": "rerank_model" in model_state, "model_name": model_name}