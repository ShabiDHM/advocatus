# FILE: backend/app/services/embedding_service.py
# PHOENIX PROTOCOL - EMBEDDING CLIENT V6.1 (TYPE-SAFE RESILIENCE)
# 1. FIX: Resolved Pylance 'NoneType' attribute error for rstrip.
# 2. CRITICAL FIX: Implemented Exponential Backoff to survive 300s AI startup times.
# 3. LOGIC: Retries connection up to 15 times with increasing delays (2s -> 30s).

import os
import httpx
import logging
import time
from typing import List, Optional

logger = logging.getLogger(__name__)

# --- URL RESOLUTION LOGIC ---
ALBANIAN_ENABLED = os.getenv("ALBANIAN_AI_ENABLED", "false").lower() == "true"
ALBANIAN_URL = os.getenv("ALBANIAN_EMBEDDING_SERVICE_URL")
STANDARD_URL = os.getenv("EMBEDDING_SERVICE_URL")
# Ensure LEGACY_URL is always a string
LEGACY_URL = str(os.getenv("AI_CORE_URL", "http://ai-core-service:8000"))

# Initialize with the legacy default to ensure it is never None (satisfies Pylance)
ACTIVE_EMBEDDING_URL: str = LEGACY_URL

if ALBANIAN_ENABLED and ALBANIAN_URL:
    ACTIVE_EMBEDDING_URL = ALBANIAN_URL
    logger.info(f"🔌 [Embedding] Configured for ALBANIAN Service: {ACTIVE_EMBEDDING_URL}")
elif STANDARD_URL:
    ACTIVE_EMBEDDING_URL = STANDARD_URL
    logger.info(f"🔌 [Embedding] Configured for STANDARD Service: {ACTIVE_EMBEDDING_URL}")
else:
    logger.warning(f"⚠️ [Embedding] Using LEGACY default: {ACTIVE_EMBEDDING_URL}")

# Persistent Client Configuration
GLOBAL_SYNC_HTTP_CLIENT = httpx.Client(
    timeout=60.0, 
    limits=httpx.Limits(max_keepalive_connections=20, max_connections=50)
)

def generate_embedding(text: str, language: Optional[str] = None) -> List[float]:
    """
    Generates a vector embedding using the correctly resolved Microservice URL.
    Includes Exponential Backoff to handle cold starts (up to 5 mins).
    """
    if not text or not text.strip():
        return []

    # Final Type Guard for Pylance/Runtime
    if not ACTIVE_EMBEDDING_URL:
        logger.error("❌ [Embedding] ACTIVE_EMBEDDING_URL is not configured.")
        return []

    # Ensure URL is clean and constructed correctly
    base_url = ACTIVE_EMBEDDING_URL.rstrip("/")
    endpoint = f"{base_url}/embeddings/generate"
    
    payload = {
        "text_content": text,
        "language": language or "sq" # Default to Albanian per config
    }
    
    # PHOENIX PROTOCOL: RESILIENCE SETTINGS
    # Strategy: Wait long enough for the 300s start_period of ai-core-service
    MAX_RETRIES = 15
    BASE_DELAY = 2   
    MAX_DELAY = 30   
    
    for attempt in range(MAX_RETRIES):
        try:
            response = GLOBAL_SYNC_HTTP_CLIENT.post(endpoint, json=payload)
            response.raise_for_status()
            
            data = response.json()
            
            if "embedding" in data:
                return data["embedding"]
            elif "data" in data and isinstance(data["data"], list):
                return data["data"][0]["embedding"]
            else:
                logger.error(f"❌ [Embedding] Unknown response format from {endpoint}: {data.keys()}")
                return []
            
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as e:
            # Service might still be loading models (300s start_period)
            sleep_time = min(BASE_DELAY * (2 ** attempt), MAX_DELAY)
            
            if attempt < MAX_RETRIES - 1:
                logger.warning(
                    f"⏳ [Embedding] Service unreachable (Attempt {attempt+1}/{MAX_RETRIES}). "
                    f"Retrying in {sleep_time}s... Error: {e}"
                )
                time.sleep(sleep_time)
            else:
                logger.error(f"❌ [Embedding] CRITICAL: Service unreachable after {MAX_RETRIES} attempts.")
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code in [502, 503, 504]:
                sleep_time = min(BASE_DELAY * (2 ** attempt), MAX_DELAY)
                logger.warning(f"⚠️ [Embedding] Gateway Error {e.response.status_code}. Retrying in {sleep_time}s...")
                time.sleep(sleep_time)
            else:
                logger.error(f"❌ [Embedding] HTTP Error {e.response.status_code}: {e}")
                return []
                
        except Exception as e:
            logger.error(f"❌ [Embedding] Unexpected error: {e}")
            return []
            
    return []