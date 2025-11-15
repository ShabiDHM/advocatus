# FILE: backend/app/models/user.py
# PHOENIX PROTOCOL - THE DEFINITIVE AND FINAL CORRECTION (SYNTAX INTEGRITY)
# CORRECTION: The 'id' field in the UserOut model has been changed from 'str' to 'PyObjectId'.
# This resolves a critical ResponseValidationError by correctly informing Pydantic of the
# data type it will receive from the database model before serialization. The existing
# json_encoder will then correctly convert this ObjectId to a string in the final JSON output.
# CORRECTION: The 'id' field in the UserLoginResponse model has been similarly corrected for consistency.

from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional, Literal
from datetime import datetime

from .common import PyObjectId

class UserBase(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    full_name: Optional[str] = Field(None, max_length=100)

class UserCreate(UserBase):
    password: str = Field(min_length=8)

class UserInDBBase(UserBase):
    id: PyObjectId = Field(alias="_id")
    hashed_password: str
    
    role: Literal['USER', 'ADMIN'] = 'USER'
    
    subscription_status: Literal['ACTIVE', 'INACTIVE', 'TRIAL', 'EXPIRED'] = 'INACTIVE'
    
    subscription_expiry_date: Optional[datetime] = None
    last_payment_date: Optional[datetime] = None
    last_payment_amount: Optional[float] = None
    admin_notes: Optional[str] = None
    last_login: Optional[datetime] = None
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

class UserOut(BaseModel):
    # This type hint is now correct for the source data.
    id: PyObjectId = Field(alias="_id")
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    role: str
    subscription_status: str
    subscription_expiry_date: Optional[datetime] = None
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
        # This encoder correctly handles the serialization of the PyObjectId to a string.
        json_encoders={PyObjectId: str}
    )

class AdminUserOut(BaseModel):
    id: str = Field(alias="_id")
    username: str
    email: EmailStr
    role: str
    subscription_status: str
    created_at: datetime
    last_login: Optional[datetime] = None
    case_count: int
    document_count: int

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={PyObjectId: str}
    )

class UserInDB(UserInDBBase):
    pass

class UserLoginResponse(BaseModel):
    # This type hint is also corrected for consistency and robustness.
    id: PyObjectId = Field(alias="_id")
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    role: str
    subscription_status: str
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={PyObjectId: str}
    )