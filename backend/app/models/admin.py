# FILE: backend/app/models/admin.py
# PHOENIX PROTOCOL - ADMIN MODELS V1.0
# 1. STATUS: Defines Pydantic models for Admin operations.
# 2. FIX: Resolves "Module is not callable" errors by providing actual Classes.

from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional
from datetime import datetime
from .common import PyObjectId

# --- Admin View of a User ---
class UserAdminView(BaseModel):
    id: PyObjectId = Field(alias="_id", serialization_alias="id")
    username: str
    email: EmailStr
    role: str
    subscription_status: Optional[str] = "TRIAL"
    is_active: bool = True # Mapped from 'disabled' or status logic usually
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    
    # Organization Info
    org_id: Optional[PyObjectId] = None
    organization_name: Optional[str] = None # Legacy/Cache
    
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
        arbitrary_types_allowed=True,
    )

# --- Admin Update Request for a User ---
class UserUpdateRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    subscription_status: Optional[str] = None
    password: Optional[str] = None # Admin can reset password
    
    # Tier 2 / Org
    org_id: Optional[PyObjectId] = None
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True
    )