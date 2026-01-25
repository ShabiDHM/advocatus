# FILE: backend/app/api/endpoints/finance.py
# PHOENIX PROTOCOL - FINANCE ROUTER V16.7 (MOBILE TO EXPENSE - VERIFIED STORAGE)
# 1. VERIFIED: Using actual storage service functions
# 2. FIXED: Type-safe file handling with correct signatures
# 3. OPTIMIZED: Uses copy_s3_object for efficient file movement

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Body
from fastapi.responses import StreamingResponse, JSONResponse
from typing import List, Annotated, Optional, Any, Dict, cast
from datetime import datetime, timedelta
from bson import ObjectId
from pymongo.database import Database 
import io
import asyncio
import os
import uuid
import json
import redis
import structlog

from app.models.user import UserInDB
from app.models.finance import (
    InvoiceCreate, InvoiceOut, InvoiceUpdate, 
    ExpenseCreate, ExpenseOut, ExpenseUpdate,
    AnalyticsDashboardData, SalesTrendPoint, TopProductItem,
    CaseFinancialSummary 
)
from app.models.archive import ArchiveItemOut 
from app.services.finance_service import FinanceService
from app.services.archive_service import ArchiveService
from app.services import report_service, ocr_service, llm_service 
from app.api.endpoints.dependencies import get_current_user, get_db, get_current_active_user
from app.core.config import settings
from app.services.storage_service import get_file_stream, copy_s3_object, delete_file


router = APIRouter(tags=["Finance"])
logger = structlog.get_logger(__name__)

redis_client: redis.Redis = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"), decode_responses=True)

# --- ANALYTICS & HISTORY ENDPOINTS (SYNC) ---

@router.get("/case-summary", response_model=List[CaseFinancialSummary])
def get_case_financial_summaries(
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    db: Database = Depends(get_db)
):
    user_oid = ObjectId(current_user.id)
    invoice_pipeline = [
        {"$match": {"user_id": user_oid, "status": {"$ne": "CANCELLED"}, "related_case_id": {"$exists": True, "$ne": None}}},
        {"$group": {"_id": "$related_case_id", "total_billed": {"$sum": "$total_amount"}}}
    ]
    expense_pipeline = [
        {"$match": {"user_id": user_oid, "related_case_id": {"$exists": True, "$ne": None}}},
        {"$group": {"_id": "$related_case_id", "total_expenses": {"$sum": "$amount"}}}
    ]
    billed_data = list(db["invoices"].aggregate(invoice_pipeline))
    expense_data = list(db["expenses"].aggregate(expense_pipeline))
    
    billed_map = {item['_id']: item['total_billed'] for item in billed_data}
    expense_map = {item['_id']: item['total_expenses'] for item in expense_data}
    all_case_ids = set(billed_map.keys()) | set(expense_map.keys())
    
    if not all_case_ids: return []

    case_oids = [ObjectId(cid) for cid in all_case_ids if ObjectId.is_valid(cid)]
    cases = list(db["cases"].find({"_id": {"$in": case_oids}}, {"title": 1, "case_number": 1}))
    case_map = {str(c["_id"]): c for c in cases}

    summaries = []
    for case_id in all_case_ids:
        if case_id in case_map:
            billed = billed_map.get(case_id, 0.0)
            expenses = expense_map.get(case_id, 0.0)
            summaries.append(CaseFinancialSummary(
                case_id=case_id,
                case_title=case_map[case_id].get("title", "Pa Titull"),
                case_number=case_map[case_id].get("case_number", ""),
                total_billed=billed,
                total_expenses=expenses,
                net_balance=billed - expenses
            ))
            
    return sorted(summaries, key=lambda s: s.total_billed, reverse=True)


