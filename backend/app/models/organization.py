# FILE: backend/app/models/organization.py
# PHOENIX PROTOCOL - ORGANIZATION MODEL V2.0 (TIER EXPANSION)
# 1. IMPLEMENTED: 'plan_tier', 'user_limit', 'current_active_users' per Blueprint.
# 2. RETAINED: Safe 'id' and 'owner_email' types.
# 3. MIGRATION: Replaced 'seat_limit'/'seat_count' with 'user_limit'/'current_active_users'.

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Any, Literal
from datetime import datetime

# Explicit Export
__all__ = ["OrganizationBase", "OrganizationInDB", "OrganizationOut"]

# Base Schema
class OrganizationBase(BaseModel):
    name: str
    owner_email: Optional[str] = None  # Production Safe: str instead of EmailStr
    
    # Tier Expansion Fields
    plan_tier: Literal['DEFAULT', 'GROWTH'] = 'DEFAULT'
    user_limit: int = 5
    current_active_users: int = 0
    
    status: str = "TRIAL"

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