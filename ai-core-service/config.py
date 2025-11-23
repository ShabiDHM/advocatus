import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Juristi AI Core"
    API_V1_STR: str = "/api/v1"
    
    # API Keys
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    
    # --- MODEL CONFIGURATION (SOTA UPGRADE) ---
    # 1. Embeddings: BAAI/bge-m3
    # Why: Best multilingual performance, large context window (8192 tokens).
    EMBEDDING_MODEL_NAME: str = "BAAI/bge-m3"
    
    # 2. Reranking: BAAI/bge-reranker-v2-m3
    # Why: Massive accuracy improvement for legal document sorting.
    RERANK_MODEL_NAME: str = "BAAI/bge-reranker-v2-m3"
    
    # 3. NER: Spacy Multilingual (Lightweight)
    # We keep this light because the other two are heavy.
    NER_MODEL_NAME: str = "xx_ent_wiki_sm"
    
    # 4. Categorization: BART Large MNLI
    CATEGORIZATION_MODEL_NAME: str = "facebook/bart-large-mnli"
    
    # Feature Flags
    USE_LOCAL_EMBEDDINGS: bool = True
    USE_LOCAL_LLM: bool = True

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()