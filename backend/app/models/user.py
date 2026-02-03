# FILE: backend/app/models/user.py
# PHOENIX PROTOCOL - USER MODEL V8.2 (TIER EXPANSION SYNC)
# 1. UPDATED: PLAN_LIMITS for TEAM_PLAN changed from 5 to 10.
# 2. STATUS: Aligned with Juristi Tier Expansion requirements.

from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum
from .common import PyObjectId

# --- Subscription Matrix Enums ---
class AccountType(str, Enum):
    SOLO = "SOLO"
    ORGANIZATION = "ORGANIZATION"

class SubscriptionTier(str, Enum):
    BASIC = "BASIC"
    PRO = "PRO"

class ProductPlan(str, Enum):
    SOLO_PLAN = "SOLO_PLAN"
    TEAM_PLAN = "TEAM_PLAN"

# Base User Model
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: Optional[str] = Field(None, max_length=100) 
    role: str = "STANDARD" 
    
    # Organization Context
    org_id: Optional[PyObjectId] = None 
    org_role: str = "OWNER" 
    
    # Subscription Matrix Fields
    account_type: AccountType = AccountType.SOLO
    subscription_tier: SubscriptionTier = SubscriptionTier.BASIC
    product_plan: ProductPlan = ProductPlan.SOLO_PLAN 

    # SaaS Lifecycle
    subscription_status: str = "INACTIVE" 
    subscription_expiry: Optional[datetime] = None
    
    organization_name: Optional[str] = None
    logo: Optional[str] = None 

# Model for creating a new user
class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

# Model for updating user details
class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    
    org_id: Optional[PyObjectId] = None
    org_role: Optional[str] = None
    
    account_type: Optional[AccountType] = None
    subscription_tier: Optional[SubscriptionTier] = None
    product_plan: Optional[ProductPlan] = None
    subscription_status: Optional[str] = None
    subscription_expiry: Optional[datetime] = None
    
    organization_name: Optional[str] = None
    logo: Optional[str] = None

# Model stored in DB
class UserInDB(UserBase):
    id: PyObjectId = Field(alias="_id", default=None)
    hashed_password: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    
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

# --- PHOENIX V8.2: Updated Plan Limits ---
# CORRECTED: TEAM_PLAN now allows 10 users as per Tier Expansion blueprint.
PLAN_LIMITS = {
    ProductPlan.SOLO_PLAN: 1,
    ProductPlan.TEAM_PLAN: 10,
}