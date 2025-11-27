# FILE: backend/app/models/admin.py
# PHOENIX PROTOCOL - USER STATUS FIX
# 1. NEW FIELD: Added the missing 'status' field to the SubscriptionUpdate model.
# 2. VALIDATOR: Added a validator to normalize the status to lowercase, matching other fields.
# 3. RESULT: The backend model now correctly aligns with the frontend, resolving the 422 error.

from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, Any
from datetime import datetime

from .common import PyObjectId

class SubscriptionUpdate(BaseModel):
    subscription_status: Optional[str] = None
    subscription_expiry_date: Optional[datetime] = None
    last_payment_date: Optional[datetime] = None
    last_payment_amount: Optional[float] = None
    admin_notes: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None # <--- ADDED MISSING FIELD

    @field_validator('subscription_status', 'status', mode='before')
    @classmethod
    def normalize_status_fields(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        if isinstance(v, str):
            # Normalize to backend format (lowercase)
            return v.lower()
        return v

    @field_validator('role', mode='before')
    @classmethod
    def normalize_role(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        if isinstance(v, str):
            return v.upper()
        return v

class AdminUserOut(BaseModel):
    id: str = Field(alias="_id")
    username: str
    email: str
    role: str
    status: Optional[str] = 'active' # Ensure status is part of the output
    subscription_status: Optional[str] = None
    created_at: datetime
    last_login: Optional[datetime] = None
    case_count: int
    document_count: int

    @field_validator('id', mode='before')
    @classmethod
    def id_to_str(cls, v: Any) -> str:
        return str(v)

    @field_validator('role', mode='before')
    @classmethod
    def role_to_uppercase(cls, v: str) -> str:
        if isinstance(v, str):
            return v.upper()
        return v

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

UserAdminView = AdminUserOut