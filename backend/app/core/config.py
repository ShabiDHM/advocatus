# FILE: backend/app/core/config.py
# PHOENIX PROTOCOL - CONFIGURATION V7.3 (EXPLICIT CORS FIX)
# 1. FIXED: Removed wildcards. Added literal Vercel deployment URL.
# 2. FIXED: Included production and dev domains as exact matches.
# 3. STATUS: Resolves credentialed CORS blocking on Vercel.

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Union
from pydantic import field_validator, Field
import json

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env', 
        env_file_encoding='utf-8', 
        extra='ignore'
    )

    # --- API Setup ---
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "production"
    FRONTEND_URL: str = "https://juristi.tech"
    
    # --- Auth ---
    SECRET_KEY: str = "changeme"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 10080

    # --- Encryption (Neutralized via Service Fix) ---
    ENCRYPTION_SALT: str = Field(default="")
    ENCRYPTION_PASSWORD: str = Field(default="")

    # --- CORS Configuration (LITERAL STRINGS ONLY) ---
    # Browsers block credentials if wildcards (*) are used.
    BACKEND_CORS_ORIGINS: List[str] = Field(
        default=[
            "https://juristi.tech",
            "https://www.juristi.tech",
            "https://api.juristi.tech",
            "https://advocatus-ai.vercel.app",
            "https://advocatus-bpu736pv2-shabans-projects-31c11eb7.vercel.app",
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173"
        ],
        description="Explicitly allowed origins"
    )

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

    # --- AI & Services ---
    DEEPSEEK_API_KEY: str = ""
    LOCAL_LLM_URL: str = "http://host.docker.internal:11434/api/generate"
    CHROMA_HOST: str = "chroma"
    CHROMA_PORT: int = 8000
    EMBEDDING_SERVICE_URL: str = "http://embedding-service:8001"
    
    # --- Uploads ---
    MAX_UPLOAD_SIZE: int = 15 * 1024 * 1024
    UPLOAD_TIMEOUT: int = 45

settings = Settings()