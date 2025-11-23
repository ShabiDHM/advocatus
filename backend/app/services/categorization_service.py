# FILE: backend/app/services/categorization_service.py
# PHOENIX PROTOCOL - FAULT TOLERANT CLASSIFICATION
# 1. PRIMARY: Juristi AI Core (Zero-Shot Classification).
# 2. FALLBACK: Local LLM (Ollama) if Core is busy/down.
# 3. RESULT: Minimizes "Unknown" labels.

import os
import httpx
import logging
import json
from typing import List, Optional

logger = logging.getLogger(__name__)

# Configuration
AI_CORE_URL = os.getenv("AI_CORE_URL", "http://ai-core-service:8000")
LOCAL_LLM_URL = os.environ.get("LOCAL_LLM_URL", "http://local-llm:11434/api/chat")
LOCAL_MODEL_NAME = "llama3"

class CategorizationService:
    """
    Service responsible for document classification.
    Uses Hybrid approach: Specialized Model -> General LLM Fallback.
    """
    def __init__(self):
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

    def _categorize_with_ollama(self, text: str, labels: List[str]) -> Optional[str]:
        """Fallback: Ask Local Llama3 to classify the text."""
        logger.info("⚠️ Switching to LOCAL LLM for categorization...")
        try:
            truncated_text = text[:1000] # Header contains most clues
            labels_str = ", ".join([f'"{l}"' for l in labels])
            
            prompt = f"""
            Classify the following document into exactly one of these categories: [{labels_str}].
            
            Document Text:
            {truncated_text}
            
            Return ONLY the category name as a JSON string. Example: {{"category": "kontratë"}}
            """
            
            payload = {
                "model": LOCAL_MODEL_NAME,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "format": "json"
            }
            
            with httpx.Client(timeout=20.0) as client:
                response = client.post(LOCAL_LLM_URL, json=payload)
                response.raise_for_status()
                data = response.json()
                content = data.get("message", {}).get("content", "")
                
                result = json.loads(content)
                cat = result.get("category", "").lower()
                
                # Verify result is in allowed list
                if any(l in cat for l in labels):
                    return cat
                return None
                
        except Exception as e:
            logger.error(f"❌ Local LLM Categorization failed: {e}")
            return None

    def categorize_document(self, text: str, custom_labels: Optional[List[str]] = None) -> str:
        """
        Main entry point. Tries AI Core first, then Ollama.
        """
        if not text:
            return "unknown"
            
        labels = custom_labels if custom_labels else self.default_labels
        
        # TIER 1: AI CORE (Specialized Model)
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{AI_CORE_URL}/categorization/categorize",
                    json={"text": text, "candidate_labels": labels}
                )
                response.raise_for_status()
                data = response.json()
                return data.get("predicted_category", "uncategorized")
                
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            logger.warning(f"⚠️ AI Core unavailable ({e}). Attempting fallback.")
        except Exception as e:
            logger.error(f"❌ AI Core Error: {e}")

        # TIER 2: LOCAL LLM FALLBACK
        fallback_result = self._categorize_with_ollama(text, labels)
        if fallback_result:
            return fallback_result

        return "uncategorized"

# --- Global Instance ---
CATEGORIZATION_SERVICE = CategorizationService()