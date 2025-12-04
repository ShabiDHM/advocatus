# FILE: backend/app/models/finance.py
# PHOENIX PROTOCOL - FINANCE MODELS V2 (EXPENSES ADDED)
# 1. ADDED: ExpenseBase, ExpenseCreate, ExpenseInDB, ExpenseOut.
# 2. STATUS: Ready for database integration.

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime
from .common import PyObjectId

# --- INVOICE MODELS ---
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
    id: PyObjectId = Field(alias="_id", serialization_alias="id", default=None)

# --- EXPENSE MODELS (NEW) ---
class ExpenseBase(BaseModel):
    category: str  # e.g., "Office", "Software", "Travel", "Utilities"
    amount: float
    description: Optional[str] = None
    date: datetime = Field(default_factory=datetime.utcnow)
    currency: str = "EUR"

class ExpenseCreate(ExpenseBase):
    pass

class ExpenseInDB(ExpenseBase):
    id: PyObjectId = Field(alias="_id", default=None)
    user_id: PyObjectId
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

class ExpenseOut(ExpenseInDB):
    id: PyObjectId = Field(alias="_id", serialization_alias="id", default=None)