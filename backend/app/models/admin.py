# FILE: backend/app/models/admin.py
# PHOENIX PROTOCOL - DATA MODEL RESILIENCE
# 1. FIX: The 'id' field in 'UserAdminView' is now configured to alias the '_id' field from MongoDB.
# 2. BEHAVIOR: A validator has been added to automatically convert the BSON ObjectId to a string, making the model resilient to the database's native format.
# 3. RESULT: This prevents response validation errors by correctly mapping the database schema to the API schema.

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

class SubscriptionUpdate(BaseModel):
    role: Optional[str] = None
    status: Optional[str] = None
    subscription_status: Optional[str] = None
    subscription_plan: Optional[str] = None
    subscription_expiry_date: Optional[datetime] = None
    admin_notes: Optional[str] = None
    email: Optional[EmailStr] = None

class UserAdminView(BaseModel):
    # PHOENIX FIX: Alias '_id' from MongoDB to the 'id' field in the API response.
    id: str = Field(..., alias='_id')
    username: str
    email: EmailStr
    role: str
    subscription_status: str
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
        populate_by_name = True # Enables the use of aliases
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            ObjectId: lambda v: str(v), # Ensure ObjectId is always serialized to string
        }

class AdminUserOut(UserAdminView):
    pass