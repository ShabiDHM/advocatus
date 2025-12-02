# FILE: backend/app/core/embeddings.py (NEW FILE)
# PHOENIX PROTOCOL - CANONICAL EMBEDDING CLIENT
# 1. PURPOSE: Provides a single, centralized ChromaDB EmbeddingFunction class.
# 2. ARCHITECTURE: Acts as the bridge between ChromaDB and your robust, retry-enabled embedding_service.
# 3. CONSISTENCY: Ensures the entire application uses the microservice pattern for embeddings.

import logging
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings
from app.services import embedding_service

logger = logging.getLogger(__name__)

class JuristiRemoteEmbeddings(EmbeddingFunction):
    """
    The canonical ChromaDB embedding function for the Juristi AI backend.
    
    This class conforms to the chromadb.EmbeddingFunction interface and uses the
    robust, centralized `embedding_service.generate_embedding` function to
    communicate with the dedicated ai-core-service.
    """
    def __call__(self, input: Documents) -> Embeddings:
        vectors = []
        for text in input:
            try:
                # Use the canonical, retry-enabled service function
                embedding = embedding_service.generate_embedding(text=text)
                if embedding:
                    vectors.append(embedding)
                else:
                    # Service function already logged the error, append a zero vector
                    # to maintain batch integrity. The dimension should match your model.
                    vectors.append([0.0] * 768) 
            except Exception as e:
                logger.error(f"❌ Unhandled error during embedding generation via service: {e}")
                vectors.append([0.0] * 768)
        return vectors