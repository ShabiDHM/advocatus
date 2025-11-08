# embedding_service/main.py

import os
import logging
from contextlib import asynccontextmanager
from typing import List
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

# --- Model & Application State ---
model_state = {}

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Lifespan Manager for Model Loading ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- MODEL-AGILE IMPLEMENTATION ---
    # Read the model name from an environment variable.
    # Default to the current production model for backward compatibility.
    model_name = os.getenv("MODEL_NAME", "paraphrase-multilingual-mpnet-base-v2")
    
    logger.info(f"--- [Embedding Service] Attempting to load model: {model_name} ---")
    
    try:
        model_state["embedding_model"] = SentenceTransformer(model_name)
        model_state["model_name"] = model_name
        logger.info(f"--- [Embedding Service] Model '{model_name}' loaded successfully. ---")
    except Exception as e:
        logger.error(f"--- [Embedding Service] CRITICAL: Failed to load model '{model_name}'. Error: {e} ---")
    
    yield
    
    logger.info("--- [Embedding Service] Shutting down... ---")
    model_state.clear()
    logger.info("--- [Embedding Service] Shutdown complete. ---")

# --- FastAPI App Initialization ---
app = FastAPI(lifespan=lifespan)

# --- Pydantic Models for API ---
class EmbeddingRequest(BaseModel):
    text_content: str

class EmbeddingResponse(BaseModel):
    embedding: List[float]

# --- API Endpoints ---
@app.post("/generate", response_model=EmbeddingResponse)
def generate_embedding_endpoint(request: EmbeddingRequest):
    model = model_state.get("embedding_model")
    if not model:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Embedding model is not available or failed to load."
        )
    
    try:
        embedding = model.encode(request.text_content).tolist()
        return EmbeddingResponse(embedding=embedding)
    except Exception as e:
        logger.error(f"Failed to generate embedding: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while generating the embedding: {str(e)}"
        )

@app.get("/health")
def health_check():
    """Health check endpoint to verify service status and loaded model."""
    model_name = model_state.get("model_name", "None")
    return {"status": "ok", "model_loaded": "embedding_model" in model_state, "model_name": model_name}