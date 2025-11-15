# FILE: backend/app/models/user.py
# PHOENIX PROTOCOL MODIFICATION: Subscription Status Normalization
# CORRECTION: Added subscription_status normalization to match role field behavior
# This resolves the ValidationError where 'active' (lowercase) doesn't match expected uppercase literals

from pydantic import BaseModel, Field, EmailStr, ConfigDict, model_validator
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
    
    @model_validator(mode='before')
    @classmethod
    def normalize_fields(cls, values):
        """Ensure role and subscription_status fields are always uppercase to prevent case sensitivity issues"""
        if isinstance(values, dict):
            # Normalize role field
            if 'role' in values:
                role_value = values['role']
                if isinstance(role_value, str):
                    normalized_role = role_value.upper()
                    if normalized_role in ['USER', 'ADMIN']:
                        values['role'] = normalized_role
                    else:
                        # Default to USER if invalid role value
                        values['role'] = 'USER'
            
            # PHOENIX PROTOCOL CURE: Normalize subscription_status field
            if 'subscription_status' in values:
                sub_status_value = values['subscription_status']
                if isinstance(sub_status_value, str):
                    normalized_sub = sub_status_value.upper()
                    if normalized_sub in ['ACTIVE', 'INACTIVE', 'TRIAL', 'EXPIRED']:
                        values['subscription_status'] = normalized_sub
                    else:
                        # Default to INACTIVE if invalid subscription_status value
                        values['subscription_status'] = 'INACTIVE'
        return values

class UserOut(BaseModel):
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