# backend/app/services/albanian_model_manager.py
# Albanian RAG Enhancement - Phase 1: Foundational Class

import os
from sentence_transformers import SentenceTransformer
from typing import Optional

# --- Configuration Constants ---
# Use the environment variable for the Albanian model name.
ALBANIAN_EMBEDDING_MODEL_NAME: str = os.getenv("ALBANIAN_EMBEDDING_MODEL_NAME", "distiluse-base-multilingual-cased-v2")
# Use the environment variable for the Hugging Face cache location.
HF_CACHE_DIR: str = os.getenv("HF_HOME", "/huggingface_cache")

class AlbanianModelManager:
    """
    Manages the lifecycle and availability of the specialized Albanian embedding model.
    Ensures the model is loaded once and provides methods to validate its configuration.
    """
    _model: Optional[SentenceTransformer] = None
    _is_model_loaded: bool = False

    @classmethod
    def get_model(cls) -> SentenceTransformer:
        """
        Returns the SentenceTransformer model instance, loading it if not already loaded.
        Raises an exception if loading fails.
        """
        if cls._model is None:
            cls._model = cls._load_model()
            cls._is_model_loaded = True
        return cls._model

    @classmethod
    def is_model_loaded(cls) -> bool:
        """Checks if the model has been successfully loaded into memory."""
        return cls._is_model_loaded

    @classmethod
    def _load_model(cls) -> SentenceTransformer:
        """Internal method to handle the actual model loading."""
        print(f"INFO: AlbanianModelManager: Attempting to load model: {ALBANIAN_EMBEDDING_MODEL_NAME}")
        try:
            # SentenceTransformer handles downloading and caching automatically.
            model = SentenceTransformer(
                model_name_or_path=ALBANIAN_EMBEDDING_MODEL_NAME,
                device=os.environ.get("PYTORCH_DEVICE", "cpu"), # Default to CPU
                cache_folder=HF_CACHE_DIR,
                # Explicitly disable model loading if cache is unavailable (for safer deployment)
                # However, for RAG, we MUST have the model, so we let it fail if not found.
            )
            print(f"INFO: AlbanianModelManager: Model '{ALBANIAN_EMBEDDING_MODEL_NAME}' loaded successfully.")
            return model
        except Exception as e:
            # CRITICAL: Log a clear error if the model cannot be found or loaded.
            print(f"CRITICAL: AlbanianModelManager: Failed to load model '{ALBANIAN_EMBEDDING_MODEL_NAME}'. Error: {e}")
            raise RuntimeError(f"Failed to initialize Albanian Embedding Model: {ALBANIAN_EMBEDDING_MODEL_NAME}") from e

# Initialize the model on import to ensure it's ready when the service starts
# NOTE: This will fail the backend service startup if the model cannot be loaded.
# This is a hard requirement for the Albanian RAG feature.
try:
    AlbanianModelManager.get_model()
except RuntimeError:
    # Service will fail to start, but the exception is already raised above.
    pass