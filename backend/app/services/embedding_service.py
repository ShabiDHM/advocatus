# backend/app/services/embedding_service.py
# DEFINITIVE VERSION 7.0: Final Final Pylance Fix
#   - Resolves all Pylance assignment errors by using a local assert before assignment.

import os
import httpx
from typing import List, Optional

# --- Configuration ---
# Standard (Multilingual) Embedding Service
STANDARD_EMBEDDING_SERVICE_URL: str | None = os.getenv("EMBEDDING_SERVICE_URL")
if not STANDARD_EMBEDDING_SERVICE_URL:
    raise EnvironmentError("EMBEDDING_SERVICE_URL environment variable is not set.")

# The application guarantees STANDARD_EMBEDDING_SERVICE_URL is str if it reaches here.
# NOTE: We remove the global assert to fix the Pylance issue.

# Albanian RAG Embedding Service (Specialized)
ALBANIAN_EMBEDDING_SERVICE_URL: str | None = os.getenv("ALBANIAN_EMBEDDING_SERVICE_URL")

# --- Global Client Initialization for Performance ---
# Use a persistent, unverified synchronous client for reliable internal Docker network calls.
GLOBAL_SYNC_HTTP_CLIENT = httpx.Client(verify=False, timeout=120.0)

def generate_embedding(text: str, language: Optional[str] = None) -> List[float]:
    """
    Generates a vector embedding for a given text. Routes to the specialized Albanian
    service if the language is 'albanian' and the service URL is configured.
    """
    # 1. Determine the appropriate service URL
    service_url: str # Target type is str
    log_prefix: str
    
    if language and language.lower() == 'albanian' and ALBANIAN_EMBEDDING_SERVICE_URL:
        # Assertion to satisfy Pylance that the value is not None before assignment.
        assert ALBANIAN_EMBEDDING_SERVICE_URL is not None
        service_url = ALBANIAN_EMBEDDING_SERVICE_URL
        log_prefix = "Albanian"
    else:
        # Assertion to satisfy Pylance that the value is not None before assignment.
        assert STANDARD_EMBEDDING_SERVICE_URL is not None
        service_url = STANDARD_EMBEDDING_SERVICE_URL
        log_prefix = "Standard"
        
    # 2. Call the service using the persistent client
    try:
        # The endpoint in the microservice is assumed to be "/generate"
        endpoint = f"{service_url}/generate"
        
        response = GLOBAL_SYNC_HTTP_CLIENT.post(
            endpoint, 
            json={"text_content": text}, 
        )
        
        # Raise an exception if the service returned an error
        response.raise_for_status()
        
        data = response.json()
        
        if "embedding" not in data or not isinstance(data["embedding"], list):
            raise ValueError(f"[{log_prefix} Embedding] Invalid response format from service at {service_url}.")
            
        return data["embedding"]
        
    except httpx.RequestError as e:
        print(f"!!! CRITICAL: [{log_prefix} Embedding] Could not connect to service at {service_url}. Reason: {e}")
        raise Exception(f"Failed to connect to {log_prefix} embedding service.") from e
    except ValueError as e:
        print(f"!!! CRITICAL: [{log_prefix} Embedding] Invalid data received. Reason: {e}")
        raise Exception(f"Invalid response from {log_prefix} embedding service.") from e
    except Exception as e:
        print(f"!!! CRITICAL: [{log_prefix} Embedding] Unknown error. Reason: {e}")
        raise Exception(f"Unknown error in {log_prefix} embedding service.") from e