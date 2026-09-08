# FILE: backend/app/core/config.py
# PHOENIX PROTOCOL - CONFIG V12.0 (GDPR HARDENED & ENCRYPTION READY)

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
    # SECRET_KEY tani duhet të vendoset patjetër në mjedis (në .env ose në Render)
    SECRET_KEY: str = ""   # No default fallback
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 10080

    # Frontend Domain Configuration (Strip trailing slash automatically)
    FRONTEND_URL: str = "https://juristi.tech"

    DATABASE_URI: str = ""
    MONGO_DB_NAME: str = "advocatus_db"
    REDIS_URL: str = ""

    OPENAI_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""

    # --- FORENSIC SUITE CONFIGURATION ---
    FORENSIC_LLM_MODEL: str = "anthropic/claude-sonnet-4.6"
    FORENSIC_API_KEY: str = ""

    # Audio Forensics (AssemblyAI: Diarization & Speech Sentiment/Stress)
    ASSEMBLYAI_API_KEY: str = ""

    # Visual Forensics (Google Vision API)
    GOOGLE_VISION_API_KEY: str = ""

    # Interactive War Room GraphRAG (Neo4j Aura)
    NEO4J_URI: str = ""
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = ""

    # B2 Storage Configuration
    B2_KEY_ID: str = ""
    B2_APPLICATION_KEY: str = ""
    B2_BUCKET_NAME: str = ""
    B2_ENDPOINT_URL: str = ""
    B2_REGION_NAME: str = ""  # e.g., 'eu-central-003'
    
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000

    # --- ENCRYPTION SERVICE (GDPR / Data at Rest) ---
    # These values are read by encryption_service.py
    ENCRYPTION_SALT: str = ""
    ENCRYPTION_PASSWORD: str = ""

    def validate_production_settings(self):
        """
        Validates that critical secrets are set in production.
        Should be called during startup if ENVIRONMENT == 'production'.
        """
        missing = []
        if not self.SECRET_KEY:
            missing.append("SECRET_KEY")
        if not self.DATABASE_URI:
            missing.append("DATABASE_URI")
        if not self.REDIS_URL:
            missing.append("REDIS_URL")
        if not self.ENCRYPTION_SALT:
            missing.append("ENCRYPTION_SALT")
        if not self.ENCRYPTION_PASSWORD:
            missing.append("ENCRYPTION_PASSWORD")
        # Add other critical keys as needed
        if missing:
            raise RuntimeError(
                f"Missing critical environment variables: {', '.join(missing)}"
            )

settings = Settings()