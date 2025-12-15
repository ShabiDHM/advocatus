# FILE: backend/app/services/text_sterilization_service.py
# PHOENIX PROTOCOL - VERSION 5.1 (SMART SHIELD)
# 1. FEATURE: Added 'redact_names' flag. 
#    - Default False: Keeps "Shaban Bala" for legal context.
#    - True: Becomes "[PERSON_ANONIMIZUAR]" for max privacy.
# 2. SECURITY: Always redacts IDs, Phones, and Emails regardless of flag.
# 3. STATUS: Granular Privacy Control.

import logging
import re
from typing import List, cast, Tuple

# Import the Albanian NER Service
from .albanian_ner_service import ALBANIAN_NER_SERVICE 

logger = logging.getLogger(__name__)

# Regex Patterns for Structured Data (Always Redact these)
REGEX_PATTERNS = [
    # Email Addresses
    (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL_ANONIMIZUAR]'),
    
    # Phone Numbers (Kosovo +383, Albania +355, local 044/049)
    (r'(?:\+383|\+355|00383|00355|0)(?:[\s\-\/]?)(\d{2})(?:[\s\-\/]?)(\d{3})(?:[\s\-\/]?)(\d{3})', '[TELEFON_ANONIMIZUAR]'),
    
    # Personal ID Numbers (10 digits)
    (r'\b[0-9]{10}\b', '[ID_ANONIMIZUAR]')
]

def sterilize_text_for_llm(text: str, redact_names: bool = False) -> str:
    """
    Primary Sanitization Pipeline.
    
    Args:
        text: The raw text.
        redact_names: If True, replaces names with [PERSON]. 
                      If False, keeps names for legal context (Shaban vs Sanije).
    """
    if not isinstance(text, str):
        logger.warning("--- [Sterilization] Input was not a string, returning empty. ---")
        return ""

    # Step 1: Regex Redaction (ALWAYS ON)
    # We never send IDs, Phones, or Emails to the AI.
    text = _redact_patterns(text)

    # Step 2: AI/NER Redaction (CONDITIONAL)
    # Only runs if strict privacy is requested.
    if redact_names:
        text = _redact_pii_with_ner(text)
    
    # Step 3: UTF-8 Sanitization
    try:
        clean_text = text.encode('utf-8', 'ignore').decode('utf-8')
        return clean_text
    except Exception as e:
        logger.error(f"--- [Sterilization] Unexpected error during UTF-8 sanitization: {e}")
        return ""

def _redact_patterns(text: str) -> str:
    """
    Sanitizes structured data using Regex.
    """
    for pattern, placeholder in REGEX_PATTERNS:
        text = re.sub(pattern, placeholder, text)
    return text

def _redact_pii_with_ner(text: str) -> str:
    """
    Internal function that uses the Albanian NER Service to find and replace Names/Orgs.
    """
    try:
        entities = ALBANIAN_NER_SERVICE.extract_entities(text)
        entities.sort(key=lambda x: x[2], reverse=True)
        
        mutable_text = text
        count_redacted = 0

        for entity_text, entity_label, start_index_untyped in entities:
            start_index = cast(int, start_index_untyped)
            placeholder = ALBANIAN_NER_SERVICE.get_albanian_placeholder(entity_label)
            end_index = start_index + len(entity_text)

            if start_index < 0 or end_index > len(mutable_text):
                continue

            mutable_text = mutable_text[:start_index] + placeholder + mutable_text[end_index:]
            count_redacted += 1

        if count_redacted > 0:
            logger.info(f"--- [Sterilization] Redacted {count_redacted} entities via NER. ---")
            
        return mutable_text

    except Exception as e:
        logger.error(f"--- [Sterilization] NER Failure: {e}.")
        return text

# Backward compatibility wrapper
def sterilize_text_to_utf8(text: str) -> str:
    # Now just passes through to the main function with minimal redaction
    return sterilize_text_for_llm(text, redact_names=False)