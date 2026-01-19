# FILE: backend/app/models/admin.py
# PHOENIX PROTOCOL - ADMIN MODELS V2.0 (DATA EXPOSURE)
# 1. FIX: Added 'plan_tier' and 'subscription_expiry' to UserAdminView.
# 2. LOGIC: Ensures frontend receives the actual SaaS status of the user.

from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional
from datetime import datetime
from .common import PyObjectId

# --- Admin View of a User (Response) ---
class UserAdminView(BaseModel):
    id: PyObjectId = Field(alias="_id", serialization_alias="id")
    username: str
    email: EmailStr
    role: str
    
    # Status
    subscription_status: Optional[str] = "TRIAL"
    is_active: bool = True 
    
    # PHOENIX FIX: Expose SaaS Data
    plan_tier: Optional[str] = "SOLO"
    subscription_expiry: Optional[datetime] = None
    
    # Metadata
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    
    # Organization Info
    org_id: Optional[PyObjectId] = None
    organization_name: Optional[str] = None
    
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
        arbitrary_types_allowed=True,
    )

# --- Admin Update Request for a User (Request) ---
class UserUpdateRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    
    # SaaS Updates
    subscription_status: Optional[str] = None
    plan_tier: Optional[str] = None
    subscription_expiry: Optional[datetime] = None
    
    password: Optional[str] = None
    org_id: Optional[PyObjectId] = None
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True
    )