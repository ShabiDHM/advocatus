# FILE: backend/app/services/finance_service.py
# PHOENIX PROTOCOL - FINANCE LOGIC (BUGFIX)
# 1. FIX: Removed redundant '_id' argument to prevent TypeError.
# 2. STATUS: Auto-calculation and numbering fully operational.

import structlog
from datetime import datetime, timezone
from bson import ObjectId
from pymongo.database import Database
from fastapi import HTTPException

from ..models.finance import InvoiceCreate, InvoiceInDB, InvoiceUpdate, InvoiceItem

logger = structlog.get_logger(__name__)

class FinanceService:
    def __init__(self, db: Database):
        self.db = db

    def _generate_invoice_number(self, user_id: str) -> str:
        """Generates simple sequential numbers per user (INV-2023-0001)."""
        count = self.db.invoices.count_documents({"user_id": ObjectId(user_id)})
        return f"INV-{datetime.now().year}-{count + 1:04d}"

    def create_invoice(self, user_id: str, data: InvoiceCreate) -> InvoiceInDB:
        # 1. Calculate Totals
        subtotal = sum(item.quantity * item.unit_price for item in data.items)
        # Update line item totals explicitly
        for item in data.items:
            item.total = item.quantity * item.unit_price
            
        tax_amount = (subtotal * data.tax_rate) / 100
        total_amount = subtotal + tax_amount

        # 2. Prepare Document
        invoice_doc = data.model_dump()
        invoice_doc.update({
            "user_id": ObjectId(user_id),
            "invoice_number": self._generate_invoice_number(user_id),
            "issue_date": datetime.now(timezone.utc),
            "due_date": data.due_date or datetime.now(timezone.utc),
            "subtotal": subtotal,
            "tax_amount": tax_amount,
            "total_amount": total_amount,
            "status": "DRAFT",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        })

        # 3. Insert (Modifies invoice_doc in-place to add _id)
        self.db.invoices.insert_one(invoice_doc)
        
        # PHOENIX FIX: 'invoice_doc' now contains '_id', so we just unpack it.
        return InvoiceInDB(**invoice_doc)

    def get_invoices(self, user_id: str) -> list[InvoiceInDB]:
        cursor = self.db.invoices.find({"user_id": ObjectId(user_id)}).sort("created_at", -1)
        # PHOENIX FIX: Removed redundant _id arg
        return [InvoiceInDB(**doc) for doc in cursor]

    def get_invoice(self, user_id: str, invoice_id: str) -> InvoiceInDB:
        doc = self.db.invoices.find_one({"_id": ObjectId(invoice_id), "user_id": ObjectId(user_id)})
        if not doc:
            raise HTTPException(status_code=404, detail="Invoice not found")
        # PHOENIX FIX: Removed redundant _id arg
        return InvoiceInDB(**doc)

    def update_invoice_status(self, user_id: str, invoice_id: str, status: str) -> InvoiceInDB:
        result = self.db.invoices.find_one_and_update(
            {"_id": ObjectId(invoice_id), "user_id": ObjectId(user_id)},
            {"$set": {"status": status, "updated_at": datetime.now(timezone.utc)}},
            return_document=True
        )
        if not result:
            raise HTTPException(status_code=404, detail="Invoice not found")
        # PHOENIX FIX: Removed redundant _id arg
        return InvoiceInDB(**result)