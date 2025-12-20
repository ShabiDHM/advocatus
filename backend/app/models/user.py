# FILE: backend/app/models/user.py
# PHOENIX PROTOCOL - USER MODEL V5.0 (BRANDING SUPPORT)
# 1. FEATURE: Added 'organization_name' and 'logo' fields for White-Labeling.
# 2. SECURITY: Fields are optional and default to None.

from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional
from datetime import datetime
from .common import PyObjectId

# Base User Model
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    role: str = "STANDARD" # USER, ADMIN, LAWYER
    subscription_status: str = "TRIAL" # ACTIVE, INACTIVE, TRIAL, EXPIRED
    status: str = "inactive"
    
    # PHOENIX NEW: Branding Fields
    organization_name: Optional[str] = None
    logo: Optional[str] = None 

# Model for creating a new user (Registration)
class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

# Model for updating user details
class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    role: Optional[str] = None
    subscription_status: Optional[str] = None
    status: Optional[str] = None
    organization_name: Optional[str] = None
    logo: Optional[str] = None

# Model stored in DB (includes hashed password)
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

# Model for returning user data (Exclude password)
class UserOut(UserBase):
    id: PyObjectId = Field(alias="_id", serialization_alias="id")
    created_at: datetime
    last_login: Optional[datetime] = None
    
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
        arbitrary_types_allowed=True,
    )

# Model for Login Request
class UserLogin(BaseModel):
    username: str
    password: str