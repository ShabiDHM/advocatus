import logging
from typing import Optional, List, Tuple, Any
from sentence_transformers import CrossEncoder
from config import settings

logger = logging.getLogger(__name__)

class RerankManager:
    _instance = None
    # Type hints
    model: Optional[CrossEncoder] = None
    model_name: str = ""

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RerankManager, cls).__new__(cls)
            cls._instance.model = None
            cls._instance.model_name = settings.RERANK_MODEL_NAME
        return cls._instance

    def load_model(self):
        """Loads the CrossEncoder model into memory."""
        if self.model is None:
            logger.info(f"📥 Loading Rerank Model: {self.model_name}...")
            try:
                self.model = CrossEncoder(self.model_name)
                logger.info("✅ Rerank Model loaded successfully.")
            except Exception as e:
                logger.error(f"❌ Failed to load rerank model: {e}")
                raise e

    def rank_documents(self, query: str, documents: List[str]) -> List[str]:
        """
        Sorts documents based on relevance to the query.
        """
        # 1. Ensure model is loaded
        if self.model is None:
            self.load_model()
            
        # 2. Final Safety Check
        if self.model is None:
             raise RuntimeError("Rerank model failed to initialize.")

        if not documents:
            return []

        try:
            # Prepare pairs [query, doc]
            model_input = [[query, doc] for doc in documents]
            
            # Predict scores
            scores = self.model.predict(model_input)
            
            # Zip, Sort, and Extract
            # Cast to list explicitly for safety
            doc_scores: List[Tuple[str, Any]] = list(zip(documents, scores))
            
            # Sort by score descending (high score = better match)
            sorted_doc_scores = sorted(doc_scores, key=lambda x: x[1], reverse=True)
            
            return [doc for doc, score in sorted_doc_scores]
            
        except Exception as e:
            logger.error(f"Error during reranking: {e}")
            raise e

rerank_manager = RerankManager()