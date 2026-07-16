# FILE: backend/app/core/config.py
# PHOENIX PROTOCOL - CONFIG V9.0 (CLEAN ROUTING)
import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    PROJECT_NAME: str = "Juristi AI"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "changeme"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 10080

    DATABASE_URI: str = ""
    MONGO_DB_NAME: str = "advocatus_db"
    REDIS_URL: str = ""

    # PHOENIX: Removed OPENAI_BASE_URL to allow individual services to define their own.
    OPENAI_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""
    
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000

settings = Settings()