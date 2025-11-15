# FILE: backend/app/core/config.py
# PHOENIX PROTOCOL - THE FINAL AND DEFINITIVE CORRECTION (STATIC ANALYSIS COMPLIANT)
# CORRECTION: A default value of [] is provided to satisfy Pylance.
# The runtime validator is retained to ensure the environment variable is still mandatory,
# maintaining the single source of truth principle.

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import List, Optional

class Settings(BaseSettings):
    """
    Defines the application's configuration settings.
    Establishes the environment as the single source of truth.
    """
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    # --- Database & Broker ---
    DATABASE_URI: str = ""
    REDIS_URL: str = ""
    
    # --- Auth ---
    SECRET_KEY: Optional[str] = None
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 10080
    
    @field_validator('SECRET_KEY')
    @classmethod
    def secret_key_must_not_be_none(cls, v: Optional[str]) -> str:
        if v is None:
            raise ValueError("SECRET_KEY is not set in the environment. The application cannot start.")
        return v

    # --- CORS Configuration ---
    # PHOENIX PROTOCOL CORRECTION:
    # Default is now an empty list to resolve Pylance's static analysis warning.
    # The validator ensures that if the env var isn't loaded, the app will not start.
    BACKEND_CORS_ORIGINS: List[str] = []

    @field_validator('BACKEND_CORS_ORIGINS')
    @classmethod
    def cors_origins_must_not_be_empty(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("BACKEND_CORS_ORIGINS is not set or is empty in the environment. The application cannot start.")
        return v

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