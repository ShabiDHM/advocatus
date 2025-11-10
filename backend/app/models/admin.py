# FILE: backend/app/models/admin.py
# DEFINITIVE VERSION 5.1 (TYPO CORRECTION):
# 1. CRITICAL FIX: Corrected the decorator typo from '@field_tolower' to the valid
#    Pydantic decorator '@field_validator'.
# 2. This resolves the 'reportUndefinedVariable' build error and restores the integrity
#    of the data model.

from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, Literal, Any
from datetime import datetime

from .common import PyObjectId

class SubscriptionUpdate(BaseModel):
    subscription_status: Literal['active', 'expired', 'none']
    subscription_expiry_date: Optional[datetime] = None
    last_payment_date: Optional[datetime] = None
    last_payment_amount: Optional[float] = None
    admin_notes: Optional[str] = None

class AdminUserOut(BaseModel):
    """
    Definitive data model for the admin dashboard user list. Includes aggregated counts
    and matches the frontend's 'AdminUser' TypeScript interface precisely.
    """
    id: str = Field(alias="_id")
    username: str
    email: str
    role: str
    subscription_status: str
    created_at: datetime
    last_login: Optional[datetime] = None
    case_count: int
    document_count: int

    @field_validator('id', mode='before')
    @classmethod
    def id_to_str(cls, v: Any) -> str:
        return str(v)

    # PHOENIX PROTOCOL CURE: Corrected the decorator name from '@field_tolower'
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

# Retaining the old model name to avoid breaking other dependencies, but pointing it to the new one.
UserAdminView = AdminUserOut