import os
import httpx
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

# Configuration
# Points to the new Unified Juristi AI Core
AI_CORE_URL = os.getenv("AI_CORE_URL", "http://ai-core-service:8000")

class CategorizationService:
    """
    Service responsible for document classification using the centralized Juristi AI Core.
    Replaces the legacy categorization-microservice.
    """
    def __init__(self):
        # Categorization (BART Model) can be slow on large texts, so we use a higher timeout
        self.timeout = 30.0
        
        # Standard Legal Categories for Kosovo Context
        self.default_labels = [
            "kontratë",                 # Contract
            "vendim gjyqësor",          # Court Decision
            "ligj / akt normativ",      # Law / Regulation
            "padi / kërkesë padi",      # Lawsuit
            "shkresë zyrtare",          # Official Correspondence
            "faturë / dokument financiar" # Invoice
        ]

    def categorize_document(self, text: str, custom_labels: Optional[List[str]] = None) -> str:
        """
        Sends text to Juristi AI Core for Zero-Shot Classification.
        """
        if not text:
            return "unknown"
            
        labels = custom_labels if custom_labels else self.default_labels
        
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{AI_CORE_URL}/categorization/categorize",
                    json={
                        "text": text, 
                        "candidate_labels": labels
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                return data.get("predicted_category", "uncategorized")
                
        except httpx.TimeoutException:
            logger.error("❌ [Categorization Service] Timeout connecting to AI Core.")
            return "uncategorized_timeout"
        except Exception as e:
            logger.error(f"❌ [Categorization Service] Failed to categorize document: {e}")
            return "uncategorized_error"

# --- Global Instance ---
CATEGORIZATION_SERVICE = CategorizationService()