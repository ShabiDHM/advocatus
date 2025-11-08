# backend/app/config/albanian_feature_flags.py
# DEFINITIVE VERSION 2.0 - ADDED DEVELOPMENT OVERRIDE SWITCH

import os
import hashlib
import logging
from typing import Set, Dict, Optional

logger = logging.getLogger(__name__)

class AlbanianRAGFeatureFlags:
    def __init__(self):
        self.enabled = os.getenv('ALBANIAN_AI_ENABLED', 'false').lower() == 'true'
        self.rollout_percentage = int(os.getenv('ALBANIAN_AI_ROLLOUT_PERCENT', '0'))
        self.allowed_users: Set[str] = set(filter(None, os.getenv('ALBANIAN_AI_ALLOWED_USERS', '').split(',')))
        
        # --- THE NEW DEVELOPMENT OVERRIDE ---
        # If ALBANIAN_AI_DEV_MODE is set to 'true', the feature is enabled for ALL users.
        self.dev_mode_enabled = os.getenv('ALBANIAN_AI_DEV_MODE', 'false').lower() == 'true'
        
        if self.dev_mode_enabled:
            logger.warning("!!! Albanian AI DEV MODE is ACTIVE. Feature will be enabled for ALL users, bypassing other checks. !!!")
        else:
            logger.info(f"Albanian RAG Feature Flags initialized: enabled={self.enabled}, rollout={self.rollout_percentage}%")
    
    def is_enabled_for_request(self, user_id: Optional[str] = None, request_id: Optional[str] = None) -> bool:
        """
        Determine if Albanian RAG features should be enabled for this request.
        """
        # --- NEW: Dev Mode has the highest priority ---
        if self.dev_mode_enabled:
            return True
            
        # Global toggle (if not in dev mode)
        if not self.enabled:
            return False
        
        # Explicit user allowlist
        if user_id and user_id in self.allowed_users:
            return True
        
        # Percentage-based rollout
        if request_id:
            hash_value = int(hashlib.md5(request_id.encode()).hexdigest(), 16) % 100
            return hash_value < self.rollout_percentage
        
        return False

    def get_status(self) -> Dict:
        """Get current feature flag status."""
        if self.dev_mode_enabled:
            return {
                "status": "DEV MODE ACTIVE - ENABLED FOR ALL USERS",
                "rollout_percentage": 100,
            }
        return {
            "enabled": self.enabled,
            "rollout_percentage": self.rollout_percentage,
            "allowed_users_count": len(self.allowed_users),
        }