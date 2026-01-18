# FILE: backend/app/services/categorization_service.py
# PHOENIX PROTOCOL - RECONSTRUCTION V1.1 (DIRECT IMPORT)
# 1. FIX: Imports 'categorize_document_text' function directly from llm_service.
# 2. LOGIC: Breaks the circular dependency and resolves the startup crash.

import logging
# CORRECTED IMPORT: Import the specific function, not the non-existent service object.
from .llm_service import categorize_document_text

logger = logging.getLogger(__name__)

class CategorizationService:
    """
    A service dedicated to classifying document text into predefined categories.
    """
    def categorize_document(self, text: str) -> str:
        """
        Uses the LLM service to determine the category of a given text.
        """
        try:
            # Directly call the imported function
            category = categorize_document_text(text)
            if not category:
                return "Unknown"
            return category
        except Exception as e:
            logger.error(f"Error during document categorization: {e}", exc_info=True)
            return "Unknown"

# --- CRITICAL INSTANTIATION ---
CATEGORIZATION_SERVICE = CategorizationService()