# FILE: backend/app/services/api_key_service.py
# DEFINITIVE VERSION 2.0 (ARCHITECTURAL CORRECTION):
# Removed the unused and invalid 'get_db' import, resolving the 'ImportError'
# startup crash.

import httpx
from pymongo.database import Database
from typing import List, Tuple, Optional
import logging

# --- PHOENIX PROTOCOL FIX: Removed invalid import ---
# from ..core.db import get_db
from ..models.user import UserInDB
from ..models.api_key import ApiKeyInDB, ApiKeyOut, ApiKeyCreate
from .encryption_service import encryption_service
from ..models.common import PyObjectId

logger = logging.getLogger(__name__)

# --- Key Validation Functions ---

async def _validate_openai_key(api_key: str) -> Tuple[bool, str]:
    """Makes a simple, cheap API call to OpenAI to validate the key."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {api_key}"}
            )
        response.raise_for_status()
        logger.info("OpenAI key validation successful.")
        return True, "Valid OpenAI key."
    except httpx.HTTPStatusError as e:
        logger.warning(f"OpenAI key validation failed. Status: {e.response.status_code}")
        return False, "Invalid OpenAI API key."
    except Exception as e:
        logger.error(f"An unexpected error occurred during OpenAI key validation: {e}")
        return False, f"An unexpected error occurred: {str(e)}"

async def validate_api_key(provider: str, api_key: str) -> Tuple[bool, str]:
    """Routes to the appropriate validation function based on the provider."""
    if provider == 'openai':
        return await _validate_openai_key(api_key)
    # Add other providers here
    return False, "Unsupported provider."

# --- CRUD Service Functions (Architecturally Correct) ---

async def create_and_store_key(db: Database, user: UserInDB, key_data: ApiKeyCreate) -> ApiKeyInDB:
    """Encrypts and stores a new API key for a user."""
    encrypted_key = encryption_service.encrypt_key(key_data.api_key)
    
    db_key_data = {
        "user_id": user.id,
        "provider": key_data.provider,
        "key_name": key_data.key_name,
        "encrypted_api_key": encrypted_key,
    }

    db.user_api_keys.update_one(
        {"user_id": user.id, "provider": key_data.provider},
        {"$set": db_key_data},
        upsert=True
    )
    
    created_or_updated_key = db.user_api_keys.find_one({"user_id": user.id, "provider": key_data.provider})
    
    return ApiKeyInDB.model_validate(created_or_updated_key)

def get_user_keys(db: Database, user: UserInDB) -> List[ApiKeyOut]:
    """Retrieves all of a user's API keys (without the encrypted key value)."""
    keys_cursor = db.user_api_keys.find({"user_id": user.id})
    return [ApiKeyOut.model_validate(key) for key in keys_cursor]

def delete_user_key(db: Database, user: UserInDB, key_id: PyObjectId) -> bool:
    """Deletes a specific API key belonging to the user."""
    result = db.user_api_keys.delete_one({"_id": key_id, "user_id": user.id})
    return result.deleted_count > 0