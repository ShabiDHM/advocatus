# FILE: backend/app/models/api_key.py
# NEW FILE for Phase 3: BYOK Implementation

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal
from datetime import datetime

from .common import PyObjectId

class ApiKeyBase(BaseModel):
    provider: Literal['openai', 'anthropic', 'google']
    key_name: str = Field(..., max_length=100)
    
class ApiKeyCreate(ApiKeyBase):
    api_key: str = Field(..., description="The user's plain-text API key. This will be encrypted.")

class ApiKeyInDB(ApiKeyBase):
    id: PyObjectId = Field(alias="_id")
    user_id: PyObjectId
    encrypted_api_key: str
    is_active: bool = True
    last_used: Optional[datetime] = None
    usage_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

class ApiKeyOut(ApiKeyBase):
    """Public-facing model for API keys, does not expose the encrypted key."""
    id: PyObjectId = Field(alias="_id")
    is_active: bool
    last_used: Optional[datetime] = None
    usage_count: int

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )