# FILE: backend/app/services/text_sterilization_service.py
# PHOENIX PROTOCOL - VERSION 6.0 (SMART SHIELD WITH EMOJI SUPPORT)
# 1. FIX: Preserves emojis and all Unicode characters in text
# 2. FEATURE: Added 'redact_names' flag. 
#    - Default False: Keeps "Shaban Bala" for legal context.
#    - True: Becomes "[PERSON_ANONIMIZUAR]" for max privacy.
# 3. SECURITY: Always redacts IDs, Phones, and Emails regardless of flag.
# 4. STATUS: Granular Privacy Control with full Unicode support.

import logging
import re
import unicodedata
from typing import List, cast, Tuple

# Import the Albanian NER Service
try:
    from .albanian_ner_service import ALBANIAN_NER_SERVICE
except ImportError:
    # Fallback for development/testing
    ALBANIAN_NER_SERVICE = None

logger = logging.getLogger(__name__)

# Regex Patterns for Structured Data (Always Redact these)
REGEX_PATTERNS = [
    # Email Addresses
    (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL_ANONIMIZUAR]'),
    
    # Phone Numbers (Kosovo +383, Albania +355, local 044/049)
    (r'(?:\+383|\+355|00383|00355|0)(?:[\s\-\/]?)(\d{2})(?:[\s\-\/]?)(\d{3})(?:[\s\-\/]?)(\d{3})', '[TELEFON_ANONIMIZUAR]'),
    
    # Personal ID Numbers (10 digits)
    (r'\b[0-9]{10}\b', '[ID_ANONIMIZUAR]'),
    
    # Credit Card Numbers (simplified pattern)
    (r'\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b', '[CARD_ANONIMIZUAR]'),
    
    # IBAN Numbers (simplified)
    (r'\b[A-Z]{2}\d{2}[\s\-]?[A-Z0-9]{4}[\s\-]?[A-Z0-9]{4}[\s\-]?[A-Z0-9]{4}[\s\-]?[A-Z0-9]{4}[\s\-]?[A-Z0-9]{0,2}\b', '[IBAN_ANONIMIZUAR]')
]

def _safe_utf8_encode(text: str) -> str:
    """
    Safely encode and decode text while preserving all Unicode characters including emojis.
    """
    try:
        # Normalize Unicode to NFC form (canonical composition)
        normalized_text = unicodedata.normalize('NFC', text)
        
        # Try direct UTF-8 encoding/decoding
        encoded = normalized_text.encode('utf-8')
        return encoded.decode('utf-8')
    except UnicodeEncodeError:
        # Fallback for problematic characters - replace only what truly can't be encoded
        logger.warning("--- [Sterilization] Some characters could not be encoded, using safe fallback ---")
        return normalized_text.encode('utf-8', errors='replace').decode('utf-8')
    except Exception as e:
        logger.error(f"--- [Sterilization] UTF-8 encoding error: {e}")
        # Last resort: return original but clean
        return ''.join(char for char in text if unicodedata.category(char)[0] != 'C')  # Remove control characters

def sterilize_text_for_llm(text: str, redact_names: bool = False) -> str:
    """
    Primary Sanitization Pipeline - PRESERVES EMOJIS AND UNICODE.
    
    Args:
        text: The raw text to sanitize.
        redact_names: If True, replaces names with [PERSON_ANONIMIZUAR].
                      If False, keeps names for legal context.
    
    Returns:
        Sanitized text with PII removed but emojis/Unicode preserved.
    """
    if not isinstance(text, str):
        logger.warning("--- [Sterilization] Input was not a string, returning empty. ---")
        return ""
    
    if not text or text.strip() == "":
        return text
    
    original_length = len(text)
    logger.debug(f"--- [Sterilization] Processing text ({original_length} chars) ---")
    
    # Step 1: Safe UTF-8 encoding (preserves emojis)
    safe_text = _safe_utf8_encode(text)
    
    # Step 2: Regex Redaction (ALWAYS ON - security critical)
    # We never send IDs, Phones, Emails, or financial data to the AI.
    redacted_text = _redact_patterns(safe_text)
    
    if redacted_text != safe_text:
        logger.info(f"--- [Sterilization] Redacted sensitive patterns from text ---")
    
    # Step 3: AI/NER Redaction (CONDITIONAL - privacy setting)
    # Only runs if strict privacy is requested.
    final_text = redacted_text
    if redact_names and ALBANIAN_NER_SERVICE:
        final_text = _redact_pii_with_ner(redacted_text)
    
    # Log processing summary
    final_length = len(final_text)
    if final_length != original_length:
        logger.info(f"--- [Sterilization] Text length changed: {original_length} → {final_length} chars ---")
    
    # Verify emojis are preserved
    original_emojis = [c for c in text if unicodedata.category(c) == 'So']  # 'So' = Symbol, Other (includes emojis)
    final_emojis = [c for c in final_text if unicodedata.category(c) == 'So']
    
    if original_emojis and len(final_emojis) < len(original_emojis):
        logger.warning(f"--- [Sterilization] Warning: {len(original_emojis) - len(final_emojis)} emojis may have been lost ---")
    
    return final_text

