# FILE: backend/app/services/embedding_service.py
# PHOENIX PROTOCOL - VECTOR UNIFICATION
# 1. CRITICAL FIX: Forces ALL embedding generation to use the STANDARD_EMBEDDING_SERVICE.
# 2. RATIONALE: Prevents dimension mismatches (512 vs 768) between different containers.
# 3. COMPATIBILITY: The standard 'paraphrase-multilingual-mpnet-base-v2' supports Albanian perfectly.

import os
import httpx
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

# --- Configuration ---
# We rely on the Standard Service as the Single Source of Truth for vectors.
STANDARD_EMBEDDING_SERVICE_URL: str | None = os.getenv("EMBEDDING_SERVICE_URL")
if not STANDARD_EMBEDDING_SERVICE_URL:
    raise EnvironmentError("EMBEDDING_SERVICE_URL environment variable is not set.")

# We deliberately ignore the specialized Albanian URL for embeddings to ensure
# all vectors live in the same mathematical space (768 dimensions).
# ALBANIAN_EMBEDDING_SERVICE_URL = os.getenv("ALBANIAN_EMBEDDING_SERVICE_URL")

# --- Global Client Initialization ---
# Persistent client for performance
GLOBAL_SYNC_HTTP_CLIENT = httpx.Client(verify=False, timeout=120.0)

def generate_embedding(text: str, language: Optional[str] = None) -> List[float]:
    """
    Generates a vector embedding for a given text.
    
    PHOENIX FIX: Routes EVERYTHING to the Standard Service.
    This guarantees that 'ingestion' and 'query' vectors are always compatible.
    """
    # Always use the Standard URL
    assert STANDARD_EMBEDDING_SERVICE_URL is not None
    service_url = STANDARD_EMBEDDING_SERVICE_URL
    log_prefix = "Standard (Forced)"
    
    # 2. Call the service
    try:
        endpoint = f"{service_url}/generate"
        
        response = GLOBAL_SYNC_HTTP_CLIENT.post(
            endpoint, 
            json={"text_content": text}, 
        )
        
        response.raise_for_status()
        data = response.json()
        
        if "embedding" not in data or not isinstance(data["embedding"], list):
            raise ValueError(f"[{log_prefix}] Invalid response format from {service_url}.")
            
        return data["embedding"]
        
    except httpx.RequestError as e:
        logger.critical(f"!!! [{log_prefix}] Could not connect to embedding service at {service_url}. Error: {e}")
        raise Exception("Embedding service unavailable.") from e
    except Exception as e:
        logger.critical(f"!!! [{log_prefix}] Error generating embedding: {e}")
        raise Exception("Embedding generation failed.") from e