# FILE: backend/app/models/finance.py
# PHOENIX PROTOCOL - FINANCIAL MODELS (TYPE FIX)
# 1. FIX: Added default=None to 'id' fields to satisfy Pylance inheritance rules.
# 2. STRUCTURE: Supports line items, tax calculations, and status tracking.

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime
from .common import PyObjectId

class InvoiceItem(BaseModel):
    description: str
    quantity: float = 1.0
    unit_price: float = 0.0
    total: float = 0.0

class InvoiceBase(BaseModel):
    invoice_number: Optional[str] = None
    client_name: str
    client_email: Optional[str] = None
    client_address: Optional[str] = None
    
    issue_date: datetime = Field(default_factory=datetime.utcnow)
    due_date: datetime = Field(default_factory=datetime.utcnow)
    
    items: List[InvoiceItem] = []
    notes: Optional[str] = None
    
    subtotal: float = 0.0
    tax_rate: float = 0.0 
    tax_amount: float = 0.0
    total_amount: float = 0.0
    
    currency: str = "EUR"
    status: str = "DRAFT" 

class InvoiceCreate(BaseModel):
    client_name: str
    client_email: Optional[str] = None
    client_address: Optional[str] = None
    items: List[InvoiceItem]
    tax_rate: float = 0.0
    due_date: Optional[datetime] = None
    notes: Optional[str] = None

class InvoiceUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None

class InvoiceInDB(InvoiceBase):
    id: PyObjectId = Field(alias="_id", default=None)
    user_id: PyObjectId
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

class InvoiceOut(InvoiceInDB):
    # PHOENIX FIX: Added default=None to match base class signature
    id: PyObjectId = Field(alias="_id", serialization_alias="id", default=None)