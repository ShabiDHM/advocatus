# FILE: backend/app/services/embedding_service.py
# PHOENIX PROTOCOL - EMBEDDING CLIENT V7.0 (ALWAYS ALBANIAN + FULL LOGGING)
# 1. FIXED: Force language to 'sq' – the embedding service is Albanian‑only.
# 2. ADDED: DEBUG logging of response status and keys on every call.
# 3. ADDED: Fallback extraction from 'embedding', 'vector', 'data[0].embedding', 'embeddings[0]'.
# 4. STATUS: Every embedding call is logged; failure reasons are explicit.

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
LEGACY_URL = str(os.getenv("AI_CORE_URL", "http://ai-core-service:8000"))

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
    Generates a vector embedding using the Albanian‑optimised model.
    The `language` parameter is IGNORED – we force 'sq' for compatibility.
    """
    if not text or not text.strip():
        logger.debug("⏭️ [Embedding] Empty text – returning []")
        return []

    if not ACTIVE_EMBEDDING_URL:
        logger.error("❌ [Embedding] ACTIVE_EMBEDDING_URL is not configured.")
        return []

    base_url = ACTIVE_EMBEDDING_URL.rstrip("/")
    endpoint = f"{base_url}/embeddings/generate"

    # --- PHOENIX: FORCE LANGUAGE TO 'sq' ---
    # The embedding service is trained on Albanian text; passing 'en' may break it.
    payload = {
        "text_content": text,
        "language": "sq"  # 🛡️ Hardcoded – always use Albanian model
    }

    MAX_RETRIES = 15
    BASE_DELAY = 2
    MAX_DELAY = 30

    for attempt in range(MAX_RETRIES):
        try:
            response = GLOBAL_SYNC_HTTP_CLIENT.post(endpoint, json=payload)
            response.raise_for_status()

            data = response.json()
            
            # --- PHOENIX: Log response summary for debugging ---
            logger.debug(f"🔍 [Embedding] Response status={response.status_code}, keys={list(data.keys())}")
            if len(text) > 100:
                logger.debug(f"🔍 [Embedding] Text preview: {text[:100]}...")

            # --- Try multiple possible field names ---
            if "embedding" in data and isinstance(data["embedding"], list):
                return data["embedding"]
            
            if "vector" in data and isinstance(data["vector"], list):
                return data["vector"]
            
            if "data" in data and isinstance(data["data"], list) and len(data["data"]) > 0:
                first = data["data"][0]
                if "embedding" in first and isinstance(first["embedding"], list):
                    return first["embedding"]
                if "vector" in first and isinstance(first["vector"], list):
                    return first["vector"]
            
            if "embeddings" in data and isinstance(data["embeddings"], list) and len(data["embeddings"]) > 0:
                return data["embeddings"][0]

            # --- If we get here, the response format is unknown ---
            logger.error(f"❌ [Embedding] Unknown response format from {endpoint}. Keys: {list(data.keys())}")
            logger.error(f"❌ [Embedding] Response preview: {str(data)[:200]}")
            return []

        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as e:
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
                # Log response body if possible
                try:
                    logger.error(f"❌ [Embedding] Response body: {e.response.text[:500]}")
                except:
                    pass
                return []

        except Exception as e:
            logger.error(f"❌ [Embedding] Unexpected error: {e}", exc_info=True)
            return []

    return []