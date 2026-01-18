# FILE: backend/app/models/user.py
# PHOENIX PROTOCOL - USER MODEL V6.0 (MULTI-TENANT SUPPORT)
# 1. ADDED: 'org_id' (Optional -> Required later) to link user to Organization.
# 2. ADDED: 'org_role' to distinguish OWNER vs MEMBER.
# 3. PRESERVED: Legacy branding fields for backward compatibility during migration.

from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional
from datetime import datetime
from .common import PyObjectId

# Base User Model
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    role: str = "STANDARD" # System Level Role (e.g. SUPER_ADMIN vs USER)
    
    # Organization Context
    org_id: Optional[PyObjectId] = None # The Tenant ID
    org_role: str = "OWNER"             # OWNER, ADMIN, MEMBER
    
    subscription_status: str = "TRIAL"
    status: str = "inactive"
    
    # Legacy / Individual Branding (Kept for Tier 1 compatibility)
    organization_name: Optional[str] = None
    logo: Optional[str] = None 

# Model for creating a new user
class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

# Model for updating user details
class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    role: Optional[str] = None
    
    org_id: Optional[PyObjectId] = None
    org_role: Optional[str] = None
    
    subscription_status: Optional[str] = None
    status: Optional[str] = None
    organization_name: Optional[str] = None
    logo: Optional[str] = None

# Model stored in DB
class UserInDB(UserBase):
    id: PyObjectId = Field(alias="_id", default=None)
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    
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