def _redact_patterns(text: str) -> str:
    """
    Sanitizes structured sensitive data using Regex patterns.
    Only targets PII/financial data, leaves emojis and regular text intact.
    """
    if not text:
        return text
    
    result = text
    for pattern, placeholder in REGEX_PATTERNS:
        try:
            result = re.sub(pattern, placeholder, result)
        except re.error as e:
            logger.error(f"--- [Sterilization] Regex pattern error: {e} for pattern: {pattern}")
            continue
    
    return result

def _redact_pii_with_ner(text: str) -> str:
    """
    Internal function that uses the Albanian NER Service to find and replace Names/Orgs.
    Preserves emojis during the redaction process.
    """
    if not ALBANIAN_NER_SERVICE or not text:
        return text
    
    try:
        entities = ALBANIAN_NER_SERVICE.extract_entities(text)
        if not entities:
            return text
        
        # Sort by start index (descending) to avoid index shifting issues
        entities.sort(key=lambda x: x[2] if len(x) > 2 else 0, reverse=True)
        
        mutable_text = text
        count_redacted = 0
        
        for entity in entities:
            if len(entity) < 3:
                continue
                
            entity_text, entity_label, start_index_untyped = entity[:3]
            start_index = cast(int, start_index_untyped)
            
            # Get appropriate placeholder for the entity type
            placeholder = "[ENTITY_ANONIMIZUAR]"
            if hasattr(ALBANIAN_NER_SERVICE, 'get_albanian_placeholder'):
                placeholder = ALBANIAN_NER_SERVICE.get_albanian_placeholder(entity_label)
            
            end_index = start_index + len(entity_text)
            
            # Validate indices
            if start_index < 0 or end_index > len(mutable_text) or start_index >= end_index:
                continue
            
            # Perform the replacement
            mutable_text = mutable_text[:start_index] + placeholder + mutable_text[end_index:]
            count_redacted += 1
        
        if count_redacted > 0:
            logger.info(f"--- [Sterilization] Redacted {count_redacted} entities via NER. ---")
        
        return mutable_text
        
    except Exception as e:
        logger.error(f"--- [Sterilization] NER Failure: {e}. Returning original text. ---")
        return text

# Backward compatibility wrapper
def sterilize_text_to_utf8(text: str) -> str:
    """
    Legacy function for backward compatibility.
    Passes through to the main function with minimal redaction (no name redaction).
    """
    return sterilize_text_for_llm(text, redact_names=False)

def test_emoji_preservation():
    """
    Test function to verify emoji preservation.
    Run this to ensure the fix works.
    """
    test_cases = [
        "🛒 Faturë: 120€ 🍎🥦 + 🥤 = 150€ 💳 ✅",
        "📧 Email: test@example.com 📱 Phone: +383 44 123 456",
        "Shaban Bala 👨‍💼 ka ID: 1234567890",
        "Mixed text with 😀 emojis and normal text 📄",
        "Arabic: مرحبا 🌍 Chinese: 你好 🎌 Japanese: こんにちは 🗾",
        "Special chars: ©®™ €£¥ $¢ ½¼ ²³ °℃ ℉",
        "Emoji sequences: 👨‍👩‍👧‍👦 🚀🔥🌟🎯💯",
    ]
    
    print("🧪 Testing Emoji Preservation in Text Sterilization")
    print("=" * 60)
    
    for i, test in enumerate(test_cases, 1):
        result = sterilize_text_for_llm(test, redact_names=False)
        
        # Count emojis
        orig_emojis = [c for c in test if unicodedata.category(c) == 'So']
        res_emojis = [c for c in result if unicodedata.category(c) == 'So']
        
        print(f"\nTest {i}:")
        print(f"Original ({len(test)} chars, {len(orig_emojis)} emojis): {test}")
        print(f"Result   ({len(result)} chars, {len(res_emojis)} emojis): {result}")
        
        if len(orig_emojis) == len(res_emojis):
            print("✅ Emojis preserved perfectly!")
        else:
            print(f"⚠️  Emoji count changed: {len(orig_emojis)} → {len(res_emojis)}")
        
        # Check for PII redaction
        if "@example.com" in result and "@example.com" not in test:
            print("✅ Email properly redacted")
        if "+383 44 123 456" in result and "+383 44 123 456" not in test:
            print("✅ Phone properly redacted")
    
    print("\n" + "=" * 60)
    print("Test complete! All emojis should be preserved while PII is redacted.")

# If run directly, execute tests
if __name__ == "__main__":
    test_emoji_preservation()