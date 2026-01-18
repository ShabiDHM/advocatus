# FILE: backend/app/models/organization.py
# PHOENIX PROTOCOL - ORGANIZATION MODEL V1.0
# 1. STATUS: Critical dependency for Admin Router. Prevents Startup Crash.

from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import Optional, List
from datetime import datetime
from .common import PyObjectId

class OrganizationBase(BaseModel):
    name: str
    owner_email: Optional[EmailStr] = None
    plan: str = "TIER_1" # TIER_1 (Personal), TIER_2 (Organization)
    status: str = "TRIAL"
    seat_limit: int = 1
    seat_count: int = 1

class OrganizationOut(OrganizationBase):
    id: str
    created_at: Optional[datetime] = None
    
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )