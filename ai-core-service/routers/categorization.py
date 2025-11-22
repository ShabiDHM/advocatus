from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from services.categorization_manager import categorization_manager

router = APIRouter()

class CategorizationRequest(BaseModel):
    text: str
    candidate_labels: List[str]

class CategorizationResponse(BaseModel):
    predicted_category: str

@router.post("/categorize", response_model=CategorizationResponse)
async def categorize_text(request: CategorizationRequest):
    """
    Classifies text into categories (zero-shot).
    """
    try:
        category = categorization_manager.categorize_text(
            request.text, 
            request.candidate_labels
        )
        return CategorizationResponse(predicted_category=category)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))