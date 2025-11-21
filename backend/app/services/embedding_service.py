# FILE: backend/app/services/embedding_service.py
import os
import httpx
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

# --- Configuration ---
# PHOENIX PROTOCOL: Transition to AI Core Service
# We now point to the unified container. 
# If env var is missing, we default to the standard docker-compose hostname.
AI_CORE_BASE_URL = os.getenv("AI_CORE_URL", "http://ai-core-service:8000")

# --- Global Client Initialization ---
# Persistent client for performance. 
# Reduced timeout from 120s to 30s because the new local model is faster.
GLOBAL_SYNC_HTTP_CLIENT = httpx.Client(timeout=30.0)

def generate_embedding(text: str, language: Optional[str] = None) -> List[float]:
    """
    Generates a vector embedding using the centralized AI Core Service.
    """
    # The new router is located at /embeddings/generate
    endpoint = f"{AI_CORE_BASE_URL}/embeddings/generate"
    
    try:
        # We intentionally ignore the 'language' parameter for now 
        # because ai-core-service handles optimization internally.
        response = GLOBAL_SYNC_HTTP_CLIENT.post(
            endpoint, 
            json={"text_content": text}, 
        )
        
        response.raise_for_status()
        data = response.json()
        
        if "embedding" not in data or not isinstance(data["embedding"], list):
            raise ValueError(f"Invalid response format from AI Core at {endpoint}")
            
        return data["embedding"]
        
    except httpx.RequestError as e:
        # This handles "Connection refused" if the service is down
        logger.error(f"❌ [Embedding Service] Could not connect to AI Core at {AI_CORE_BASE_URL}. Error: {e}")
        raise Exception("AI Core Service unavailable.") from e
        
    except httpx.HTTPStatusError as e:
        # This handles 400/500 errors from the service
        logger.error(f"❌ [Embedding Service] AI Core returned error {e.response.status_code}: {e.response.text}")
        raise Exception(f"AI Core error: {e.response.status_code}") from e
        
    except Exception as e:
        logger.error(f"❌ [Embedding Service] Unexpected error: {e}")
        raise Exception("Embedding generation failed.") from e