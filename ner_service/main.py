# ner_service/main.py
# DEFINITIVE MISSION-COMPLETE VERSION V12.1: Adds missing Dict import.

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Any, Dict # <-- THE CRITICAL FIX IS HERE
import spacy
import logging

app = FastAPI()

# Configure basic logging
logging.basicConfig(level=logging.INFO)

# --- Load the spaCy model ---
try:
    nlp = spacy.load("xx_ent_wiki_sm")
    logging.info(f"✅ NER model 'xx_ent_wiki_sm' loaded successfully. Type: {type(nlp)}")
except Exception as e:
    logging.critical(f"--- [NER Service] CRITICAL: An exception occurred during model load: {e} ---", exc_info=True)
    nlp = None

class NerRequest(BaseModel):
    text: str

class Entity(BaseModel):
    text: str
    label: str

class NerResponse(BaseModel):
    entities: List[Entity]

@app.post("/extract", response_model=NerResponse)
def extract_entities(request: NerRequest):
    if not nlp:
        raise HTTPException(status_code=503, detail="NER model is not available due to a startup error.")
    doc = nlp(request.text)
    entities = [Entity(text=ent.text, label=ent.label_) for ent in doc.ents]
    return NerResponse(entities=entities)

# --- Hardened Health Check ---
@app.get("/health")
def health_check():
    if nlp is not None:
        model_name = nlp.meta.get('name', 'unknown')
        logging.info(f"Health check PASSED. Model '{model_name}' is loaded.")
        return {"status": "ok", "model_loaded": model_name}
    
    logging.warning("Health check FAILED. The 'nlp' object is None.")
    raise HTTPException(status_code=503, detail="Model is not loaded.")

# --- Diagnostic Endpoint ---
@app.get("/debug-model")
def debug_model() -> Dict[str, Any]:
    """A temporary endpoint to inspect the loaded nlp object."""
    if not nlp:
        return {"error": "NLP object is not loaded."}
    
    return {
        "nlp_object_type": str(type(nlp)),
        "model_meta": nlp.meta,
        "pipeline_names": nlp.pipe_names,
        "is_ner_in_pipeline": "ner" in nlp.pipe_names
    }