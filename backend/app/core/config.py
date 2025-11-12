# FILE: backend/app/core/config.py

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
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
    # PHOENIX PROTOCOL CURE: Default to None for linter, validate at runtime.
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