# FILE: backend/app/models/user.py
# DEFINITIVE VERSION 1.4: ARCHITECTURAL FIX: Added validator to uppercase 'role' in UserOut and UserLoginResponse 
# to align with frontend TypeScript type definitions ('ADMIN', 'LAWYER', 'STANDARD', etc.).

from pydantic import BaseModel, Field, EmailStr, ConfigDict, field_validator
from typing import Optional, Literal, Any
from datetime import datetime

# Import the centralized, Pydantic v2-compliant PyObjectId
from .common import PyObjectId

class UserBase(BaseModel):
    # CRITICAL FIX: Ensure all required fields are explicitly listed in the base model for clarity
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    full_name: Optional[str] = Field(None, max_length=100) # Added optional field for robust registration

class UserCreate(UserBase):
    password: str = Field(min_length=8)

class UserInDBBase(UserBase):
    id: PyObjectId = Field(alias="_id")
    hashed_password: str
    role: Literal['user', 'admin', 'lawyer', 'standard'] = 'user' # Expanded literals to cover all possible values
    subscription_status: Literal['active', 'expired', 'none'] = 'none'
    subscription_expiry_date: Optional[datetime] = None
    last_payment_date: Optional[float] = None # Adjusted type for last_payment_amount to match common float storage
    last_payment_amount: Optional[float] = None
    admin_notes: Optional[str] = None
    
    model_config = ConfigDict(
        populate_by_name = True,
        arbitrary_types_allowed = True,
    )

class UserOut(BaseModel):
    """Public-facing model for general user data retrieval."""
    id: str = Field(alias="_id") 
    username: str
    email: EmailStr
    full_name: Optional[str] = None # Include new field in public output
    role: str
    subscription_status: str
    subscription_expiry_date: Optional[datetime] = None
    
    # FINAL FIX: Add a validator to ensure the '_id' (PyObjectId) from the database
    # is converted to a string before the model is validated for the response.
    @field_validator('id', mode='before')
    @classmethod
    def id_to_str(cls, v: Any) -> str:
        return str(v)

    # --- PHOENIX PROTOCOL FIX 1: Uppercase the role for the frontend contract ---
    @field_validator('role', mode='before')
    @classmethod
    def role_to_uppercase(cls, v: str) -> str:
        return v.upper()

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

class UserInDB(UserInDBBase):
    """Provides the full user object from the DB, for internal use."""
    pass

class UserLoginResponse(BaseModel):
    id: str
    username: str
    email: EmailStr
    full_name: Optional[str] = None # Include new field in login response
    role: str
    subscription_status: str
    
    # FINAL FIX: Add a validator to ensure the '_id' (PyObjectId) from the database
    # is converted to a string before the model is validated for the response.
    @field_validator('id', mode='before')
    @classmethod
    def id_to_str(cls, v: Any) -> str:
        return str(v)

    # --- PHOENIX PROTOCOL FIX 2: Uppercase the role for the frontend contract ---
    @field_validator('role', mode='before')
    @classmethod
    def role_to_uppercase(cls, v: str) -> str:
        return v.upper()
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )