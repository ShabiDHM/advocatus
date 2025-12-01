# FILE: backend/app/services/finance_service.py
# PHOENIX PROTOCOL - FINANCE LOGIC v1.3
# 1. FORMAT: Changed Invoice Number schema to 'Faktura-YYYY-NNNN'.
# 2. VALIDATION: Added ObjectId validation to prevent crashes on invalid IDs.

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
        """
        Generates sequential numbers per user: Faktura-2025-0001.
        Replaces the old 'INV-' prefix.
        """
        count = self.db.invoices.count_documents({"user_id": ObjectId(user_id)})
        year = datetime.now().year
        # Format: Faktura-YYYY-0001
        return f"Faktura-{year}-{count + 1:04d}"

    def create_invoice(self, user_id: str, data: InvoiceCreate) -> InvoiceInDB:
        subtotal = sum(item.quantity * item.unit_price for item in data.items)
        # Ensure item totals are consistent
        for item in data.items:
            item.total = item.quantity * item.unit_price
            
        tax_amount = (subtotal * data.tax_rate) / 100
        total_amount = subtotal + tax_amount

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

        result = self.db.invoices.insert_one(invoice_doc)
        
        # Populate the _id for the return object
        invoice_doc["_id"] = result.inserted_id
        
        return InvoiceInDB(**invoice_doc)

    def get_invoices(self, user_id: str) -> list[InvoiceInDB]:
        cursor = self.db.invoices.find({"user_id": ObjectId(user_id)}).sort("created_at", -1)
        return [InvoiceInDB(**doc) for doc in cursor]

    def get_invoice(self, user_id: str, invoice_id: str) -> InvoiceInDB:
        try:
            oid = ObjectId(invoice_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid Invoice ID format")

        doc = self.db.invoices.find_one({"_id": oid, "user_id": ObjectId(user_id)})
        if not doc:
            raise HTTPException(status_code=404, detail="Invoice not found")
        return InvoiceInDB(**doc)

    def update_invoice_status(self, user_id: str, invoice_id: str, status: str) -> InvoiceInDB:
        try:
            oid = ObjectId(invoice_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid Invoice ID format")

        result = self.db.invoices.find_one_and_update(
            {"_id": oid, "user_id": ObjectId(user_id)},
            {"$set": {"status": status, "updated_at": datetime.now(timezone.utc)}},
            return_document=True
        )
        if not result:
            raise HTTPException(status_code=404, detail="Invoice not found")
        return InvoiceInDB(**result)

    def delete_invoice(self, user_id: str, invoice_id: str) -> None:
        """Permanently removes an invoice."""
        try:
            oid = ObjectId(invoice_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid Invoice ID format")

        result = self.db.invoices.delete_one({
            "_id": oid,
            "user_id": ObjectId(user_id)
        })
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Invoice not found or could not be deleted.")