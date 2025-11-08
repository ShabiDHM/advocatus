# FILE: backend/app/core/config.py
# DEFINITIVE VERSION 12.0: (PHOENIX PROTOCOL: FINAL CONFIGURATION LOCK)
# 1. CRITICAL FIX: The explicit 'COOKIE_DOMAIN' setting has been completely removed.
#    This is the definitive root cause of the 401 refresh error in the cross-domain
#    architecture. By removing it, the browser will correctly scope the refresh token
#    cookie to the API's own domain, allowing the refresh mechanism to function.

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional

class Settings(BaseSettings):
    """
    Defines the application's configuration settings.
    """
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    # --- Database & Broker ---
    DATABASE_URI: str = ""
    REDIS_URL: str = ""
    
    # --- Auth ---
    SECRET_KEY: str = "PHOENIX_PROTOCOL_FINAL_STABLE_SECRET_KEY_A9B3E1C5D7F2A4B9E1C5D7F2A4B9E1C5D7F2A4B9E1C5D7F2A4B9E1C5D7F2A4B9"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 10080
    
    # --- PHOENIX PROTOCOL FIX: COOKIE_DOMAIN REMOVED ---
    # COOKIE_DOMAIN: Optional[str] = None # This line is intentionally commented out or removed.

    # --- CORS Configuration ---
    BACKEND_CORS_ORIGINS: List[str] = [
        "https://advocatus-ai.vercel.app",
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    # --- BYOK ENCRYPTION SECRETS (Phase 3) ---
    ENCRYPTION_SALT: str = ""
    ENCRYPTION_PASSWORD: str = ""

    # --- External Services ---
    B2_KEY_ID: str = ""
    B2_APPLICATION_KEY: str = ""
    B2_ENDPOINT_URL: str = ""
    B2_BUCKET_NAME: str = ""
    GROQ_API_KEY: str = ""
    HF_TOKEN: str = ""
    GROQ_MODEL: str = "" 

    # --- Internal AI Services ---
    EMBEDDING_MODEL: str = ""
    CHROMA_HOST: str = ""
    CHROMA_PORT: int = 8000
    EMBEDDING_SERVICE_URL: str = ""
    NER_SERVICE_URL: str = ""
    RERANK_SERVICE_URL: str = ""
    CATEGORIZATION_SERVICE_URL: str = ""

settings = Settings()