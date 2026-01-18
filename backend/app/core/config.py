# FILE: backend/app/core/config.py
# PHOENIX PROTOCOL - CONFIGURATION V6.2 (INVITE URL)
# 1. ADDED: 'FRONTEND_URL' to generate correct email invitation links.
# 2. STATUS: End-to-end ready.

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Union
from pydantic import field_validator
import json

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    # --- API Setup ---
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "production"
    # PHOENIX ADDITION: URL for email links
    FRONTEND_URL: str = "https://juristi.tech"
    
    # --- Auth ---
    SECRET_KEY: str = "changeme"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 10080

    # --- CORS Configuration ---
    BACKEND_CORS_ORIGINS: List[str] = []

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, str):
            return json.loads(v)
        return v

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