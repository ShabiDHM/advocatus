# FILE: backend/app/core/config.py
# PHOENIX PROTOCOL - CONFIG V9.4 (DEBUG PRINT B2)

import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = Path(__file__).resolve().parent.parent

if (ROOT_DIR / ".env").exists():
    ENV_FILE_PATH = str(ROOT_DIR / ".env")
elif (BACKEND_DIR / ".env").exists():
    ENV_FILE_PATH = str(BACKEND_DIR / ".env")
else:
    ENV_FILE_PATH = ".env"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE_PATH, 
        extra='ignore'
    )

    PROJECT_NAME: str = "Juristi AI"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "changeme"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 10080

    DATABASE_URI: str = ""
    MONGO_DB_NAME: str = "advocatus_db"
    REDIS_URL: str = ""

    OPENAI_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""

    # B2 Storage
    B2_KEY_ID: str = ""
    B2_APPLICATION_KEY: str = ""
    B2_BUCKET_NAME: str = ""
    B2_ENDPOINT_URL: str = ""
    
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000

settings = Settings()
print(f"DEBUG CONFIG -> B2_KEY_ID loaded: {bool(settings.B2_KEY_ID)}, B2_BUCKET: {settings.B2_BUCKET_NAME}")