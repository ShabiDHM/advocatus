# FILE: backend/app/services/embedding_service.py
# PHOENIX PROTOCOL - EMBEDDING CLIENT V5.0 (ENV-AWARE)
# 1. CRITICAL FIX: Detects the correct URL from your .env file (Albanian vs Standard).
# 2. ROBUSTNESS: Logs the exact connection target to debugging.

import os
import httpx
import logging
import time
from typing import List, Optional

logger = logging.getLogger(__name__)

# --- URL RESOLUTION LOGIC ---
# We check which service is enabled in the .env and pick the right URL.
ALBANIAN_ENABLED = os.getenv("ALBANIAN_AI_ENABLED", "false").lower() == "true"
ALBANIAN_URL = os.getenv("ALBANIAN_EMBEDDING_SERVICE_URL")
STANDARD_URL = os.getenv("EMBEDDING_SERVICE_URL")
LEGACY_URL = os.getenv("AI_CORE_URL", "http://ai-core-service:8000")

if ALBANIAN_ENABLED and ALBANIAN_URL:
    ACTIVE_EMBEDDING_URL = ALBANIAN_URL
    logger.info(f"🔌 [Embedding] Connected to ALBANIAN Service: {ACTIVE_EMBEDDING_URL}")
elif STANDARD_URL:
    ACTIVE_EMBEDDING_URL = STANDARD_URL
    logger.info(f"🔌 [Embedding] Connected to STANDARD Service: {ACTIVE_EMBEDDING_URL}")
else:
    ACTIVE_EMBEDDING_URL = LEGACY_URL
    logger.warning(f"⚠️ [Embedding] Using LEGACY default: {ACTIVE_EMBEDDING_URL}")

# Persistent Client
GLOBAL_SYNC_HTTP_CLIENT = httpx.Client(
    timeout=60.0, 
    limits=httpx.Limits(max_keepalive_connections=20, max_connections=50)
)

def generate_embedding(text: str, language: Optional[str] = None) -> List[float]:
    """
    Generates a vector embedding using the correctly resolved Microservice URL.
    """
    if not text or not text.strip():
        return []

    # Construct endpoint based on the resolved base URL
    # Note: Adjust '/embeddings/generate' if your specific microservice uses a different path
    # Standard Juristi/Phoenix microservices use /embeddings/generate or /v1/embeddings
    endpoint = f"{ACTIVE_EMBEDDING_URL}/embeddings/generate"
    
    payload = {
        "text_content": text,
        "language": language or "sq" # Default to Albanian per your config
    }
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = GLOBAL_SYNC_HTTP_CLIENT.post(endpoint, json=payload)
            response.raise_for_status()
            
            data = response.json()
            
            # Handle different response formats (some return 'embedding', some 'data')
            if "embedding" in data:
                return data["embedding"]
            elif "data" in data and isinstance(data["data"], list):
                return data["data"][0]["embedding"]
            else:
                logger.error(f"❌ [Embedding] Unknown response format from {endpoint}: {data.keys()}")
                return []
            
        except httpx.HTTPError as e:
            logger.warning(f"⚠️ [Embedding] Connection failed to {endpoint}: {e} (Attempt {attempt+1})")
            time.sleep(1)
        except Exception as e:
            logger.error(f"❌ [Embedding] Unexpected error: {e}")
            return []
            
    logger.error(f"❌ [Embedding] FAILED after {max_retries} attempts. URL: {endpoint}")
    return []