@router.get("/analytics/dashboard", response_model=AnalyticsDashboardData)
def get_analytics_dashboard(
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    db: Database = Depends(get_db),
    days: int = 30
):
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    user_oid = ObjectId(current_user.id)

    inv_pipeline = [
        {"$match": {"user_id": user_oid, "issue_date": {"$gte": start_date, "$lte": end_date}, "status": {"$ne": "CANCELLED"}}},
        {"$unwind": "$items"},
        {"$project": {"date": "$issue_date", "amount": {"$multiply": ["$items.quantity", "$items.unit_price"]}, "product": "$items.description", "quantity": "$items.quantity"}}
    ]
    exp_pipeline = [
        {"$match": {"user_id": user_oid, "date": {"$gte": start_date, "$lte": end_date}}},
        {"$project": {"date": "$date", "amount": {"$multiply": ["$amount", -1]}}}
    ]
    
    inv_data = list(db["invoices"].aggregate(inv_pipeline))
    exp_data = list(db["expenses"].aggregate(exp_pipeline))
    
    total_revenue = sum(item['amount'] for item in inv_data)
    total_count = len(inv_data)
    
    trend_map: Dict[str, float] = {}
    product_map: Dict[str, Dict[str, float]] = {}

    for item in inv_data:
        date_obj = item["date"]
        if isinstance(date_obj, str):
            try: date_obj = datetime.fromisoformat(date_obj)
            except: pass
        
        date_key = date_obj.strftime("%Y-%m-%d") if isinstance(date_obj, datetime) else str(date_obj)
        
        trend_map[date_key] = trend_map.get(date_key, 0.0) + item['amount']
        prod_name = item.get("product", "Shërbim")
        if prod_name not in product_map: product_map[prod_name] = {"qty": 0, "rev": 0.0}
        product_map[prod_name]["qty"] += item.get('quantity', 0)
        product_map[prod_name]["rev"] += item['amount']

    for exp in exp_data:
        date_obj = exp["date"]
        if isinstance(date_obj, str):
            try: date_obj = datetime.fromisoformat(date_obj)
            except: pass
        
        date_key = date_obj.strftime("%Y-%m-%d") if isinstance(date_obj, datetime) else str(date_obj)
        trend_map[date_key] = trend_map.get(date_key, 0.0) + exp['amount']

    sales_trend = [SalesTrendPoint(date=k, amount=round(v, 2)) for k, v in sorted(trend_map.items())]
    sorted_products = sorted(product_map.items(), key=lambda i: i[1]['rev'], reverse=True)[:5]
    top_products = [TopProductItem(product_name=k, total_quantity=v['qty'], total_revenue=round(v['rev'], 2)) for k, v in sorted_products]

    return AnalyticsDashboardData(total_revenue_period=round(total_revenue, 2), total_transactions_period=total_count, sales_trend=sales_trend, top_products=top_products)

