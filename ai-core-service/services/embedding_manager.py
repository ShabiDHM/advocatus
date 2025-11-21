import logging
from typing import Optional, Any
from sentence_transformers import SentenceTransformer
from config import settings
from langdetect import detect, LangDetectException

logger = logging.getLogger(__name__)

class EmbeddingManager:
    _instance = None
    # Explicitly type hint as Optional (can be None or the model)
    model: Optional[SentenceTransformer] = None
    model_name: str = ""

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EmbeddingManager, cls).__new__(cls)
            cls._instance.model = None
            cls._instance.model_name = settings.EMBEDDING_MODEL_NAME
        return cls._instance

    def load_model(self):
        """Loads the embedding model into memory."""
        if self.model is None:
            logger.info(f"📥 Loading Embedding Model: {self.model_name}...")
            try:
                self.model = SentenceTransformer(self.model_name)
                logger.info("✅ Embedding Model loaded successfully.")
            except Exception as e:
                logger.error(f"❌ Failed to load embedding model: {e}")
                raise e

    def generate_embedding(self, text: str):
        """Generates embedding for the given text."""
        # 1. Ensure model is loaded
        if self.model is None:
            self.load_model()
        
        # 2. Final Safety Check for the Linter
        # If it's still None after loading, something is critically wrong.
        if self.model is None:
            raise RuntimeError("Embedding model failed to initialize.")

        try:
            # Now Pylance knows self.model is definitely NOT None here.
            embedding = self.model.encode(text).tolist()
            return embedding
        except Exception as e:
            logger.error(f"Error during embedding generation: {e}")
            raise e

    def _detect_language(self, text: str) -> str:
        try:
            return detect(text)
        except LangDetectException:
            return "unknown"

# Global instance exported for use in routers
embedding_manager = EmbeddingManager()