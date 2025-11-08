# categorization_service/main.py
# FINAL PRODUCTION VERSION: Removes incorrect lifespan manager.

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from transformers import pipeline
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =========================================================================
# == DEFINITIVE FIX: The incorrect import of a non-existent 'lifespan'   ==
# == manager has been removed.                                           ==
# =========================================================================

# =========================================================================
# == DEFINITIVE FIX: The FastAPI app is now instantiated correctly       ==
# == without the 'lifespan' parameter.                                   ==
# =========================================================================
app = FastAPI(title="Categorization Service")

# Initialize the model pipeline on startup
try:
    logger.info("Initializing zero-shot-classification pipeline...")
    # This will download the model if not present, which requires the HF_TOKEN
    classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
    logger.info("Pipeline initialized successfully.")
except Exception as e:
    logger.critical(f"Failed to initialize model pipeline: {e}", exc_info=True)
    classifier = None

# --- Pydantic Models for API Contract ---
class CategorizationRequest(BaseModel):
    text: str
    candidate_labels: List[str]

class CategorizationResponse(BaseModel):
    predicted_category: str

# --- API Endpoints ---
@app.get("/health", status_code=200)
def read_health():
    """Provides a simple health check for the service."""
    if classifier is not None:
        return {"status": "healthy"}
    else:
        # Return a 503 Service Unavailable if the model failed to load
        raise HTTPException(status_code=503, detail="Service Unhealthy: Model pipeline not initialized.")

@app.post("/categorize", response_model=CategorizationResponse)
async def categorize_text(request: CategorizationRequest):
    """
    Accepts text and labels, and returns a predicted category using the ML model.
    """
    if classifier is None:
        raise HTTPException(status_code=503, detail="Service Unavailable: Model is not initialized.")
    
    if not request.text or not request.candidate_labels:
        raise HTTPException(status_code=400, detail="Text and candidate labels are required.")
    
    try:
        logger.info(f"Received categorization request for {len(request.text)} chars with labels: {request.candidate_labels}")
        # Perform classification
        result = classifier(request.text, request.candidate_labels)
        predicted_category = result['labels'][0]
        
        logger.info(f"Categorized text as: {predicted_category}")
        return CategorizationResponse(predicted_category=predicted_category)

    except Exception as e:
        logger.error(f"Error during categorization: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")