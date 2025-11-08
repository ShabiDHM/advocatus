# backend/app/services/albanian_language_detector.py
# Albanian RAG Enhancement - Phase 1: Foundational Class

from typing import List

class AlbanianLanguageDetector:
    """
    Implements a hybrid language detection strategy:
    1. Fast Keyword Check (High Precision, Low Recall)
    2. Optional ML Model Check (High Precision, High Recall - placeholder)
    """

    # VITAL: A list of common, high-confidence Albanian legal and common stop words.
    # This list allows for a very fast check without needing the ML model.
    # We prioritize words that are distinct from other common multilingual corpus languages.
    HIGH_CONFIDENCE_ALBANIAN_WORDS: List[str] = [
        "ligjor", "gjykata", "neni", "vendim", "paditës", "të", "dhe", "në", "për", "është", "me",
        "një", "kanë", "ky", "sipas", "kësaj", "nga", "që", "duke", "ku", "para", "rreth", "apo"
    ]

    # Threshold: Percentage of document that must contain high-confidence keywords
    KEYWORD_THRESHOLD: float = 0.05  # e.g., 5% of all words must be from the list.

    @classmethod
    def detect_language(cls, text: str) -> bool:
        """
        Performs hybrid detection to determine if the text is predominantly Albanian.
        """
        if not text:
            return False

        # 1. Normalize and tokenize the text
        text_lower = text.lower()
        words = text_lower.split()
        total_words = len(words)

        if total_words == 0:
            return False

        # 2. Fast Keyword Check
        albanian_word_count = sum(1 for word in words if word in cls.HIGH_CONFIDENCE_ALBANIAN_WORDS)
        keyword_density = albanian_word_count / total_words

        if keyword_density >= cls.KEYWORD_THRESHOLD:
            # High confidence via keyword density
            return True

        # 3. ML Fallback (Placeholder for Phase 2)
        # The ML model check (e.g., using a fine-tuned langdetect or similar) would go here.
        # This is where the feature flag for the full ML model would be checked.
        # if settings.ALBANIAN_AI_ENABLED:
        #    return cls._run_ml_check(text)
        
        # For now, without the ML check, we rely solely on the keyword density
        return False

    @staticmethod
    def _run_ml_check(text: str) -> bool:
        """Placeholder for the resource-intensive ML check (to be implemented in Phase 2)."""
        # This would call an ML language model or a specialized microservice.
        # return model.predict_language(text) == 'sq'
        return False # Placeholder