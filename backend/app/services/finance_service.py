# FILE: backend/app/services/finance_service.py
# PHOENIX PROTOCOL - FINANCE LOGIC V5.1 (CIRCULAR IMPORT FIX)
# 1. FIX: Changed 'from app.services import storage_service' to specific import to break circular dependency.
# 2. STATUS: Fully functional async/sync service.

import structlog
from datetime import datetime, timezone
from bson import ObjectId
from pymongo.database import Database
from fastapi import HTTPException, UploadFile
from typing import Any

# ABSOLUTE IMPORTS
from app.models.finance import (
    InvoiceCreate, InvoiceInDB, InvoiceUpdate, InvoiceItem, 
    ExpenseCreate, ExpenseInDB, ExpenseUpdate
)
# PHOENIX FIX: Direct import to avoid circular dependency with __init__.py
from app.services.storage_service import upload_file_raw

logger = structlog.get_logger(__name__)

class FinanceService:
    def __init__(self, db: Database):
        self.db = db

    # --- POS / INTEGRATION HUB LOGIC ---
    async def get_monthly_pos_revenue(self, async_db: Any, user_id: str, month: int, year: int) -> float:
        """
        Calculates total revenue from imported POS transactions for a specific month.
        Requires the async motor database instance.
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
                        "date_time": {
                            "$gte": start_date,
                            "$lt": end_date
                        }
                    }
                },
                {
                    "$group": {
                        "_id": None,
                        "total_revenue": {"$sum": "$total_amount"}
                    }
                }
            ]

            result = await async_db["transactions"].aggregate(pipeline).to_list(length=1)
            if result:
                return float(result[0]["total_revenue"])
            return 0.0
        except Exception as e:
            logger.error(f"Error calculating POS revenue: {e}")
            return 0.0

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

    def update_invoice(self, user_id: str, invoice_id: str, update_data: InvoiceUpdate) -> InvoiceInDB:
        try: oid = ObjectId(invoice_id)
        except: raise HTTPException(status_code=400, detail="Invalid Invoice ID")
        
        # 1. Fetch existing
        existing = self.db.invoices.find_one({"_id": oid, "user_id": ObjectId(user_id)})
        if not existing: raise HTTPException(status_code=404, detail="Invoice not found")
        
        if existing.get("is_locked"):
            raise HTTPException(status_code=403, detail="Cannot edit a locked/closed invoice.")

        # 2. Prepare Update Dictionary
        update_dict = update_data.model_dump(exclude_unset=True)
        
        # 3. Recalculate Totals if items or tax changed
        if "items" in update_dict or "tax_rate" in update_dict:
            # Use new values or fall back to existing
            items_data = update_dict.get("items", existing["items"])
            tax_rate = update_dict.get("tax_rate", existing["tax_rate"])
            
            # Convert dict items back to objects if needed
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
            
            update_dict["items"] = new_items
            update_dict["subtotal"] = subtotal
            update_dict["tax_amount"] = tax_amount
            update_dict["total_amount"] = total_amount

        update_dict["updated_at"] = datetime.now(timezone.utc)

        # 4. Perform Update
        result = self.db.invoices.find_one_and_update(
            {"_id": oid},
            {"$set": update_dict},
            return_document=True
        )
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
        
        # Prevent deleting locked invoices
        existing = self.db.invoices.find_one({"_id": oid, "user_id": ObjectId(user_id)})
        if existing and existing.get("is_locked"):
             raise HTTPException(status_code=403, detail="Cannot delete a locked/closed invoice.")
             
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

    def update_expense(self, user_id: str, expense_id: str, update_data: ExpenseUpdate) -> ExpenseInDB:
        try: oid = ObjectId(expense_id)
        except: raise HTTPException(status_code=400, detail="Invalid Expense ID")
        
        existing = self.db.expenses.find_one({"_id": oid, "user_id": ObjectId(user_id)})
        if not existing: raise HTTPException(status_code=404, detail="Expense not found")
        if existing.get("is_locked"):
            raise HTTPException(status_code=403, detail="Cannot edit a locked expense.")

        update_dict = update_data.model_dump(exclude_unset=True)
        
        result = self.db.expenses.find_one_and_update(
            {"_id": oid},
            {"$set": update_dict},
            return_document=True
        )
        return ExpenseInDB(**result)

    def delete_expense(self, user_id: str, expense_id: str) -> None:
        try: oid = ObjectId(expense_id)
        except: raise HTTPException(status_code=400, detail="Invalid Expense ID")
        
        existing = self.db.expenses.find_one({"_id": oid, "user_id": ObjectId(user_id)})
        if existing and existing.get("is_locked"):
             raise HTTPException(status_code=403, detail="Cannot delete a locked expense.")

        result = self.db.expenses.delete_one({"_id": oid, "user_id": ObjectId(user_id)})
        if result.deleted_count == 0: raise HTTPException(status_code=404, detail="Expense not found")

    def upload_expense_receipt(self, user_id: str, expense_id: str, file: UploadFile) -> str:
        try: oid = ObjectId(expense_id)
        except: raise HTTPException(status_code=400, detail="Invalid Expense ID")
        
        expense = self.db.expenses.find_one({"_id": oid, "user_id": ObjectId(user_id)})
        if not expense:
            raise HTTPException(status_code=404, detail="Expense not found")

        folder = f"expenses/{user_id}"
        # PHOENIX FIX: Using the directly imported function
        storage_key = upload_file_raw(file, folder)
        
        self.db.expenses.update_one(
            {"_id": oid},
            {"$set": {"receipt_url": storage_key}}
        )
        return storage_key