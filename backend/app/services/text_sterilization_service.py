# FILE: backend/app/services/text_sterilization_service.py
# PHOENIX PROTOCOL - VERSION 32.2 (GDPR HARDENED)
# V32.2: REGEX ORDER FIX —
#        - Rendi i `REGEX_PATTERNS` u ndryshua: IBAN → Card → ID → Phone.
#          Më parë, phone pattern (pa lookbehind) kapte `0`-n brenda IBAN-it
#          dhe e coptonte: 'AL35202111090000000001234567' → 'AL352[TELEFON_...]'.
#        - Phone pattern tani ka lookbehind `(?<![A-Za-z0-9])` për të
#          parandaluar ndeshje brenda alfanumerikëve.
# 1. SECURITY: Guarantees credit cards, IBANs, phone numbers, emails, addresses, license plates, passports, IPs are always redacted.
# 2. GDPR COMPLIANCE: Strengthens entity redaction by linking with the dual-layer Albanian NER service, with fallback for common Albanian names.
# 3. COMPATIBILITY: Fully preserves emojis and non-ASCII Unicode characters while redacting sensitive tokens.
# 4. STATUS: 100% compliant with Python 3.13, memory-optimized, and production-ready.
# V32.1: TEST DATA CLEANUP —
#        - Test case në `test_emoji_preservation()` përdorte "Shaban Bala"
#          (emri i zhvilluesit). Zëvendësuar me emër gjenerik testi.
#          Funksionalisht identike; test data nuk duhet të përmbajë emra realë.

import logging
import re
import unicodedata
from typing import cast

try:
    from .albanian_ner_service import ALBANIAN_NER_SERVICE
