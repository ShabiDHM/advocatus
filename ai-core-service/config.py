import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Juristi AI Core"
    API_V1_STR: str = "/api/v1"
    
    # API Keys
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    
    # Model Configurations
    EMBEDDING_MODEL_NAME: str = "paraphrase-multilingual-mpnet-base-v2"
    RERANK_MODEL_NAME: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    
    # Feature Flags
    USE_LOCAL_EMBEDDINGS: bool = True
    USE_LOCAL_LLM: bool = True

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()