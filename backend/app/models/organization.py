# FILE: backend/app/models/organization.py
# PHOENIX PROTOCOL - ORGANIZATION MODEL V2.1 (CORRECTED BASELINE)
# 1. CORRECTED: 'user_limit' default changed from 5 to 1 (Single User).

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Any, Literal
from datetime import datetime

# Explicit Export
__all__ = ["OrganizationBase", "OrganizationInDB", "OrganizationOut"]

# Base Schema
class OrganizationBase(BaseModel):
    name: str
    owner_email: Optional[str] = None 
    
    # Tier Expansion Fields
    plan_tier: Literal['DEFAULT', 'GROWTH'] = 'DEFAULT'
    user_limit: int = 1  # <--- RESTORED TO SINGLE USER BASELINE
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
    id: str 
    created_at: Optional[datetime] = None
    
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )