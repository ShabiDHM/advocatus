import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Advocatus AI Core"
    API_V1_STR: str = "/api/v1"
    
    # We will link these to your root .env file later
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    
    # Logic toggles for optimization
    USE_LOCAL_EMBEDDINGS: bool = True
    USE_LOCAL_LLM: bool = True

    class Config:
        case_sensitive = True

settings = Settings()