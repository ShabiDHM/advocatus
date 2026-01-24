# FILE: backend/app/services/finance_service.py
# PHOENIX PROTOCOL - FINANCE SERVICE V8.2 (TEMP UPLOAD)
# 1. ADDED: New 'upload_temporary_receipt' method.
# 2. LOGIC: This new method bypasses all database validation, safely storing files for mobile sessions.

import structlog
import json
from datetime import datetime, timezone
from bson import ObjectId
from pymongo.database import Database
from fastapi import HTTPException, UploadFile
from typing import Any, Dict, List, Optional, Union

from app.models.finance import (
    InvoiceCreate, InvoiceInDB, InvoiceUpdate, 
    ExpenseCreate, ExpenseInDB, ExpenseUpdate
)
import app.services.llm_service as llm_service
from app.services.storage_service import upload_file_raw, get_file_stream

logger = structlog.get_logger(__name__)

class FinanceService:
    def __init__(self, db: Database):
        self.db = db

    # --- ANALYTICS & AI ---

    def get_monthly_pos_revenue(self, db: Database, user_id: str, month: int, year: int) -> float:
        """
        Synchronous calculation of POS revenue using PyMongo.
        """
        try:
            start_date = datetime(year, month, 1)
            if month == 12:
                end_date = datetime(year + 1, 1, 1)
            else:
                end_date = datetime(year, month + 1, 1)

            pipeline = [
                {
                    "$match": {
                        "user_id": ObjectId(user_id),
                        "date_time": {"$gte": start_date, "$lt": end_date}
                    }
                },
                {
                    "$group": {
                        "_id": None,
                        "total_revenue": {"$sum": "$total_amount"}
                    }
                }
            ]

            # Sync aggregation
            result = list(db["transactions"].aggregate(pipeline))
            
            if result:
                return float(result[0]["total_revenue"])
            return 0.0
        except Exception as e:
            logger.error(f"Error calculating POS revenue: {e}")
            return 0.0

    def generate_ai_report(self, user_id: str, db: Database) -> Dict[str, Any]:
        """
        Aggregates data and asks the Forensic Accountant for a JSON report (Sync).
        """
        try:
            invoices = list(self.db.invoices.find({"user_id": ObjectId(user_id)}).sort("issue_date", -1).limit(30))
            expenses = list(self.db.expenses.find({"user_id": ObjectId(user_id)}).sort("date", -1).limit(30))
            
            now = datetime.now()
            # Sync call
            pos_revenue = self.get_monthly_pos_revenue(db, user_id, now.month, now.year)

            financial_snapshot = {
                "report_period": now.strftime("%B %Y"),
                "currency": "EUR",
                "cash_flow_summary": {
                    "pos_revenue": pos_revenue,
                    "invoices_total": sum(i.get("total_amount", 0) for i in invoices),
                    "expenses_total": sum(e.get("amount", 0) for e in expenses)
                },
                "recent_invoices": [
                    {
                        "date": str(i.get("issue_date")),
                        "amount": i.get("total_amount"),
                        "status": i.get("status"),
                        "client": i.get("client_name", "Unknown")
                    } for i in invoices
                ],
                "recent_expenses": [
                    {
                        "date": str(e.get("date")),
                        "amount": e.get("amount"),
                        "category": e.get("category"),
                        "description": e.get("description", "")
                    } for e in expenses
                ]
            }

            json_context = json.dumps(financial_snapshot, default=str)
            ai_report_json = llm_service.analyze_financial_portfolio(json_context)
            
            return ai_report_json

        except Exception as e:
            logger.error(f"AI Report Gen Failed: {e}")
            return {"error": "Gabim gjatë gjenerimit.", "executive_summary": "Nuk mund të gjenerohej raporti."}

    # --- INVOICE CRUD (Preserved) ---
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

    def get_invoices(self, user_id: str) -> List[InvoiceInDB]:
        cursor = self.db.invoices.find({"user_id": ObjectId(user_id)}).sort("created_at", -1)
        return [InvoiceInDB(**doc) for doc in cursor]

    def get_invoice(self, user_id: str, invoice_id: str) -> InvoiceInDB:
        try: oid = ObjectId(invoice_id)
        except: raise HTTPException(status_code=400, detail="Invalid Invoice ID")
        doc = self.db.invoices.find_one({"_id": oid, "user_id": ObjectId(user_id)})
        if not doc: raise HTTPException(status_code=404, detail="Invoice not found")
        return InvoiceInDB(**doc)

    def update_invoice(self, user_id: str, invoice_id: str, update_data: InvoiceUpdate) -> InvoiceInDB:
        try: oid = ObjectId(invoice_id)
        except: raise HTTPException(status_code=400, detail="Invalid Invoice ID")
        
        existing = self.db.invoices.find_one({"_id": oid, "user_id": ObjectId(user_id)})
        if not existing: raise HTTPException(status_code=404, detail="Invoice not found")
        if existing.get("is_locked"): raise HTTPException(status_code=403, detail="Cannot edit a locked invoice.")

        update_dict = update_data.model_dump(exclude_unset=True)
        
        if "items" in update_dict or "tax_rate" in update_dict:
            items_data = update_dict.get("items", existing["items"])
            tax_rate = update_dict.get("tax_rate", existing["tax_rate"])
            subtotal = 0.0
            new_items = []
            for item in items_data:
                q = item["quantity"] if isinstance(item, dict) else item.quantity
                p = item["unit_price"] if isinstance(item, dict) else item.unit_price
                row_total = q * p
                subtotal += row_total
                item_dict = item if isinstance(item, dict) else item.model_dump()
                item_dict["total"] = row_total
                new_items.append(item_dict)
            
            tax_amount = (subtotal * tax_rate) / 100
            total_amount = subtotal + tax_amount
            update_dict.update({"items": new_items, "subtotal": subtotal, "tax_amount": tax_amount, "total_amount": total_amount})

        update_dict["updated_at"] = datetime.now(timezone.utc)
        result = self.db.invoices.find_one_and_update({"_id": oid}, {"$set": update_dict}, return_document=True)
        return InvoiceInDB(**result)

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
        existing = self.db.invoices.find_one({"_id": oid, "user_id": ObjectId(user_id)})
        if existing and existing.get("is_locked"): raise HTTPException(status_code=403, detail="Cannot delete a locked invoice.")
        result = self.db.invoices.delete_one({"_id": oid, "user_id": ObjectId(user_id)})
        if result.deleted_count == 0: raise HTTPException(status_code=404, detail="Invoice not found")

    # --- EXPENSE CRUD ---
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

    def get_expense(self, user_id: str, expense_id: str) -> ExpenseInDB:
        try: oid = ObjectId(expense_id)
        except: raise HTTPException(status_code=400, detail="Invalid Expense ID")
        doc = self.db.expenses.find_one({"_id": oid, "user_id": ObjectId(user_id)})
        if not doc: raise HTTPException(status_code=404, detail="Expense not found")
        return ExpenseInDB(**doc)

    def get_expenses(self, user_id: str) -> List[ExpenseInDB]:
        cursor = self.db.expenses.find({"user_id": ObjectId(user_id)}).sort("date", -1)
        return [ExpenseInDB(**doc) for doc in cursor]

    def update_expense(self, user_id: str, expense_id: str, update_data: ExpenseUpdate) -> ExpenseInDB:
        try: oid = ObjectId(expense_id)
        except: raise HTTPException(status_code=400, detail="Invalid Expense ID")
        existing = self.db.expenses.find_one({"_id": oid, "user_id": ObjectId(user_id)})
        if not existing: raise HTTPException(status_code=404, detail="Expense not found")
        if existing.get("is_locked"): raise HTTPException(status_code=403, detail="Cannot edit a locked expense.")

        update_dict = update_data.model_dump(exclude_unset=True)
        result = self.db.expenses.find_one_and_update({"_id": oid}, {"$set": update_dict}, return_document=True)
        return ExpenseInDB(**result)

    def delete_expense(self, user_id: str, expense_id: str) -> None:
        try: oid = ObjectId(expense_id)
        except: raise HTTPException(status_code=400, detail="Invalid Expense ID")
        existing = self.db.expenses.find_one({"_id": oid, "user_id": ObjectId(user_id)})
        if existing and existing.get("is_locked"): raise HTTPException(status_code=403, detail="Cannot delete a locked expense.")
        result = self.db.expenses.delete_one({"_id": oid, "user_id": ObjectId(user_id)})
        if result.deleted_count == 0: raise HTTPException(status_code=404, detail="Expense not found")

    def upload_expense_receipt(self, user_id: str, expense_id: str, file: UploadFile) -> str:
        try: oid = ObjectId(expense_id)
        except: raise HTTPException(status_code=400, detail="Invalid Expense ID")
        expense = self.db.expenses.find_one({"_id": oid, "user_id": ObjectId(user_id)})
        if not expense: raise HTTPException(status_code=404, detail="Expense not found")
        
        folder = f"expenses/{user_id}"
        storage_key = upload_file_raw(file, folder)
        self.db.expenses.update_one({"_id": oid}, {"$set": {"receipt_url": storage_key}})
        return storage_key

    # PHOENIX: New dedicated method for temporary mobile uploads
    def upload_temporary_receipt(self, user_id: str, temp_id: str, file: UploadFile) -> str:
        """
        Uploads a file to a temporary location for a mobile session without DB validation.
        """
        # We create a unique folder path to avoid conflicts
        folder = f"temp_uploads/{user_id}/{temp_id}"
        storage_key = upload_file_raw(file, folder)
        return storage_key

    def get_expense_receipt_stream(self, user_id: str, expense_id: str) -> Any:
        try: oid = ObjectId(expense_id)
        except: raise HTTPException(status_code=400, detail="Invalid Expense ID")
        
        expense = self.db.expenses.find_one({"_id": oid, "user_id": ObjectId(user_id)})
        if not expense: raise HTTPException(status_code=404, detail="Expense not found")
        
        storage_key = expense.get("receipt_url")
        if not storage_key or storage_key == "PENDING_REFRESH":
            raise HTTPException(status_code=404, detail="Receipt not found for this expense.")
            
        return get_file_stream(storage_key)