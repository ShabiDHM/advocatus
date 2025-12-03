# FILE: backend/app/models/admin.py
# PHOENIX PROTOCOL - UNIFIED UPDATE MODEL
# 1. ADDED: A new 'UserUpdateRequest' model that includes all fields the frontend can edit.
# 2. BEHAVIOR: This model will serve as the single source of truth for the user update endpoint.
# 3. CLEANUP: Preserves existing models for other functionalities.

from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# PHOENIX ADDITION: A comprehensive model for the unified update endpoint
class UserUpdateRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None

    # This is the critical "Gatekeeper" field
    subscription_status: Optional[str] = None

    # Include other potential fields from the old model for compatibility
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
    id: str
    username: str
    email: EmailStr
    role: str
    subscription_status: str
    created_at: datetime
    last_login: Optional[datetime] = None
    case_count: int
    document_count: int

    class Config:
        from_attributes = True
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

class AdminUserOut(UserAdminView):
    pass