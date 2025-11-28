# FILE: backend/app/models/business.py
# PHOENIX PROTOCOL - BUSINESS ENTITY (TYPE SAFE)
# 1. FIX: Used 'PyObjectId' for '_id' and 'user_id' to handle MongoDB ObjectIds.
# 2. STATUS: Compatible with Pydantic V2 and MongoDB.

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
    pass

class BusinessProfileInDB(BusinessProfileBase):
    # PHOENIX FIX: Use PyObjectId to accept BSON ObjectIds from Mongo
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