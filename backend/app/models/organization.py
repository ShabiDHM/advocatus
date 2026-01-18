# FILE: backend/app/models/organization.py
# PHOENIX PROTOCOL - ORGANIZATION MODEL V1.3 (SAFE TYPES)
# 1. FIX: Changed 'id' to 'str' and 'owner_email' to 'str' to prevent validation crashes.
# 2. STATUS: Production Safe.

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Any
from datetime import datetime

# Explicit Export
__all__ = ["OrganizationBase", "OrganizationInDB", "OrganizationOut"]

# Base Schema
class OrganizationBase(BaseModel):
    name: str
    owner_email: Optional[str] = None # Changed from EmailStr to str for safety
    plan: str = "TIER_1" 
    status: str = "TRIAL"
    seat_limit: int = 1
    seat_count: int = 1

# Database Schema
class OrganizationInDB(OrganizationBase):
    id: Any = Field(alias="_id", default=None)
    user_id: Any = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

# API Response Schema
class OrganizationOut(OrganizationBase):
    # PHOENIX FIX: Accept 'id' as string directly to avoid PyObjectId alias conflicts
    id: str 
    created_at: Optional[datetime] = None
    
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )