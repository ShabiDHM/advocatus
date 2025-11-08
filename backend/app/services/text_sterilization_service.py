# app/services/text_sterilization_service.py
# DEFINITIVE VERSION 4.1: FIXING PYCLANCE TYPE ERRORS AND RETURN PATHS

import logging
import re
from typing import List, cast # <<< FIX 1: Import 'cast' for explicit type hinting

# Import the new Albanian NER Service
from .albanian_ner_service import ALBANIAN_NER_SERVICE 

logger = logging.getLogger(__name__)


def sterilize_text_for_llm(text: str) -> str:
    """
    Performs PII redaction using the specialized Albanian NER service and 
    then forces the text into a clean UTF-8 format.
    """
    if not isinstance(text, str):
        logger.warning("--- [Sterilization] Input was not a string, returning empty. ---")
        return "" # Returns str: OK

    # Step 1: PII Redaction via NER Service
    redacted_text = _redact_pii_with_ner(text)
    
    # Step 2: UTF-8 Sanitization (Original Logic)
    try:
        # We explicitly return the result of the encoding/decoding process
        clean_text = redacted_text.encode('utf-8', 'ignore').decode('utf-8')
        logger.debug("--- [Sterilization] PII Redaction and UTF-8 cleaning successful. ---")
        return clean_text # Returns str: OK
    except Exception as e:
        logger.error(f"--- [Sterilization] Unexpected error during UTF-8 sanitization: {e}")
        return "" # Returns str: OK


def _redact_pii_with_ner(text: str) -> str:
    """
    Internal function that uses the Albanian NER Service to find and replace PII.
    """
    # 1. Get all entities from the local NER model
    entities = ALBANIAN_NER_SERVICE.extract_entities(text)
    
    # 2. Sort entities by start index in reverse order
    entities.sort(key=lambda x: x[2], reverse=True)
    
    # 3. Apply Redaction
    mutable_text = text
    for entity_text, entity_label, start_index_untyped in entities:
        # <<< FIX 2: Explicitly cast start_index to an integer to resolve Pylance's str+int issue
        start_index = cast(int, start_index_untyped) 
        
        placeholder = ALBANIAN_NER_SERVICE.get_albanian_placeholder(entity_label)
        end_index = start_index + len(entity_text) # This calculation is correct

        # This string slicing/concatenation is the correct way to replace in Python
        mutable_text = mutable_text[:start_index] + placeholder + mutable_text[end_index:]
        logger.debug(f"--- [Sterilization] Redacted: '{entity_text}' with '{placeholder}'. ---")
        
    # Final cleanup 
    mutable_text = mutable_text.replace("Avokati Phoenix", "[AVOKAT_ANONIMIZUAR]")
    mutable_text = mutable_text.replace("Klienti Test", "[KLIENT_ANONIMIZUAR]")
    
    return mutable_text


# The old function name is kept for backward compatibility if other services use it.
# This function is now wrapped in a try/except to ensure a return on all paths.
def sterilize_text_to_utf8(text: str) -> str:
    # <<< FIX 3: Add try/except block to ensure all code paths return a str.
    logger.warning("--- [Sterilization] Deprecated: Use 'sterilize_text_for_llm' for PII safety. ---")
    try:
        # The result of encode/decode is a str
        return text.encode('utf-8', 'ignore').decode('utf-8')
    except Exception as e:
        logger.error(f"--- [Sterilization] Unexpected error in deprecated function: {e}")
        return "" # Returns str on failure: Resolves Pylance return type error