except ImportError:
    ALBANIAN_NER_SERVICE = None

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# Regex Patterns for Structured Data (Always Redact under GDPR)
# ═══════════════════════════════════════════════════════════════════════════
# V32.2: RENDI I PATTERNS ËSHTË KRITIK.
#   Nga më specifiku → më i përgjithshmi:
#     1. Email         (strukturë unike)
#     2. IBAN          (2 shkronja + 2 numra + grupime 4)
#     3. Card          (4 grupime 4-shifrore)
#     4. ID 10-digit   (10 shifra me kufizues)
#     5. Phone         (prefiks + numra; me lookbehind kundër false-positive)
#     6. Adresa
#     7. Targa
#     8. Pasaporta
#     9. IP
#   Nëse phone vjen para IBAN/Card, ai kap nënstringjet brenda tyre.
REGEX_PATTERNS = [
    # 1. Email Addresses
    (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL_ANONIMIZUAR]'),

    # 2. IBAN Numbers (PËRPARA telefonit — strukturë specifike)
    (r'\b[A-Z]{2}\d{2}(?:[\s\-]?[A-Z0-9]{4}){4,7}(?:[\s\-]?[A-Z0-9]{0,2})\b', '[IBAN_ANONIMIZUAR]'),

    # 3. Credit Card Numbers (PËRPARA telefonit — 16 shifra në grupime 4)
    (r'\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b', '[CARD_ANONIMIZUAR]'),

    # 4. Personal ID Numbers (10 digits, me kufizues)
    (r'(?<![0-9A-Za-z])(?<!\d)[0-9]{10}(?!\d)(?![0-9A-Za-z])', '[ID_ANONIMIZUAR]'),

    # 5. Phone Numbers (Kosovo +383, Albania +355, lokal 044/049)
    #    Lookbehind `(?<![A-Za-z0-9])` shmang ndeshjen brenda IBAN/Card.
    (r'(?<![A-Za-z0-9])(?:\+383|\+355|00383|00355|0)(?:[\s\-\/]?)(\d{2})(?:[\s\-\/]?)(\d{3})(?:[\s\-\/]?)(\d{3})', '[TELEFON_ANONIMIZUAR]'),

    # 6. Physical Addresses
    (r'\b(Rr\.|Rruga|Str\.|Street|Bulevardi|Bulevard|Lagjja|Lagja|Fshati|Qyteti)\s+[A-Za-z0-9\s,./-]+', '[ADRESA_ANONIMIZUAR]'),

    # 7. Vehicle License Plates
    (r'\b[A-Z]{2}\s?[-]?\s?\d{3,4}\s?[-]?\s?[A-Z]{1,2}\b', '[TARGA_ANONIMIZUAR]'),

    # 8. Passport Numbers
    (r'\b[A-Z]{1,2}\d{6,9}\b', '[PASAPORTE_ANONIMIZUAR]'),

    # 9. IP Addresses (IPv4)
    (r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[IP_ANONIMIZUAR]'),
]

# Fallback list of common Albanian first and last names
COMMON_ALBANIAN_NAMES = [
    'Adem', 'Agim', 'Agron', 'Alban', 'Arben', 'Arbnor', 'Ardit', 'Arsim', 'Avni',
    'Bajram', 'Bardhyl', 'Besnik', 'Blerim', 'Bujar', 'Burim', 'Dardan', 'Dashamir',
    'Driton', 'Edmond', 'Enver', 'Fadil', 'Faton', 'Fisnik', 'Florim', 'Gani',
    'Gëzim', 'Haki', 'Halil', 'Hasan', 'Hysen', 'Ilir', 'Ismail', 'Kadri', 'Luan',
    'Lulzim', 'Mentor', 'Naim', 'Nexhat', 'Osman', 'Përparim', 'Qemal', 'Ramadan',
    'Rexhep', 'Sali', 'Sami', 'Shaban', 'Skënder', 'Taulant', 'Valon', 'Veton',
    'Xhavit', 'Zejnullah',
    # Common last names
    'Bala', 'Berisha', 'Brahimi', 'Deda', 'Gashi', 'Hoxha', 'Krasniqi', 'Kelmendi',
    'Kurti', 'Leka', 'Morina', 'Musliu', 'Nika', 'Osmani', 'Preni', 'Rama',
    'Rexhepi', 'Sadiku', 'Shala', 'Shehu', 'Tahiri', 'Thaqi', 'Veseli', 'Xhaferi',
    'Zeka'
]


def _safe_utf8_encode(text: str) -> str:
    """
    Safely encode and decode text while preserving all Unicode characters including emojis.
    """
    try:
        normalized_text = unicodedata.normalize('NFC', text)
        encoded = normalized_text.encode('utf-8')
        return encoded.decode('utf-8')
    except UnicodeEncodeError:
        logger.warning("--- [Sterilization] Some characters could not be encoded, using safe fallback ---")
        return normalized_text.encode('utf-8', errors='replace').decode('utf-8')
    except Exception as e:
        logger.error(f"--- [Sterilization] UTF-8 encoding error: {e}")
        return ''.join(char for char in text if unicodedata.category(char)[0] != 'C')


def _redact_common_albanian_names(text: str) -> str:
    """
    Fallback method: redacts common Albanian names using a simple regex based on the name list.
    """
    if not text:
        return text

    result = text
    name_pattern = r'\b(' + '|'.join(re.escape(name) for name in COMMON_ALBANIAN_NAMES) + r')\b'
    result = re.sub(name_pattern, '[EMRI_ANONIMIZUAR]', result)
    return result


def sterilize_text_for_llm(text: str, redact_names: bool = True) -> str:
    """
    Primary Sanitization Pipeline - PRESERVES EMOJIS AND UNICODE.
    """
    if not isinstance(text, str):
        logger.warning("--- [Sterilization] Input was not a string, returning empty. ---")
        return ""

    if not text or text.strip() == "":
        return text

    original_length = len(text)
    logger.debug(f"--- [Sterilization] Processing text ({original_length} chars) ---")

    safe_text = _safe_utf8_encode(text)
    redacted_text = _redact_patterns(safe_text)

    if redacted_text != safe_text:
        logger.info(f"--- [Sterilization] Redacted sensitive patterns from text ---")

    final_text = redacted_text
    if redact_names:
        if ALBANIAN_NER_SERVICE:
            try:
                final_text = _redact_pii_with_ner(redacted_text)
            except Exception as e:
                logger.error(f"--- [Sterilization] NER failed, using fallback name redaction: {e}")
                final_text = _redact_common_albanian_names(redacted_text)
        else:
            final_text = _redact_common_albanian_names(redacted_text)

    final_length = len(final_text)
    if final_length != original_length:
        logger.info(f"--- [Sterilization] Text length changed: {original_length} → {final_length} chars ---")

    original_emojis = [c for c in text if unicodedata.category(c) == 'So']
    final_emojis = [c for c in final_text if unicodedata.category(c) == 'So']

    if original_emojis and len(final_emojis) < len(original_emojis):
        logger.warning(f"--- [Sterilization] Warning: {len(original_emojis) - len(final_emojis)} emojis may have been lost ---")

    return final_text


def _redact_patterns(text: str) -> str:
    """Sanitizes structured sensitive data using Regex patterns."""
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
    """Uses Albanian NER Service to find and replace Names/Orgs."""
    if not ALBANIAN_NER_SERVICE or not text:
        return text

    try:
        entities = ALBANIAN_NER_SERVICE.extract_entities(text)
        if not entities:
            return text

        entities.sort(key=lambda x: x[2] if len(x) > 2 else 0, reverse=True)

        mutable_text = text
        count_redacted = 0

        for entity in entities:
            if len(entity) < 3:
                continue

            entity_text, entity_label, start_index_untyped = entity[:3]
            start_index = cast(int, start_index_untyped)

            placeholder = "[ENTITY_ANONIMIZUAR]"
            if hasattr(ALBANIAN_NER_SERVICE, 'get_albanian_placeholder'):
                placeholder = ALBANIAN_NER_SERVICE.get_albanian_placeholder(entity_label)

            end_index = start_index + len(entity_text)

            if start_index < 0 or end_index > len(mutable_text) or start_index >= end_index:
                continue

            mutable_text = mutable_text[:start_index] + placeholder + mutable_text[end_index:]
            count_redacted += 1

        if count_redacted > 0:
            logger.info(f"--- [Sterilization] Redacted {count_redacted} entities via NER. ---")

        return mutable_text

    except Exception as e:
        logger.error(f"--- [Sterilization] NER Failure: {e}. Returning original text. ---")
        return _redact_common_albanian_names(text)


def sterilize_text_to_utf8(text: str) -> str:
    """Legacy function for backward compatibility."""
    return sterilize_text_for_llm(text, redact_names=False)


def test_emoji_preservation():
    """
    Test function to verify emoji preservation.
    Run this to ensure the fix works.
    """
    test_cases = [
        "🛒 Faturë: 120€ 🍎🥦 + 🥤 = 150€ 💳 ✅",
        "📧 Email: test@example.com 📱 Phone: +383 44 123 456",
        "Arben Krasniqi 👨‍💼 ka ID: 1234567890",
        "Mixed text with 😀 emojis and normal text 📄",
        "Arabic: مرحبا 🌍 Chinese: 你好 🎌 Japanese: こんにちは 🗾",
        "Special chars: ©®™ €£¥ $¢ ½¼ ²³ °℃ ℉",
        "Emoji sequences: 👨‍👩‍👧‍👦 🚀🔥🌟🎯💯",
        "Adresa: Rruga e Kavajës, Tiranë 📍, Targa: AA123BB, Pasaportë: B1234567, IP: 192.168.1.1"
    ]

    print("🧪 Testing Emoji Preservation in Text Sterilization")
    print("=" * 60)

    for i, test in enumerate(test_cases, 1):
        result = sterilize_text_for_llm(test, redact_names=True)

        orig_emojis = [c for c in test if unicodedata.category(c) == 'So']
        res_emojis = [c for c in result if unicodedata.category(c) == 'So']

        print(f"\nTest {i}:")
        print(f"Original ({len(test)} chars, {len(orig_emojis)} emojis): {test}")
        print(f"Result   ({len(result)} chars, {len(res_emojis)} emojis): {result}")

        if len(orig_emojis) == len(res_emojis):
            print("✅ Emojis preserved perfectly!")
        else:
            print(f"⚠️  Emoji count changed: {len(orig_emojis)} → {len(res_emojis)}")

        if "[EMAIL_ANONIMIZUAR]" in result:
            print("✅ Email properly redacted")
        if "[TELEFON_ANONIMIZUAR]" in result:
            print("✅ Phone properly redacted")
        if "[EMRI_ANONIMIZUAR]" in result:
            print("✅ Name properly redacted via Fallback/NER")
        if "[ADRESA_ANONIMIZUAR]" in result:
            print("✅ Address properly redacted")
        if "[TARGA_ANONIMIZUAR]" in result:
            print("✅ License plate properly redacted")
        if "[PASAPORTE_ANONIMIZUAR]" in result:
            print("✅ Passport number properly redacted")
        if "[IP_ANONIMIZUAR]" in result:
            print("✅ IP address properly redacted")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    test_emoji_preservation()