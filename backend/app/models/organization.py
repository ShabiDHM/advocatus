# FILE: backend/app/models/organization.py
# PHOENIX PROTOCOL - ORGANIZATION MODEL V1.2 (EXPORT FIX)
# 1. FIX: Added '__all__' to explicitly export symbols for Pylance.
# 2. STATUS: Contains OrganizationBase, OrganizationInDB, and OrganizationOut.

from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import Optional, List
from datetime import datetime
from .common import PyObjectId

# Explicit Export
__all__ = ["OrganizationBase", "OrganizationInDB", "OrganizationOut"]

# Base Schema
class OrganizationBase(BaseModel):
    name: str
    owner_email: Optional[EmailStr] = None
    plan: str = "TIER_1" # TIER_1 (Personal), TIER_2 (Organization)
    status: str = "TRIAL"
    seat_limit: int = 1
    seat_count: int = 1

# Database Schema (Stored in MongoDB)
class OrganizationInDB(OrganizationBase):
    id: PyObjectId = Field(alias="_id", default=None)
    user_id: Optional[PyObjectId] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

# API Response Schema (Returned to Frontend)
class OrganizationOut(OrganizationBase):
    id: PyObjectId = Field(alias="_id", serialization_alias="id")
    created_at: Optional[datetime] = None
    
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
        arbitrary_types_allowed=True,
    )