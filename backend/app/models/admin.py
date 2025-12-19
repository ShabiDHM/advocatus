# FILE: backend/app/models/admin.py
# PHOENIX PROTOCOL - DATA MODEL RESILIENCE V1.2
# 1. FIX: Added validator to force 'status' to lowercase (prevents "Active" vs "active" mismatch).
# 2. STATUS: Verified.

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List, Any
from datetime import datetime
from bson import ObjectId

class UserUpdateRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    subscription_status: Optional[str] = None
    status: Optional[str] = None
    admin_notes: Optional[str] = None
    subscription_plan: Optional[str] = None
    subscription_expiry_date: Optional[datetime] = None

    # PHOENIX FIX: Force status to lowercase to ensure login check passes
    @field_validator('status')
    @classmethod
    def normalize_status(cls, v: Optional[str]) -> Optional[str]:
        if v:
            return v.lower()
        return v

class SubscriptionUpdate(BaseModel):
    role: Optional[str] = None
    status: Optional[str] = None
    subscription_status: Optional[str] = None
    subscription_plan: Optional[str] = None
    subscription_expiry_date: Optional[datetime] = None
    admin_notes: Optional[str] = None
    email: Optional[EmailStr] = None

class UserAdminView(BaseModel):
    id: str = Field(..., alias='_id')
    username: str
    email: EmailStr
    role: str
    subscription_status: str
    # PHOENIX FIX: Added status to View so Admin can see it
    status: str = "inactive" 
    created_at: datetime
    last_login: Optional[datetime] = None
    case_count: int
    document_count: int

    @field_validator('id', mode='before')
    @classmethod
    def convert_objectid_to_str(cls, v: Any) -> str:
        if isinstance(v, ObjectId):
            return str(v)
        return v

    class Config:
        from_attributes = True
        populate_by_name = True 
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            ObjectId: lambda v: str(v), 
        }

class AdminUserOut(UserAdminView):
    pass