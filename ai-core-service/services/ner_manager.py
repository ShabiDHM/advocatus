import logging
import spacy
from typing import Optional, List, Dict, Any
from config import settings

logger = logging.getLogger(__name__)

class NERManager:
    _instance = None
    nlp: Any = None # Spacy language object
    model_name: str = ""

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(NERManager, cls).__new__(cls)
            cls._instance.nlp = None
            cls._instance.model_name = settings.NER_MODEL_NAME
        return cls._instance

    def load_model(self):
        """Loads the Spacy NER model into memory."""
        if self.nlp is None:
            logger.info(f"📥 Loading NER Model: {self.model_name}...")
            try:
                self.nlp = spacy.load(self.model_name)
                logger.info(f"✅ NER Model '{self.model_name}' loaded successfully.")
            except Exception as e:
                logger.critical(f"❌ Failed to load NER model: {e}")
                # We don't raise here to prevent blocking the whole service, 
                # but specific NER requests will fail.
                self.nlp = None

    def extract_entities(self, text: str) -> List[Dict[str, str]]:
        """
        Extracts named entities from the text.
        """
        # 1. Ensure model is loaded
        if self.nlp is None:
            self.load_model()
            
        if self.nlp is None:
             raise RuntimeError("NER model failed to initialize.")

        try:
            doc = self.nlp(text)
            # Convert Spacy entities to our standard format
            entities = [{"text": ent.text, "label": ent.label_} for ent in doc.ents]
            return entities
            
        except Exception as e:
            logger.error(f"Error during entity extraction: {e}")
            raise e

ner_manager = NERManager()