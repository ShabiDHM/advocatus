# FILE: backend/app/models/user.py
# PHOENIX PROTOCOL - USER MODEL V7.0 (SUBSCRIPTION DATES)
# 1. ADDED: 'subscription_expiry' field to manage SaaS time limits.
# 2. STATUS: Critical for the new Admin Dashboard logic.

from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
from .common import PyObjectId

# Base User Model
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    role: str = "STANDARD" # ADMIN, LAWYER, CLIENT, STANDARD
    
    # Organization Context
    org_id: Optional[PyObjectId] = None 
    org_role: str = "OWNER"             
    
    # SaaS Logic
    subscription_status: str = "INACTIVE" # ACTIVE, INACTIVE, EXPIRED, TRIAL
    subscription_expiry: Optional[datetime] = None # PHOENIX: Added Date
    plan_tier: str = "SOLO" # SOLO, STARTUP, GROWTH, ENTERPRISE
    
    # Legacy
    organization_name: Optional[str] = None
    logo: Optional[str] = None 

# Model for creating a new user
class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

# Model for updating user details
class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    
    org_id: Optional[PyObjectId] = None
    org_role: Optional[str] = None
    
    subscription_status: Optional[str] = None
    subscription_expiry: Optional[datetime] = None # Admin can update this
    plan_tier: Optional[str] = None
    status: Optional[str] = None
    
    organization_name: Optional[str] = None
    logo: Optional[str] = None

# Model stored in DB
class UserInDB(UserBase):
    id: PyObjectId = Field(alias="_id", default=None)
    hashed_password: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    
    # For Invitation Flow
    invitation_token: Optional[str] = None
    invitation_token_expiry: Optional[datetime] = None
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

# Return Model
class UserOut(UserBase):
    id: PyObjectId = Field(alias="_id", serialization_alias="id")
    created_at: datetime
    last_login: Optional[datetime] = None
    
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
        arbitrary_types_allowed=True,
    )

class UserLogin(BaseModel):
    username: str
    password: str

# Limits based on Plan Tier
PLAN_LIMITS = {
    "SOLO": 1,
    "STARTUP": 5,
    "GROWTH": 10,
    "ENTERPRISE": 50
}