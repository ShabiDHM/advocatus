# FILE: backend/app/models/finance.py
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict
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
    is_locked: bool = False

class InvoiceCreate(BaseModel):
    client_name: str
    client_email: Optional[str] = None
    client_address: Optional[str] = None
    items: List[InvoiceItem]
    tax_rate: float = 0.0
    due_date: Optional[datetime] = None
    notes: Optional[str] = None

class InvoiceUpdate(BaseModel):
    client_name: Optional[str] = None
    client_email: Optional[str] = None
    client_address: Optional[str] = None
    items: Optional[List[InvoiceItem]] = None
    tax_rate: Optional[float] = None
    due_date: Optional[datetime] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    is_locked: Optional[bool] = None

class InvoiceInDB(InvoiceBase):
    id: PyObjectId = Field(alias="_id", default=None)
    user_id: PyObjectId
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

class InvoiceOut(InvoiceInDB):
    id: str = Field(serialization_alias="id", default=None)

# --- EXPENSE MODELS ---
class ExpenseBase(BaseModel):
    category: str
    amount: float
    description: Optional[str] = None
    date: datetime = Field(default_factory=datetime.utcnow)
    currency: str = "EUR"
    receipt_url: Optional[str] = None
    related_case_id: Optional[str] = None
    is_locked: bool = False

class ExpenseCreate(ExpenseBase):
    pass

class ExpenseUpdate(BaseModel):
    category: Optional[str] = None
    amount: Optional[float] = None
    description: Optional[str] = None
    date: Optional[datetime] = None
    related_case_id: Optional[str] = None
    is_locked: Optional[bool] = None

class ExpenseInDB(ExpenseBase):
    id: PyObjectId = Field(alias="_id", default=None)
    user_id: PyObjectId
    created_at: datetime = Field(default_factory=datetime.utcnow)
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

class ExpenseOut(ExpenseInDB):
    id: str = Field(serialization_alias="id", default=None)

# --- TAX ENGINE MODELS ---
class TaxCalculation(BaseModel):
    period_month: int
    period_year: int
    total_sales_gross: float
    total_purchases_gross: float
    vat_collected: float
    vat_deductible: float
    net_obligation: float
    currency: str = "EUR"
    status: str
    regime: str = "SMALL_BUSINESS"
    tax_rate_applied: str = "9%" 
    description: str = "Tatimi"

class AuditIssue(BaseModel):
    id: str
    severity: str
    message: str
    related_item_id: Optional[str] = None
    item_type: Optional[str] = None

class WizardState(BaseModel):
    calculation: TaxCalculation
    issues: List[AuditIssue]
    ready_to_close: bool

# --- TRANSACTION & IMPORT MODELS ---
class ImportBatchBase(BaseModel):
    user_id: PyObjectId
    filename: str
    status: str 
    row_count: int = 0
    total_volume: float = 0.0
    error_message: Optional[str] = None

class ImportBatchInDB(ImportBatchBase):
    id: PyObjectId = Field(alias="_id", default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

class ImportBatchOut(BaseModel):
    id: str
    filename: str
    status: str
    row_count: int
    total_volume: float
    created_at: datetime

class TransactionBase(BaseModel):
    user_id: PyObjectId
    batch_id: PyObjectId
    transaction_ref: Optional[str] = None
    date_time: datetime
    product_name: str
    quantity: float = 1.0
    unit_price: float = 0.0
    total_amount: float
    currency: str = "EUR"
    vat_rate: Optional[float] = None
    category: Optional[str] = "Uncategorized"
    source_raw_data: dict = {}

class TransactionInDB(TransactionBase):
    id: PyObjectId = Field(alias="_id", default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

# --- COLUMN MAPPING MODELS ---
class ColumnMappingRuleInDB(BaseModel):
    id: PyObjectId = Field(alias="_id", default=None)
    user_id: PyObjectId
    source_signature: str
    mapping: Dict[str, str]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

class ColumnMappingCreate(BaseModel):
    mappings: Dict[str, str]