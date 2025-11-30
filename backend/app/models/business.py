# FILE: backend/app/models/business.py
# PHOENIX PROTOCOL - BUSINESS ENTITY (SOURCE OF TRUTH)
# 1. DEFINES: BusinessProfileUpdate and BusinessProfileInDB.
# 2. FIX: Explicitly includes 'logo_url' for frontend display.

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from .common import PyObjectId

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
    """
    Schema for updating profile details.
    Inherits fields from Base, all optional by default in Pydantic for updates 
    if strictly typed, but here we treat Base fields as updatable.
    """
    pass

class BusinessProfileInDB(BusinessProfileBase):
    """
    Schema for the Database Record.
    """
    id: PyObjectId = Field(alias="_id")
    user_id: PyObjectId
    
    logo_storage_key: Optional[str] = None
    logo_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

class BusinessProfileOut(BusinessProfileBase):
    id: str
    logo_url: Optional[str] = None
    is_complete: bool = False