# --- INVOICES ---
@router.get("/invoices", response_model=List[InvoiceOut])
def get_invoices(current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    return FinanceService(db).get_invoices(str(current_user.id))

@router.post("/invoices", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED)
def create_invoice(invoice_in: InvoiceCreate, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    return FinanceService(db).create_invoice(str(current_user.id), invoice_in)

@router.get("/invoices/{invoice_id}", response_model=InvoiceOut)
def get_invoice_details(invoice_id: str, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    return FinanceService(db).get_invoice(str(current_user.id), invoice_id)

@router.put("/invoices/{invoice_id}", response_model=InvoiceOut)
def update_invoice(invoice_id: str, invoice_update: InvoiceUpdate, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    return FinanceService(db).update_invoice(str(current_user.id), invoice_id, invoice_update)

@router.put("/invoices/{invoice_id}/status", response_model=InvoiceOut)
def update_invoice_status(invoice_id: str, status_update: InvoiceUpdate, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    if not status_update.status: raise HTTPException(status_code=400, detail="Status is required")
    return FinanceService(db).update_invoice_status(str(current_user.id), invoice_id, status_update.status)

@router.delete("/invoices/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_invoice(invoice_id: str, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    FinanceService(db).delete_invoice(str(current_user.id), invoice_id)

@router.get("/invoices/{invoice_id}/pdf")
def download_invoice_pdf(invoice_id: str, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db), lang: Optional[str] = Query("sq")):
    service = FinanceService(db)
    invoice = service.get_invoice(str(current_user.id), invoice_id)
    pdf_buffer = report_service.generate_invoice_pdf(invoice, db, str(current_user.id), lang=lang or "sq")
    filename = f"Invoice_{invoice.invoice_number}.pdf"
    headers = {'Content-Disposition': f'inline; filename="{filename}"'}
    return StreamingResponse(pdf_buffer, media_type="application/pdf", headers=headers)

@router.post("/invoices/{invoice_id}/archive", response_model=ArchiveItemOut)
async def archive_invoice(invoice_id: str, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db), case_id: Optional[str] = Query(None), lang: Optional[str] = Query("sq")):
    finance_service = FinanceService(db)
    archive_service = ArchiveService(db)
    
    invoice = finance_service.get_invoice(str(current_user.id), invoice_id)
    pdf_buffer = report_service.generate_invoice_pdf(invoice, db, str(current_user.id), lang=lang or "sq")
    pdf_content = pdf_buffer.getvalue()
    
    filename = f"Invoice_{invoice.invoice_number}.pdf"
    title = f"Fatura #{invoice.invoice_number} - {invoice.client_name}"
    
    archived_item = await archive_service.save_generated_file(user_id=str(current_user.id), filename=filename, content=pdf_content, category="INVOICE", title=title, case_id=case_id)
    return archived_item

# --- FORENSIC REPORT ---
@router.post("/forensic-report/archive", response_model=ArchiveItemOut)
async def archive_forensic_report(
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db),
    case_id: str = Body(..., embed=True),
    title: str = Body(..., embed=True),
    content: str = Body(..., embed=True),
):
    archive_service = ArchiveService(db)
    pdf_buffer = report_service.create_pdf_from_text(text=content, document_title=title)
    pdf_bytes = pdf_buffer.getvalue()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    sanitized_title = "".join(c for c in title if c.isalnum() or c in (' ', '_')).replace(' ', '_')
    filename = f"ForensicReport_{sanitized_title}_{timestamp}.pdf"
    
    archived_item = await archive_service.save_generated_file(
        user_id=str(current_user.id),
        filename=filename,
        content=pdf_bytes,
        category="FORENSIC",
        title=title,
        case_id=case_id
    )
    return archived_item

# --- EXPENSES ---
@router.post("/expenses", response_model=ExpenseOut, status_code=status.HTTP_201_CREATED)
def create_expense(expense_in: ExpenseCreate, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    return FinanceService(db).create_expense(str(current_user.id), expense_in)

@router.get("/expenses", response_model=List[ExpenseOut])
def get_expenses(current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    return FinanceService(db).get_expenses(str(current_user.id))

@router.put("/expenses/{expense_id}", response_model=ExpenseOut)
def update_expense(expense_id: str, expense_update: ExpenseUpdate, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    return FinanceService(db).update_expense(str(current_user.id), expense_id, expense_update)

@router.delete("/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(expense_id: str, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    FinanceService(db).delete_expense(str(current_user.id), expense_id)

@router.put("/expenses/{expense_id}/receipt", status_code=status.HTTP_200_OK)
def upload_expense_receipt(expense_id: str, current_user: Annotated[UserInDB, Depends(get_current_user)], file: UploadFile = File(...), db: Database = Depends(get_db)):
    service = FinanceService(db)
    storage_key = service.upload_expense_receipt(str(current_user.id), expense_id, file)
    return {"status": "success", "storage_key": storage_key}

@router.get("/expenses/{expense_id}/receipt")
def get_expense_receipt(expense_id: str, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    service = FinanceService(db)
    file_stream = service.get_expense_receipt_stream(str(current_user.id), expense_id)
    return StreamingResponse(
        file_stream, 
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'inline; filename="receipt_{expense_id}"'}
    )

@router.post("/expenses/analyze-receipt", tags=["Finance", "AI"])
async def analyze_expense_receipt(
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    file: UploadFile = File(...)
):
    try:
        image_bytes = await file.read()
        ocr_text = await asyncio.to_thread(ocr_service.extract_text_from_image_bytes, image_bytes)
        if not ocr_text or len(ocr_text) < 5:
             return JSONResponse(content={"category": "", "amount": 0, "date": "", "description": ""})
        structured_data = await asyncio.to_thread(llm_service.extract_expense_details_from_text, ocr_text)
        return JSONResponse(content=structured_data)
    except Exception as e:
        print(f"Receipt analysis failed: {e}")
        return JSONResponse(content={"category": "", "amount": 0, "date": "", "description": ""})

# --- PHOENIX NEW: COMPLETE MOBILE UPLOAD → EXPENSE PIPELINE ---

@router.post("/mobile-upload-session")
def create_general_mobile_upload_session(
    current_user: Annotated[UserInDB, Depends(get_current_user)]
):
    token = f"GEN-{uuid.uuid4()}"
    host = os.getenv("SERVER_HOST", "https://juristi.tech")
    upload_url = f"{host}/upload/{token}" 
    
    session_data = {
        "user_id": str(current_user.id),
        "case_id": "GENERAL",
        "status": "pending",
        "created_at": datetime.utcnow().isoformat()
    }
    redis_client.setex(f"mobile_upload:{token}", 1800, json.dumps(session_data)) # 30 mins
    
    return {"upload_url": upload_url, "token": token}

@router.get("/mobile-upload-status/{token}")
def check_general_mobile_upload_status(token: str):
    data_str = cast(Optional[str], redis_client.get(f"mobile_upload:{token}"))
    if not data_str:
        raise HTTPException(status_code=404, detail="Session expired or invalid")
    
    data = json.loads(data_str)
    return {"status": data.get("status", "pending")}

@router.post("/mobile-upload/{token}")
async def public_general_mobile_upload(token: str, file: UploadFile = File(...), db: Database = Depends(get_db)):
    data_str = cast(Optional[str], redis_client.get(f"mobile_upload:{token}"))
    if not data_str:
        raise HTTPException(status_code=404, detail="Session expired")
    
    data = json.loads(data_str)
    if data.get("status") == "complete":
         return {"status": "already_completed"}

    # Upload to temporary storage
    service = FinanceService(db)
    temp_id = f"temp_{token}"
    storage_key = service.upload_temporary_receipt(data["user_id"], temp_id, file)
    
    # Update session with temp file info
    data["status"] = "uploaded"
    data["temp_storage_key"] = storage_key
    data["filename"] = file.filename
    data["content_type"] = file.content_type
    redis_client.setex(f"mobile_upload:{token}", 1800, json.dumps(data))
    
    return {"status": "success", "message": "File uploaded. Call /mobile-upload-create-expense to create expense."}

@router.post("/mobile-upload-create-expense/{token}")
async def create_expense_from_mobile_upload(
    token: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db),
    case_id: Optional[str] = Body(None, embed=True)
):
    """
    Complete the mobile upload pipeline:
    1. Get uploaded file from temp storage
    2. Analyze with OCR/LLM
    3. Create expense with extracted data
    4. Copy file to permanent storage using copy_s3_object
    5. Clean up temp file
    """
    # Get session data
    data_str = cast(Optional[str], redis_client.get(f"mobile_upload:{token}"))
    if not data_str:
        raise HTTPException(status_code=404, detail="Session expired or invalid")
    
    data = json.loads(data_str)
    if data.get("status") != "uploaded":
        raise HTTPException(status_code=400, detail="No file uploaded or already processed")
    
    # Verify user owns this session
    if data["user_id"] != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized for this session")
    
    temp_storage_key = data.get("temp_storage_key")
    if not temp_storage_key:
        raise HTTPException(status_code=400, detail="No file found in session")
    
    try:
        # 1. Get file from temp storage to verify it exists
        file_stream = get_file_stream(temp_storage_key)
        if not file_stream:
            raise HTTPException(status_code=404, detail="Temp file not found")
        file_stream.close()  # Just verifying, close immediately
        
        # 2. Analyze with OCR/LLM
        # Read file content for OCR processing
        file_stream = get_file_stream(temp_storage_key)
        file_content = b""
        for chunk in file_stream:
            file_content += chunk
        file_stream.close()
        
        ocr_text = await asyncio.to_thread(ocr_service.extract_text_from_image_bytes, file_content)
        if not ocr_text or len(ocr_text) < 5:
            raise HTTPException(status_code=400, detail="Could not extract text from image")
        
        structured_data = await asyncio.to_thread(llm_service.extract_expense_details_from_text, ocr_text)
        
        # 3. Create expense
        expense_service = FinanceService(db)
        
        # Parse date if available
        expense_date = datetime.utcnow()
        if structured_data.get("date"):
            try:
                expense_date = datetime.fromisoformat(structured_data["date"].replace('Z', '+00:00'))
            except:
                pass
        
        expense_data = ExpenseCreate(
            description=structured_data.get("description", f"Receipt {datetime.utcnow().strftime('%Y-%m-%d')}"),
            amount=structured_data.get("amount", 0.0),
            category=structured_data.get("category", "OTHER"),
            date=expense_date,
            related_case_id=case_id
        )
        
        expense = expense_service.create_expense(str(current_user.id), expense_data)
        
        # 4. Copy file to permanent storage using copy_s3_object
        # Destination folder: expenses/{user_id}
        dest_folder = f"expenses/{current_user.id}"
        permanent_storage_key = copy_s3_object(temp_storage_key, dest_folder)
        
        # Update expense with receipt URL
        expense_service.db.expenses.update_one(
            {"_id": ObjectId(expense.id)},
            {"$set": {"receipt_url": permanent_storage_key}}
        )
        
        # 5. Clean up temp file (optional - temp files auto-expire)
        try:
            delete_file(temp_storage_key)
            logger.info(f"Deleted temp file: {temp_storage_key}")
        except Exception as cleanup_error:
            logger.warning(f"Failed to delete temp file {temp_storage_key}: {cleanup_error}")
            # Non-critical error
        
        # Update session as complete
        data["status"] = "complete"
        data["expense_id"] = str(expense.id)
        data["permanent_storage_key"] = permanent_storage_key
        redis_client.setex(f"mobile_upload:{token}", 300, json.dumps(data))  # Keep for 5 more mins
        
        # Return the updated expense
        expense.receipt_url = permanent_storage_key
        return ExpenseOut(**expense.dict())
        
    except Exception as e:
        logger.error(f"Failed to create expense from mobile upload: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process upload: {str(e)}")

@router.get("/mobile-upload-file/{token}")
def get_general_mobile_session_file(token: str, current_user: Annotated[UserInDB, Depends(get_current_user)]):
    data_str = cast(Optional[str], redis_client.get(f"mobile_upload:{token}"))
    if not data_str:
        raise HTTPException(status_code=404, detail="Session expired")
    
    data = json.loads(data_str)
    if data.get("status") != "complete" or not data.get("storage_key"):
        raise HTTPException(status_code=400, detail="Upload not complete")
        
    storage_key = data["storage_key"]
    
    file_stream = get_file_stream(storage_key)
    if not file_stream:
        raise HTTPException(status_code=404, detail="File not found in storage")
    
    return StreamingResponse(
        file_stream, 
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'inline; filename="{data.get("filename", "receipt.jpg")}"'}
    )