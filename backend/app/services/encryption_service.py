# FILE: backend/app/services/encryption_service.py
# PHOENIX PROTOCOL - VERSION 2.0 (FULL ENCRYPTION)
# 1. IMPLEMENTED: Strong encryption using Fernet (AES-128-CBC + HMAC) with PBKDF2HMAC key derivation.
# 2. GDPR COMPLIANCE: Provides encryption at rest for sensitive data when service is active.
# 3. NON-BLOCKING: If encryption keys are not configured, service remains inactive without crashing the backend.
# 4. STATUS: Production-ready, requires `cryptography` library (pip install cryptography).

import base64
import hashlib
import logging
import os
from typing import Optional

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

from ..core.config import settings

logger = logging.getLogger(__name__)


class EncryptionService:
    """
    Handles encryption and decryption of sensitive strings (e.g., API keys, personal data)
    using Fernet symmetric encryption with a key derived from a password and salt.
    """

    def __init__(self):
        self.salt = getattr(settings, 'ENCRYPTION_SALT', None)
        self.password = getattr(settings, 'ENCRYPTION_PASSWORD', None)
        self._fernet: Optional[Fernet] = None
        self.active = False

        if not self.salt or not self.password:
            logger.warning("Encryption Service: ENCRYPTION_SALT and/or ENCRYPTION_PASSWORD not set. Encryption is INACTIVE.")
            return

        if not CRYPTO_AVAILABLE:
            logger.error("Encryption Service: 'cryptography' library is not installed. Encryption is INACTIVE. Install with 'pip install cryptography'.")
            return

        try:
            # Derive a 32-byte key using PBKDF2HMAC
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=self.salt.encode('utf-8'),
                iterations=480000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(self.password.encode('utf-8')))
            self._fernet = Fernet(key)
            self.active = True
            logger.info("Encryption Service: Successfully initialized with PBKDF2HMAC + Fernet.")
        except Exception as e:
            logger.error(f"Encryption Service initialization failed: {e}")
            self.active = False

    def encrypt(self, plain_text: str) -> str:
        """
        Encrypts a plain text string.
        Returns the original string if service is inactive (with a warning).
        """
        if not isinstance(plain_text, str):
            logger.error("Encryption Service: encrypt() expects a string.")
            return plain_text

        if not self.active or not self._fernet:
            logger.warning("Encryption Service is inactive. Returning plain text (no encryption).")
            return plain_text

        try:
            encrypted_bytes = self._fernet.encrypt(plain_text.encode('utf-8'))
            return encrypted_bytes.decode('utf-8')
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            return plain_text  # Fallback to plain text to avoid data loss

    def decrypt(self, encrypted_text: str) -> str:
        """
        Decrypts an encrypted text string.
        Returns the original string if service is inactive or decryption fails.
        """
        if not isinstance(encrypted_text, str):
            logger.error("Encryption Service: decrypt() expects a string.")
            return encrypted_text

        if not self.active or not self._fernet:
            logger.warning("Encryption Service is inactive. Returning input unchanged.")
            return encrypted_text

        try:
            decrypted_bytes = self._fernet.decrypt(encrypted_text.encode('utf-8'))
            return decrypted_bytes.decode('utf-8')
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return encrypted_text  # Return encrypted text as fallback

    def is_active(self) -> bool:
        """Returns True if encryption is properly configured and available."""
        return self.active


# Create the singleton instance.
# Because __init__ is non-blocking, the backend will start even if encryption is not configured.
encryption_service = EncryptionService()