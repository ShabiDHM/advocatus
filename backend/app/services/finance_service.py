# FILE: backend/app/services/finance_service.py
# PHOENIX PROTOCOL - FINANCE SERVICE V3.1
# 1. FIX: Updated 'scan_receipt' to use the new 'llm_service.generate_text' method.
# 2. PERF: Wrapped LLM call in asyncio.to_thread to prevent blocking the event loop.

import structlog
import io
import json
import re
import asyncio
from datetime import datetime, timezone
from bson import ObjectId
from pymongo.database import Database
from fastapi import HTTPException, UploadFile
from PIL import Image
import pytesseract
from pdfminer.high_level import extract_text_to_fp

from ..models.finance import InvoiceCreate, InvoiceInDB, InvoiceUpdate, InvoiceItem, ExpenseCreate, ExpenseInDB
from . import llm_service 

logger = structlog.get_logger(__name__)

class FinanceService:
    def __init__(self, db: Database):
        self.db = db

    async def scan_receipt(self, file: UploadFile) -> dict:
        filename = file.filename.lower() if file.filename else ""
        content = await file.read()
        text_content = ""

        # 1. Extract Text
        try:
            if filename.endswith('.pdf'):
                output_string = io.StringIO()
                with io.BytesIO(content) as pdf_file:
                    extract_text_to_fp(pdf_file, output_string)
                text_content = output_string.getvalue()
            elif filename.endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp')):
                image = Image.open(io.BytesIO(content))
                text_content = pytesseract.image_to_string(image)
            else:
                text_content = content.decode('utf-8', errors='ignore')
        except Exception as e:
            logger.error(f"OCR Failed: {e}")
            raise HTTPException(status_code=422, detail="Could not read file content.")

        if not text_content.strip():
            raise HTTPException(status_code=422, detail="No text found in document.")

        # 2. AI Analysis
        system_prompt = """
        You are a financial accountant AI. Analyze the receipt text.
        Extract the following fields into a strictly valid JSON object:
        - "amount": (number) The total amount.
        - "date": (string) ISO format "YYYY-MM-DD" if found, else null.
        - "category": (string) Guess the category (e.g. Fuel, Food, Office, Rent, Salary, Services, Travel).
        - "description": (string) A short summary (vendor name + items).
        
        Return ONLY the JSON.
        """
        
        try:
            # PHOENIX FIX: Use asyncio.to_thread for blocking LLM call
            response_text = await asyncio.to_thread(
                llm_service.generate_text,
                user_prompt=f"RECEIPT TEXT:\n{text_content}",
                system_prompt=system_prompt,
                json_mode=True
            )
            
            cleaned_json = re.sub(r"```json|```", "", response_text).strip()
            data = json.loads(cleaned_json)
            return data

        except Exception as e:
            logger.error(f"AI Extraction Failed: {e}")
            return {"amount": 0, "date": None, "category": "General", "description": "Scan failed, please fill manually."}

    # --- INVOICE LOGIC (UNCHANGED) ---
    def _generate_invoice_number(self, user_id: str) -> str:
        count = self.db.invoices.count_documents({"user_id": ObjectId(user_id)})
        year = datetime.now().year
        return f"Faktura-{year}-{count + 1:04d}"

    def create_invoice(self, user_id: str, data: InvoiceCreate) -> InvoiceInDB:
        subtotal = sum(item.quantity * item.unit_price for item in data.items)
        for item in data.items: item.total = item.quantity * item.unit_price
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
        except: raise HTTPException(status_code=400, detail="Invalid Invoice ID format")
        doc = self.db.invoices.find_one({"_id": oid, "user_id": ObjectId(user_id)})
        if not doc: raise HTTPException(status_code=404, detail="Invoice not found")
        return InvoiceInDB(**doc)

    def update_invoice_status(self, user_id: str, invoice_id: str, status: str) -> InvoiceInDB:
        try: oid = ObjectId(invoice_id)
        except: raise HTTPException(status_code=400, detail="Invalid Invoice ID format")
        result = self.db.invoices.find_one_and_update({"_id": oid, "user_id": ObjectId(user_id)}, {"$set": {"status": status, "updated_at": datetime.now(timezone.utc)}}, return_document=True)
        if not result: raise HTTPException(status_code=404, detail="Invoice not found")
        return InvoiceInDB(**result)

    def delete_invoice(self, user_id: str, invoice_id: str) -> None:
        try: oid = ObjectId(invoice_id)
        except: raise HTTPException(status_code=400, detail="Invalid Invoice ID format")
        result = self.db.invoices.delete_one({"_id": oid, "user_id": ObjectId(user_id)})
        if result.deleted_count == 0: raise HTTPException(status_code=404, detail="Invoice not found")

    # --- EXPENSE LOGIC ---
    def create_expense(self, user_id: str, data: ExpenseCreate) -> ExpenseInDB:
        expense_doc = data.model_dump()
        expense_doc.update({"user_id": ObjectId(user_id), "created_at": datetime.now(timezone.utc)})
        result = self.db.expenses.insert_one(expense_doc)
        expense_doc["_id"] = result.inserted_id
        return ExpenseInDB(**expense_doc)

    def get_expenses(self, user_id: str) -> list[ExpenseInDB]:
        cursor = self.db.expenses.find({"user_id": ObjectId(user_id)}).sort("date", -1)
        return [ExpenseInDB(**doc) for doc in cursor]

    def delete_expense(self, user_id: str, expense_id: str) -> None:
        try: oid = ObjectId(expense_id)
        except: raise HTTPException(status_code=400, detail="Invalid Expense ID format")
        result = self.db.expenses.delete_one({"_id": oid, "user_id": ObjectId(user_id)})
        if result.deleted_count == 0: raise HTTPException(status_code=404, detail="Expense not found")