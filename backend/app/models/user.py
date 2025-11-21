# FILE: backend/app/models/user.py
# PHOENIX PROTOCOL - FULL USER MODELS
# 1. INCLUDES: UserLogin, UserCreate, UserInDB, and public User models.
# 2. COMPATIBILITY: Pydantic V2 compliant with ConfigDict.

from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional
from datetime import datetime
from .common import PyObjectId

class UserBase(BaseModel):
    username: str
    email: EmailStr
    role: str = "USER"
    subscription_status: str = "ACTIVE"

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserInDB(UserBase):
    id: PyObjectId = Field(alias="_id")
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

class User(UserBase):
    id: str
    created_at: datetime
    last_login: Optional[datetime] = None

    @property
    def token(self) -> Optional[str]:
        return None

    model_config = ConfigDict(from_attributes=True)