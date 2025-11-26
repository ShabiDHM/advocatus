# FILE: backend/app/models/business.py
# PHOENIX PROTOCOL - BUSINESS ENTITY
# 1. IDENTITY: Stores firm details, logo, and branding color.
# 2. ONE-TO-ONE: Linked strictly to a single User (for now).

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class BusinessProfileBase(BaseModel):
    firm_name: str = "Zyra Ligjore"
    address: Optional[str] = None
    city: Optional[str] = "Prishtina"
    phone: Optional[str] = None
    email_public: Optional[str] = None
    website: Optional[str] = None
    tax_id: Optional[str] = None 
    branding_color: str = "#1f2937"

class BusinessProfileUpdate(BusinessProfileBase):
    pass

class BusinessProfileInDB(BusinessProfileBase):
    id: str = Field(alias="_id")
    user_id: str
    logo_storage_key: Optional[str] = None
    logo_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True

class BusinessProfileOut(BusinessProfileBase):
    id: str
    logo_url: Optional[str] = None
    is_complete: bool = False