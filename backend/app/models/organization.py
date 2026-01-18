# FILE: backend/app/models/organization.py
# PHOENIX PROTOCOL - ORGANIZATION MODEL V1.0 (TENANT FOUNDATION)
# 1. STRATEGY: Defines the 'Tenant' entity that holds Users and Data.
# 2. LOGIC: Controls 'tier' (TIER_1 vs TIER_2) and 'max_seats' (1 vs 5).

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from .common import PyObjectId

# Base Organization Attributes
class OrganizationBase(BaseModel):
    name: str
    tier: str = "TIER_1"  # "TIER_1" (Solo) or "TIER_2" (Small Firm)
    max_seats: int = 1    # 1 for Tier 1, 5 for Tier 2
    
    # Shared Branding (Replaces User-level branding eventually)
    logo: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None

# Creation Request
class OrganizationCreate(OrganizationBase):
    pass

# Update Request
class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    tier: Optional[str] = None
    max_seats: Optional[int] = None
    logo: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None

# DB Model
class OrganizationInDB(OrganizationBase):
    id: PyObjectId = Field(alias="_id", default=None)
    owner_id: PyObjectId  # The Super Admin / Payer
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

# Public Response
class OrganizationOut(OrganizationBase):
    id: PyObjectId = Field(alias="_id", serialization_alias="id")
    owner_id: PyObjectId
    created_at: datetime
    
    # Dynamic field to be populated by service layer
    current_member_count: int = 0

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
        arbitrary_types_allowed=True,
    )