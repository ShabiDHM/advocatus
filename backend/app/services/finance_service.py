# FILE: backend/app/services/finance_service.py
# PHOENIX PROTOCOL - FINANCE LOGIC V3.1
# 1. FIX: Absolute imports used for stability.

import structlog
from datetime import datetime, timezone
from bson import ObjectId
from pymongo.database import Database
from fastapi import HTTPException, UploadFile

# ABSOLUTE IMPORTS (Fixes "unknown import symbol")
from app.models.finance import (
    InvoiceCreate, InvoiceInDB, InvoiceUpdate, InvoiceItem, 
    ExpenseCreate, ExpenseInDB
)
from app.services import storage_service

logger = structlog.get_logger(__name__)

class FinanceService:
    def __init__(self, db: Database):
        self.db = db

    # --- INVOICE LOGIC ---
    def _generate_invoice_number(self, user_id: str) -> str:
        count = self.db.invoices.count_documents({"user_id": ObjectId(user_id)})
        year = datetime.now().year
        return f"Faktura-{year}-{count + 1:04d}"

    def create_invoice(self, user_id: str, data: InvoiceCreate) -> InvoiceInDB:
        subtotal = sum(item.quantity * item.unit_price for item in data.items)
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
        invoice_doc["_id"] = result.inserted_id
        return InvoiceInDB(**invoice_doc)

    def get_invoices(self, user_id: str) -> list[InvoiceInDB]:
        cursor = self.db.invoices.find({"user_id": ObjectId(user_id)}).sort("created_at", -1)
        return [InvoiceInDB(**doc) for doc in cursor]

    def get_invoice(self, user_id: str, invoice_id: str) -> InvoiceInDB:
        try: oid = ObjectId(invoice_id)
        except: raise HTTPException(status_code=400, detail="Invalid Invoice ID")
        doc = self.db.invoices.find_one({"_id": oid, "user_id": ObjectId(user_id)})
        if not doc: raise HTTPException(status_code=404, detail="Invoice not found")
        return InvoiceInDB(**doc)

    def update_invoice_status(self, user_id: str, invoice_id: str, status: str) -> InvoiceInDB:
        try: oid = ObjectId(invoice_id)
        except: raise HTTPException(status_code=400, detail="Invalid Invoice ID")
        result = self.db.invoices.find_one_and_update(
            {"_id": oid, "user_id": ObjectId(user_id)},
            {"$set": {"status": status, "updated_at": datetime.now(timezone.utc)}},
            return_document=True
        )
        if not result: raise HTTPException(status_code=404, detail="Invoice not found")
        return InvoiceInDB(**result)

    def delete_invoice(self, user_id: str, invoice_id: str) -> None:
        try: oid = ObjectId(invoice_id)
        except: raise HTTPException(status_code=400, detail="Invalid Invoice ID")
        result = self.db.invoices.delete_one({"_id": oid, "user_id": ObjectId(user_id)})
        if result.deleted_count == 0: raise HTTPException(status_code=404, detail="Invoice not found")

    # --- EXPENSE LOGIC ---
    def create_expense(self, user_id: str, data: ExpenseCreate) -> ExpenseInDB:
        expense_doc = data.model_dump()
        expense_doc.update({
            "user_id": ObjectId(user_id),
            "created_at": datetime.now(timezone.utc),
            "receipt_url": None
        })
        result = self.db.expenses.insert_one(expense_doc)
        expense_doc["_id"] = result.inserted_id
        return ExpenseInDB(**expense_doc)

    def get_expenses(self, user_id: str) -> list[ExpenseInDB]:
        cursor = self.db.expenses.find({"user_id": ObjectId(user_id)}).sort("date", -1)
        return [ExpenseInDB(**doc) for doc in cursor]

    def delete_expense(self, user_id: str, expense_id: str) -> None:
        try: oid = ObjectId(expense_id)
        except: raise HTTPException(status_code=400, detail="Invalid Expense ID")
        result = self.db.expenses.delete_one({"_id": oid, "user_id": ObjectId(user_id)})
        if result.deleted_count == 0: raise HTTPException(status_code=404, detail="Expense not found")

    def upload_expense_receipt(self, user_id: str, expense_id: str, file: UploadFile) -> str:
        try: oid = ObjectId(expense_id)
        except: raise HTTPException(status_code=400, detail="Invalid Expense ID")
        
        expense = self.db.expenses.find_one({"_id": oid, "user_id": ObjectId(user_id)})
        if not expense:
            raise HTTPException(status_code=404, detail="Expense not found")

        folder = f"expenses/{user_id}"
        storage_key = storage_service.upload_file_raw(file, folder)
        
        self.db.expenses.update_one(
            {"_id": oid},
            {"$set": {"receipt_url": storage_key}}
        )
        return storage_key