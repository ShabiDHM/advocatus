# FILE: backend/app/models/admin.py
# PHOENIX PROTOCOL - ADMIN MODELS V2.3 (STATUS SYNCHRONIZATION)
# 1. FIX: Added 'status' field to UserAdminView and UserUpdateRequest to synchronize and persist account activation states across Admin and Team tabs.

from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional
from datetime import datetime
from .common import PyObjectId

# Absolute Import to ensure stability across the application
from app.models.user import AccountType, SubscriptionTier, ProductPlan

# --- Admin View of a User (Response) ---
class UserAdminView(BaseModel):
    id: PyObjectId = Field(alias="_id", serialization_alias="id")
    username: str
    email: EmailStr
    role: str
    
    # Status
    status: Optional[str] = "active" # PHOENIX FIX: Exposes database account activation status ('active'/'pending_invite')
    subscription_status: Optional[str] = "TRIAL"
    is_active: bool = True 
    
    # Expose correct SaaS Matrix directly from DB
    account_type: Optional[AccountType] = AccountType.SOLO
    subscription_tier: Optional[SubscriptionTier] = SubscriptionTier.BASIC
    product_plan: Optional[ProductPlan] = ProductPlan.SOLO_PLAN
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

# --- Admin Update Request (Shared Request Model) ---
class UserUpdateRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    
    # SaaS Updates
    status: Optional[str] = None # PHOENIX FIX: Allows admin to explicitly update account activation status
    subscription_status: Optional[str] = None
    account_type: Optional[AccountType] = None
    subscription_tier: Optional[SubscriptionTier] = None
    product_plan: Optional[ProductPlan] = None
    subscription_expiry: Optional[datetime] = None
    
    password: Optional[str] = None
    org_id: Optional[PyObjectId] = None
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True
    )