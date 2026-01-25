# FILE: backend/app/core/config.py
# PHOENIX PROTOCOL - CONFIGURATION V6.3 (MOBILE CORS FIX)
# 1. ADDED: Pre-configured CORS origins for mobile support
# 2. ADDED: Upload configuration for mobile files
# 3. STATUS: Mobile-ready configuration

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Union
from pydantic import field_validator, Field
import json

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    # --- API Setup ---
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "production"
    FRONTEND_URL: str = "https://juristi.tech"
    
    # --- Auth ---
    SECRET_KEY: str = "changeme"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 10080

    # --- CORS Configuration (Enhanced for Mobile) ---
    BACKEND_CORS_ORIGINS: List[str] = Field(
        default=[
            "https://juristi.tech",
            "https://www.juristi.tech",
            "https://*.vercel.app",
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ],
        description="Allowed CORS origins for browser access"
    )

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, str):
            return json.loads(v)
        return v

    # --- Upload Configuration (Mobile Optimization) ---
    MAX_UPLOAD_SIZE: int = Field(
        default=15 * 1024 * 1024,  # 15MB for mobile camera images
        description="Maximum file upload size"
    )
    
    UPLOAD_TIMEOUT: int = Field(
        default=45,
        description="Upload timeout in seconds (longer for mobile)"
    )

    # --- Database & Broker ---
    DATABASE_URI: str = ""
    REDIS_URL: str = "redis://redis:6379/0"

    # --- External Services (Storage) ---
    B2_KEY_ID: str = ""
    B2_APPLICATION_KEY: str = ""
    B2_ENDPOINT_URL: str = ""
    B2_BUCKET_NAME: str = ""

    # --- AI Engines ---
    DEEPSEEK_API_KEY: str = ""
    LOCAL_LLM_URL: str = "http://host.docker.internal:11434/api/generate"
    HF_TOKEN: str = ""

    # --- Internal AI Microservices ---
    EMBEDDING_MODEL: str = "sentence-transformers/distiluse-base-multilingual-cased-v2"
    CHROMA_HOST: str = "chroma"
    CHROMA_PORT: int = 8000
    EMBEDDING_SERVICE_URL: str = "http://embedding-service:8001"
    NER_SERVICE_URL: str = "http://ner-service:8002"
    RERANK_SERVICE_URL: str = "http://rerank-service:8003"
    CATEGORIZATION_SERVICE_URL: str = "http://categorization-service:8004"
    
    # --- Encryption (BYOK) ---
    ENCRYPTION_SALT: str = ""
    ENCRYPTION_PASSWORD: str = ""

settings = Settings()