# FILE: backend/app/services/encryption_service.py
# NEW FILE for Phase 3: BYOK Implementation

import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from ..core.config import settings
import logging

logger = logging.getLogger(__name__)

class APIKeyEncryptionService:
    def __init__(self):
        salt = getattr(settings, 'ENCRYPTION_SALT', None)
        password = getattr(settings, 'ENCRYPTION_PASSWORD', None)

        if not salt or not password:
            logger.critical("CRITICAL: ENCRYPTION_SALT and ENCRYPTION_PASSWORD must be set in the .env file.")
            raise ValueError("Encryption secrets are not configured.")

        self.salt = salt.encode()
        self.password = password.encode()
        self.key = self._get_derived_key()

    def _get_derived_key(self) -> bytes:
        """Derives a Fernet key from the master password and salt."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=480000,  # Increased iterations for modern security standards
        )
        return base64.urlsafe_b64encode(kdf.derive(self.password))

    def encrypt_key(self, plain_text_key: str) -> str:
        """Encrypts a plain-text API key."""
        fernet = Fernet(self.key)
        encrypted_key = fernet.encrypt(plain_text_key.encode())
        return encrypted_key.decode()

    def decrypt_key(self, encrypted_key: str) -> str:
        """Decrypts an encrypted API key."""
        fernet = Fernet(self.key)
        decrypted_key = fernet.decrypt(encrypted_key.encode())
        return decrypted_key.decode()

# Create a singleton instance for use across the application
encryption_service = APIKeyEncryptionService()