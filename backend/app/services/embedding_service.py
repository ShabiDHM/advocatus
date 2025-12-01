# FILE: backend/app/services/embedding_service.py
# PHOENIX PROTOCOL - EMBEDDING CLIENT V4.2
# 1. ROBUSTNESS: Added retry logic (3 attempts) to handle local server load.
# 2. FEATURE: Forwards 'language' parameter to AI Core.
# 3. PERFORMANCE: Increased connection pool limits for parallel indexing.

import os
import httpx
import logging
import time
from typing import List, Optional

logger = logging.getLogger(__name__)

# Points to the unified AI container (Local 16GB Server)
AI_CORE_BASE_URL = os.getenv("AI_CORE_URL", "http://ai-core-service:8000")

# Persistent client for performance
# Increased pool size to handle parallel document processing threads (6 threads * 10 chunks)
GLOBAL_SYNC_HTTP_CLIENT = httpx.Client(
    timeout=60.0, 
    limits=httpx.Limits(max_keepalive_connections=20, max_connections=50)
)

def generate_embedding(text: str, language: Optional[str] = None) -> List[float]:
    """
    Generates a vector embedding by calling the centralized Juristi AI Core.
    Retries up to 3 times on failure to ensure stability under load.
    """
    if not text or not text.strip():
        logger.warning("[Embedding] Empty text provided. Skipping.")
        return []

    endpoint = f"{AI_CORE_BASE_URL}/embeddings/generate"
    payload = {
        "text_content": text,
        "language": language or "standard"
    }
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = GLOBAL_SYNC_HTTP_CLIENT.post(endpoint, json=payload)
            response.raise_for_status()
            
            data = response.json()
            
            if "embedding" not in data or not isinstance(data["embedding"], list):
                raise ValueError(f"Invalid response format from AI Core at {endpoint}")
                
            return data["embedding"]
            
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            # Log warning but retry
            logger.warning(f"⚠️ [Embedding] Attempt {attempt+1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(1) # Brief cool-off to let CPU breathe
            else:
                logger.error(f"❌ [Embedding] Critical Failure after retries for text len {len(text)}")
                return []
                
        except Exception as e:
            logger.error(f"❌ [Embedding] Unexpected error: {e}")
            return []
            
    return []