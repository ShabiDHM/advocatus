import logging
from typing import Optional, List, Dict, Any
from transformers import pipeline
from config import settings

logger = logging.getLogger(__name__)

class CategorizationManager:
    _instance = None
    classifier: Any = None
    model_name: str = ""

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CategorizationManager, cls).__new__(cls)
            cls._instance.classifier = None
            cls._instance.model_name = settings.CATEGORIZATION_MODEL_NAME
        return cls._instance

    def load_model(self):
        """Loads the Zero-Shot Classification pipeline."""
        if self.classifier is None:
            logger.info(f"📥 Loading Categorization Model: {self.model_name}...")
            logger.warning("⚠️ This is a large model (1.6GB). First load will take time.")
            try:
                # Using CPU for now (device=-1). If you have GPU, change to device=0.
                self.classifier = pipeline(
                    "zero-shot-classification", 
                    model=self.model_name,
                    device=-1 
                )
                logger.info("✅ Categorization Model loaded successfully.")
            except Exception as e:
                logger.critical(f"❌ Failed to load categorization model: {e}")
                # We set to None to handle gracefully later
                self.classifier = None

    def categorize_text(self, text: str, labels: List[str]) -> str:
        """
        Classifies text into one of the provided labels.
        """
        # 1. Ensure model is loaded
        if self.classifier is None:
            self.load_model()
            
        if self.classifier is None:
             raise RuntimeError("Categorization model failed to initialize.")

        try:
            # Limit text length to prevent tokenizer crash on huge documents
            # BART limit is usually 1024 tokens, safe approximation is ~3000 chars
            safe_text = text[:3000]
            
            result = self.classifier(safe_text, labels)
            
            # Result structure: {'labels': [...], 'scores': [...]}
            # First label is the highest probability
            predicted_category = result['labels'][0]
            return predicted_category
            
        except Exception as e:
            logger.error(f"Error during categorization: {e}")
            raise e

categorization_manager = CategorizationManager()