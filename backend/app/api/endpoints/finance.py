# FILE: backend/app/api/endpoints/finance.py
# PHOENIX PROTOCOL - FINANCE ROUTER V18.0 (MOBILE SCANNING FIXED)
# FIXED: /expenses/analyze-receipt now auto-creates expenses
# FIXED: Single-step mobile scanning works end-to-end

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
import boto3
from botocore.exceptions import ClientError

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
from app.services.report_service import generate_invoice_pdf, create_pdf_from_text
from app.services.ocr_service import extract_text_from_image_bytes
from app.services.llm_service import extract_expense_details_from_text
from app.api.endpoints.dependencies import get_current_user, get_db, get_current_active_user
from app.core.config import settings
from app.services.storage_service import get_file_stream, copy_s3_object, delete_file


router = APIRouter(tags=["Finance"])
logger = structlog.get_logger(__name__)

redis_client: redis.Redis = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"), decode_responses=True)

# Helper function for direct B2 upload (bypasses UploadFile requirements)
def upload_bytes_to_b2(content: bytes, folder: str, filename: str, content_type: str = "application/octet-stream") -> str:
    """
    Direct upload to Backblaze B2 without requiring UploadFile object.
    """
    try:
        # Get B2 configuration from environment
        b2_key_id = os.getenv("B2_KEY_ID", "")
        b2_app_key = os.getenv("B2_APPLICATION_KEY", "")
        b2_bucket = os.getenv("B2_BUCKET_NAME", "advocatus-ai")
        b2_endpoint = os.getenv("B2_ENDPOINT_URL", "")
        
        if not all([b2_key_id, b2_app_key, b2_bucket, b2_endpoint]):
            raise ValueError("B2 storage configuration missing")
        
        # Parse endpoint to get region and host
        # endpoint format: https://s3.eu-central-003.backblazeb2.com
        endpoint_parts = b2_endpoint.replace("https://", "").split(".")
        if len(endpoint_parts) < 2:
            raise ValueError(f"Invalid B2 endpoint: {b2_endpoint}")
        
        # Create S3 client for B2
        s3_client = boto3.client(
            's3',
            endpoint_url=b2_endpoint,
            aws_access_key_id=b2_key_id,
            aws_secret_access_key=b2_app_key
        )
        
        # Create storage key
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_filename = "".join(c for c in filename if c.isalnum() or c in ('.', '-', '_')).rstrip()
        storage_key = f"{folder}/{timestamp}_{safe_filename}"
        
        # Upload bytes directly
        s3_client.put_object(
            Bucket=b2_bucket,
            Key=storage_key,
            Body=content,
            ContentType=content_type,
            Metadata={
                'original-filename': filename,
                'upload-timestamp': timestamp,
                'upload-source': 'mobile-direct'
            }
        )
        
        logger.info(f"Direct B2 upload successful: {storage_key} ({len(content)} bytes)")
        return storage_key
        
    except ClientError as e:
        logger.error(f"B2 upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Storage upload failed: {str(e)}")
    except Exception as e:
        logger.error(f"Direct upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

# --- PUBLIC TEST OCR ENDPOINT (NO AUTH) ---
@router.post("/public-test-ocr")
async def public_test_ocr(
    file: UploadFile = File(...)
):
    """
    Public endpoint to test OCR functionality.
    Accepts an image file and returns extracted text.
    No authentication required for debugging purposes.
    """
    try:
        # Read image bytes
        image_bytes = await file.read()
        
        # Extract text using OCR service
        ocr_text = await asyncio.to_thread(extract_text_from_image_bytes, image_bytes)
        
        # Return result
        return {
            "status": "success",
            "filename": file.filename,
            "content_type": file.content_type,
            "file_size_bytes": len(image_bytes),
            "ocr_text": ocr_text,
            "ocr_text_length": len(ocr_text) if ocr_text else 0,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Public OCR test failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"OCR processing failed: {str(e)}"
        )


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
    pdf_buffer = generate_invoice_pdf(invoice, db, str(current_user.id), lang=lang or "sq")
    filename = f"Invoice_{invoice.invoice_number}.pdf"
    headers = {'Content-Disposition': f'inline; filename="{filename}"'}
    return StreamingResponse(pdf_buffer, media_type="application/pdf", headers=headers)

@router.post("/invoices/{invoice_id}/archive", response_model=ArchiveItemOut)
async def archive_invoice(invoice_id: str, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db), case_id: Optional[str] = Query(None), lang: Optional[str] = Query("sq")):
    finance_service = FinanceService(db)
    archive_service = ArchiveService(db)
    
    invoice = finance_service.get_invoice(str(current_user.id), invoice_id)
    pdf_buffer = generate_invoice_pdf(invoice, db, str(current_user.id), lang=lang or "sq")
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
    pdf_buffer = create_pdf_from_text(text=content, document_title=title)
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
    file: UploadFile = File(...),
    db: Database = Depends(get_db),
    case_id: Optional[str] = Body(None, embed=False)
):
    """
    SINGLE-STEP MOBILE SCANNING: Analyzes receipt AND creates expense automatically.
    Mobile app calls this endpoint, gets complete expense created with OCR data.
    """
    try:
        logger.info(f"🔍 Mobile scanning started: {file.filename}")
        
        # 1. Read image
        image_bytes = await file.read()
        logger.info(f"📊 Image size: {len(image_bytes)} bytes")
        
        # 2. Extract text with OCR
        ocr_text = await asyncio.to_thread(extract_text_from_image_bytes, image_bytes)
        logger.info(f"📝 OCR extracted: {len(ocr_text or '')} chars")
        
        # 3. Get structured data from LLM (or use defaults)
        if not ocr_text or len(ocr_text) < 5:
            logger.warning("⚠️ OCR text too short, using default data")
            structured_data = {
                "description": f"Receipt {datetime.utcnow().strftime('%Y-%m-%d')}",
                "amount": 0.0,
                "category": "OTHER",
                "date": datetime.utcnow().isoformat()
            }
        else:
            logger.info("🤖 Sending to LLM for structured extraction...")
            structured_data = await asyncio.to_thread(extract_expense_details_from_text, ocr_text)
            logger.info(f"✅ LLM returned: {structured_data}")
        
        # 4. Create expense with the data
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
        
        # 5. Save expense to database
        service = FinanceService(db)
        expense = service.create_expense(str(current_user.id), expense_data)
        logger.info(f"✅ Expense created: {expense.id}")
        
        # 6. Upload receipt to the expense
        # Reset file pointer and upload
        await file.seek(0)
        storage_key = service.upload_expense_receipt(str(current_user.id), str(expense.id), file)
        logger.info(f"✅ Receipt uploaded: {storage_key}")
        
        # 7. Return the COMPLETE expense (not just OCR data)
        return JSONResponse(
            status_code=201,
            content={
                "status": "success",
                "message": "Expense created from receipt scan",
                "expense": ExpenseOut(**expense.dict()).dict(),
                "ocr_data": structured_data
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Mobile scanning failed: {e}")
        # Return error but with 200 so frontend doesn't crash
        return JSONResponse(
            content={
                "status": "error",
                "message": f"Failed to process receipt: {str(e)}",
                "expense": None,
                "ocr_data": {"category": "", "amount": 0, "date": "", "description": ""}
            }
        )

# --- PHOENIX VERIFIED FIX: SINGLE-STEP MOBILE UPLOAD → EXPENSE PIPELINE ---

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
async def public_general_mobile_upload(
    token: str, 
    file: UploadFile = File(...), 
    db: Database = Depends(get_db),
    case_id: Optional[str] = Body(None, embed=True)
):
    """
    SINGLE-STEP MOBILE UPLOAD: Uploads file AND creates expense automatically.
    Optional case_id parameter to associate expense with a case.
    """
    data_str = cast(Optional[str], redis_client.get(f"mobile_upload:{token}"))
    if not data_str:
        raise HTTPException(status_code=404, detail="Session expired")
    
    data = json.loads(data_str)
    if data.get("status") == "complete":
         return {
             "status": "already_completed", 
             "expense_id": data.get("expense_id"),
             "message": "Expense already created from this upload"
         }

    try:
        # 1. Read file content
        file_content = await file.read()
        filename = file.filename or "receipt.jpg"
        content_type = file.content_type or "image/jpeg"
        data["filename"] = filename
        
        # 2. Upload directly to B2 using bytes (NO UploadFile wrapper issues)
        folder = f"temp_uploads/{data['user_id']}/temp_{token}"
        temp_storage_key = upload_bytes_to_b2(
            content=file_content,
            folder=folder,
            filename=filename,
            content_type=content_type
        )
        data["temp_storage_key"] = temp_storage_key
        
        # 3. Analyze with OCR/LLM
        ocr_text = await asyncio.to_thread(extract_text_from_image_bytes, file_content)
        if not ocr_text or len(ocr_text) < 5:
            logger.warning(f"OCR extracted insufficient text: {len(ocr_text or '')} chars")
            structured_data = {
                "description": f"Receipt from {datetime.utcnow().strftime('%Y-%m-%d')}", 
                "amount": 0.0, 
                "category": "OTHER"
            }
        else:
            structured_data = await asyncio.to_thread(extract_expense_details_from_text, ocr_text)
        
        # 4. Create expense
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
        
        service = FinanceService(db)
        expense = service.create_expense(data["user_id"], expense_data)
        
        # 5. Copy file to permanent storage (uses existing copy_s3_object)
        dest_folder = f"expenses/{data['user_id']}"
        permanent_storage_key = copy_s3_object(temp_storage_key, dest_folder)
        
        # Update expense with receipt URL
        service.db.expenses.update_one(
            {"_id": ObjectId(expense.id)},
            {"$set": {"receipt_url": permanent_storage_key}}
        )
        
        # 6. Clean up temp file
        try:
            delete_file(temp_storage_key)
        except Exception as cleanup_error:
            logger.warning(f"Failed to delete temp file {temp_storage_key}: {cleanup_error}")
        
        # 7. Update session as complete
        data["status"] = "complete"
        data["expense_id"] = str(expense.id)
        data["permanent_storage_key"] = permanent_storage_key
        redis_client.setex(f"mobile_upload:{token}", 300, json.dumps(data))  # Keep for 5 more mins
        
        return {
            "status": "success", 
            "expense_id": str(expense.id),
            "message": "Expense created successfully",
            "expense": ExpenseOut(**expense.dict()).dict()
        }
        
    except Exception as e:
        logger.error(f"Failed to process mobile upload: {e}")
        # Update session with error
        data["status"] = "error"
        data["error"] = str(e)
        redis_client.setex(f"mobile_upload:{token}", 300, json.dumps(data))
        raise HTTPException(status_code=500, detail=f"Failed to process upload: {str(e)}")

@router.get("/mobile-upload-file/{token}")
def get_general_mobile_session_file(token: str, current_user: Annotated[UserInDB, Depends(get_current_user)]):
    data_str = cast(Optional[str], redis_client.get(f"mobile_upload:{token}"))
    if not data_str:
        raise HTTPException(status_code=404, detail="Session expired")
    
    data = json.loads(data_str)
    if data.get("status") != "complete" or not data.get("permanent_storage_key"):
        raise HTTPException(status_code=400, detail="Upload not complete or no file available")
        
    storage_key = data["permanent_storage_key"]
    
    file_stream = get_file_stream(storage_key)
    if not file_stream:
        raise HTTPException(status_code=404, detail="File not found in storage")
    
    return StreamingResponse(
        file_stream, 
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'inline; filename="{data.get("filename", "receipt.jpg")}"'}
    )