# FILE: backend/app/models/user.py
# PHOENIX PROTOCOL - SERIALIZATION FIX
# 1. ID MAPPING: Added 'serialization_alias="id"' to UserOut.
#    This ensures the JSON output key is 'id' (Frontend requirement) 
#    while still reading '_id' from MongoDB.

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
    status: str = "active"

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
    # PHOENIX FIX: serialization_alias="id" ensures the frontend receives "id": "..."
    # alias="_id" ensures it reads correctly from the MongoDB object
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