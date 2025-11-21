from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from services.ner_manager import ner_manager

router = APIRouter()

class NerRequest(BaseModel):
    text: str

class Entity(BaseModel):
    text: str
    label: str

class NerResponse(BaseModel):
    entities: List[Entity]

@router.post("/extract", response_model=NerResponse)
async def extract_entities(request: NerRequest):
    """
    Extracts named entities (Persons, Locations, Orgs) from text.
    """
    try:
        raw_entities = ner_manager.extract_entities(request.text)
        # Convert dicts back to Pydantic models
        valid_entities = [Entity(text=e["text"], label=e["label"]) for e in raw_entities]
        return NerResponse(entities=valid_entities)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))