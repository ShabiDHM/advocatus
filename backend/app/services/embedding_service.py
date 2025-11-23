# FILE: backend/app/services/embedding_service.py
# PHOENIX PROTOCOL - CLIENT MODE
# Status: Lightweight Client talking to Juristi AI Core.
# Timeout: 60s (Optimized for BAAI/bge-m3 large model)

import os
import httpx
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

# Points to the unified AI container
AI_CORE_BASE_URL = os.getenv("AI_CORE_URL", "http://ai-core-service:8000")

# Persistent client for performance
GLOBAL_SYNC_HTTP_CLIENT = httpx.Client(timeout=60.0)

def generate_embedding(text: str, language: Optional[str] = None) -> List[float]:
    """
    Generates a vector embedding by calling the centralized Juristi AI Core.
    """
    endpoint = f"{AI_CORE_BASE_URL}/embeddings/generate"
    
    try:
        # We send the text to the AI Core
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
        logger.error(f"❌ [Embedding Service] Connection Failed: {e}")
        raise Exception("AI Core Service unavailable.") from e
        
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ [Embedding Service] AI Core Error {e.response.status_code}: {e.response.text}")
        raise Exception(f"AI Core error: {e.response.status_code}") from e
        
    except Exception as e:
        logger.error(f"❌ [Embedding Service] Unexpected error: {e}")
        raise Exception("Embedding generation failed.") from e