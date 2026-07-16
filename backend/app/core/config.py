# PHOENIX PROTOCOL - CONFIGURATION V8.0
# STATUS: Hardware Optimized (8GB RAM) / Dynamic Pathing

import os
import json
from typing import List, Union
from pydantic import field_validator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Dynamic detection of the .env path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENV_PATH = os.path.join(BASE_DIR, ".env")

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_PATH, 
        env_file_encoding='utf-8', 
        extra='ignore'
    )

    # --- API Setup ---
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "production"
    FRONTEND_URL: str = "http://localhost:3000"
    
    # --- Auth ---
    SECRET_KEY: str = "changeme"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 10080

    # --- Encryption ---
    ENCRYPTION_SALT: str = Field(default="")
    ENCRYPTION_PASSWORD: str = Field(default="")

    # --- CORS Configuration ---
    BACKEND_CORS_ORIGINS: List[str] = [
        "https://juristi.tech",
        "https://advocatus-ai.vercel.app",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, str):
            return json.loads(v)
        return v

    # --- Database & Infrastructure (Defaulted to Local for Windows) ---
    DATABASE_URI: str = ""
    REDIS_URL: str = "redis://localhost:6379/0"
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000

    # --- AI & Services ---
    OPENROUTER_API_KEY: str = ""
    DEEPSEEK_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    LOCAL_LLM_URL: str = "http://localhost:11434/api/generate"
    EMBEDDING_SERVICE_URL: str = "http://localhost:8001"
    
    # --- Storage: Backblaze B2 ---
    B2_KEY_ID: str = ""
    B2_APPLICATION_KEY: str = ""
    B2_BUCKET_NAME: str = ""
    B2_ENDPOINT_URL: str = "s3.eu-central-003.backblazeb2.com"

    # --- Email / SMTP ---
    SMTP_TLS: bool = True
    SMTP_PORT: int = 587
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAILS_FROM_EMAIL: str = "noreply@juristi.tech"
    ADMIN_EMAIL: str = ""

settings = Settings()