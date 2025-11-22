import os
import httpx
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)

# Configuration
# Points to the new Unified Juristi AI Core
AI_CORE_URL = os.getenv("AI_CORE_URL", "http://ai-core-service:8000")

class AlbanianNERService:
    """
    Service responsible for detecting Named Entities (PII) using the centralized Juristi AI Core.
    """
    def __init__(self):
        self.timeout = 10.0

    def extract_entities(self, text: str) -> List[Tuple[str, str, int]]:
        """
        Extracts entities from the text using the AI Core.
        
        Returns:
            List of (entity_text, entity_label, start_char_index) tuples.
        """
        if not text:
            return []
            
        try:
            # Call the Unified Core
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{AI_CORE_URL}/ner/extract",
                    json={"text": text}
                )
                response.raise_for_status()
                data = response.json()
                
                raw_entities = data.get("entities", [])
                
                results = []
                for ent in raw_entities:
                    name = ent.get("text", "")
                    label = ent.get("label", "UNKNOWN")
                    
                    # COMPATIBILITY FIX:
                    # The AI Core returns the entity text, but legacy backend expects the start index.
                    # We calculate it here. Note: This finds the *first* occurrence. 
                    # For a more robust solution later, AI Core should return indices.
                    start_index = text.find(name) 
                    
                    results.append((name, label, start_index))
                    
                return results
                
        except Exception as e:
            logger.error(f"❌ [NER Service] Failed to extract entities from AI Core: {e}")
            # Fail gracefully: return empty list so the document process doesn't crash
            return []
    
    def get_albanian_placeholder(self, entity_label: str) -> str:
        """ 
        Maps the entity label (Spacy or Custom) to an Albanian placeholder. 
        """
        # Map standard Spacy labels to your Albanian requirements
        placeholders = {
            # Standard Spacy Labels
            "PER": "[EMRI_PERSONI_ANONIMIZUAR]",
            "PERSON": "[EMRI_PERSONI_ANONIMIZUAR]",
            "ORG": "[ORGANIZATË_ANONIMIZUAR]",
            "LOC": "[VENDNDODHJA_ANONIMIZUAR]",
            "GPE": "[VENDNDODHJA_ANONIMIZUAR]",
            
            # Legacy / Custom Labels
            "PERSON_NAME": "[EMRI_PERSONI_ANONIMIZUAR]",
            "CASE_NUMBER": "[NUMRI_ÇËSHTJES_ANONIMIZUAR]",
            "ORGANIZATION": "[ORGANIZATË_ANONIMIZUAR]",
            "LOCATION": "[VENDNDODHJA_ANONIMIZUAR]",
        }
        return placeholders.get(entity_label, f"[{entity_label}_ANONIMIZUAR]")
        
# --- Global Instance ---
ALBANIAN_NER_SERVICE = AlbanianNERService()