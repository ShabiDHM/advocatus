# FILE: backend/app/services/text_sterilization_service.py
# PHOENIX PROTOCOL - VERSION 5.0 (SECURITY HARDENED)
# 1. SECURITY: Removed logging of raw PII entities (Data Leak Prevention).
# 2. LOGIC: Added Regex Safety Net for Emails, Phones, and IDs (Defense in Depth).
# 3. STABILITY: Retained reverse-index replacement logic.

import logging
import re
from typing import List, cast, Tuple

# Import the Albanian NER Service
from .albanian_ner_service import ALBANIAN_NER_SERVICE 

logger = logging.getLogger(__name__)

# Regex Patterns for Structured Data (Kosovo/Albania Context)
REGEX_PATTERNS = [
    # Email Addresses
    (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL_ANONIMIZUAR]'),
    
    # Phone Numbers (Kosovo +383, Albania +355, and local formats like 044, 049, 069)
    # Matches: +383 44 123 456, 044-123-456, 049/123456
    (r'(?:\+383|\+355|00383|00355|0)(?:[\s\-\/]?)(\d{2})(?:[\s\-\/]?)(\d{3})(?:[\s\-\/]?)(\d{3})', '[TELEFON_ANONIMIZUAR]'),
    
    # Personal ID Numbers (10 digits, common in region)
    (r'\b[0-9]{10}\b', '[ID_ANONIMIZUAR]')
]

def sterilize_text_for_llm(text: str) -> str:
    """
    Performs PII redaction using a multi-layered approach:
    1. Regex Pattern Matching (Structured Data)
    2. AI/NER Detection (Names, Orgs, Locs)
    3. UTF-8 Sanitization
    """
    if not isinstance(text, str):
        logger.warning("--- [Sterilization] Input was not a string, returning empty. ---")
        return ""

    # Step 1: Regex Redaction (Fast & Deterministic)
    text = _redact_patterns(text)

    # Step 2: AI/NER Redaction (Contextual)
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
    Sanitizes structured data using Regex before AI processing.
    """
    for pattern, placeholder in REGEX_PATTERNS:
        text = re.sub(pattern, placeholder, text)
    return text

def _redact_pii_with_ner(text: str) -> str:
    """
    Internal function that uses the Albanian NER Service to find and replace PII.
    """
    try:
        # 1. Get all entities from the local NER model
        entities = ALBANIAN_NER_SERVICE.extract_entities(text)
        
        # 2. Sort entities by start index in reverse order to prevent index drift
        entities.sort(key=lambda x: x[2], reverse=True)
        
        # 3. Apply Redaction
        mutable_text = text
        count_redacted = 0

        for entity_text, entity_label, start_index_untyped in entities:
            start_index = cast(int, start_index_untyped)
            
            placeholder = ALBANIAN_NER_SERVICE.get_albanian_placeholder(entity_label)
            end_index = start_index + len(entity_text)

            # Security Check: Ensure indices are valid
            if start_index < 0 or end_index > len(mutable_text):
                continue

            # Replace logic
            mutable_text = mutable_text[:start_index] + placeholder + mutable_text[end_index:]
            count_redacted += 1
            
            # PHOENIX SECURITY FIX: Do NOT log the actual entity text
            # logger.debug(f"Redacted entity of type {entity_label}") 

        if count_redacted > 0:
            logger.info(f"--- [Sterilization] Redacted {count_redacted} entities via NER. ---")
            
        return mutable_text

    except Exception as e:
        logger.error(f"--- [Sterilization] NER Failure: {e}. Returning regex-cleaned text only.")
        return text # Fail safe: return what we have (at least regex cleaned)

# Backward compatibility wrapper
def sterilize_text_to_utf8(text: str) -> str:
    logger.warning("--- [Sterilization] Deprecated: Use 'sterilize_text_for_llm' for PII safety. ---")
    try:
        return text.encode('utf-8', 'ignore').decode('utf-8')
    except Exception as e:
        logger.error(f"--- [Sterilization] Unexpected error in deprecated function: {e}")
        return ""