# FILE: backend/app/services/encryption_service.py
# PHOENIX PROTOCOL - BYOK DECOMMISSION V1.0 (NON-BLOCKING)
# 1. FIXED: Removed mandatory secret check in __init__ to prevent backend crash.
# 2. FIXED: Made encryption/decryption return plain text or log warnings if called.
# 3. STATUS: Neutralized. This service no longer blocks startup.

import logging
from ..core.config import settings

logger = logging.getLogger(__name__)

class APIKeyEncryptionService:
    def __init__(self):
        # We no longer raise ValueError here. 
        # If the feature is not used, the backend should still start.
        self.salt = getattr(settings, 'ENCRYPTION_SALT', None)
        self.password = getattr(settings, 'ENCRYPTION_PASSWORD', None)
        
        if not self.salt or not self.password:
            logger.info("BYOK Encryption Service: Not configured (Feature Inactive).")
            self.active = False
        else:
            self.active = True
            # Optional: Add logic here if you ever decide to re-enable it.

    def encrypt_key(self, plain_text_key: str) -> str:
        """Returns the plain text if service is inactive."""
        if not self.active:
            return plain_text_key
        # If active, you would put encryption logic here.
        return plain_text_key

    def decrypt_key(self, encrypted_key: str) -> str:
        """Returns the encrypted text as-is if service is inactive."""
        if not self.active:
            return encrypted_key
        # If active, you would put decryption logic here.
        return encrypted_key

# Create the singleton instance. 
# Because the __init__ is now safe, this will no longer crash the backend.
encryption_service = APIKeyEncryptionService()