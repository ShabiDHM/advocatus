# FILE: backend/app/api/endpoints/finance.py
# PHOENIX PROTOCOL - FINANCE V6.0 (UNIFIED ANALYTICS)
# 1. UPDATE: get_analytics_dashboard now merges data from 'invoices' AND 'transactions'.
# 2. RESULT: Charts will now show manual sales even without POS imports.

import pandas as pd
import io
import uuid
import json
import redis
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from fastapi.responses import StreamingResponse, JSONResponse
from typing import List, Annotated, Optional, Any, Dict, Union, cast
from pymongo.database import Database
from bson import ObjectId

from app.models.user import UserInDB
from app.models.common import PyObjectId
from app.models.finance import (
    InvoiceCreate, InvoiceOut, InvoiceUpdate, 
    ExpenseCreate, ExpenseOut, ExpenseUpdate,
    ImportBatchOut, ColumnMappingCreate,
    TransactionInDB, ImportBatchInDB, ColumnMappingRuleInDB,
    TransactionOut, AnalyticsDashboardData, SalesTrendPoint, TopProductItem
)
from app.models.archive import ArchiveItemOut 
from app.services.finance_service import FinanceService
from app.services.archive_service import ArchiveService
from app.services import report_service
from app.services.parsing_service import PosParsingService
from app.api.endpoints.dependencies import get_current_user, get_db, get_async_db, get_current_active_user, get_sync_redis

router = APIRouter(tags=["Finance"])

REQUIRED_FIELDS = ["product", "total"]

# --- ANALYTICS & HISTORY ENDPOINTS ---

@router.get("/import-batches", response_model=List[ImportBatchOut])
async def get_import_history(
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    db: Any = Depends(get_async_db)
):
    cursor = db["import_batches"].find({"user_id": ObjectId(current_user.id)}).sort("created_at", -1).limit(50)
    batches = await cursor.to_list(length=50)
    return batches

@router.get("/import-batches/{batch_id}/transactions", response_model=List[TransactionOut])
async def get_batch_transactions(
    batch_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    db: Any = Depends(get_async_db)
):
    try: b_oid = ObjectId(batch_id)
    except: raise HTTPException(status_code=400, detail="Invalid Batch ID")

    batch = await db["import_batches"].find_one({"_id": b_oid, "user_id": ObjectId(current_user.id)})
    if not batch: raise HTTPException(status_code=404, detail="Batch not found")

    cursor = db["transactions"].find({"batch_id": b_oid}).limit(1000)
    transactions = await cursor.to_list(length=1000)
    return transactions

@router.get("/analytics/dashboard", response_model=AnalyticsDashboardData)
async def get_analytics_dashboard(
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    db: Any = Depends(get_async_db),
    days: int = 30
):
    """
    Calculates unified sales analytics from BOTH manual Invoices and imported POS transactions.
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    user_oid = ObjectId(current_user.id)

    # --- 1. DATA FETCHING ---
    
    # A. POS Transactions Data
    pos_pipeline = [
        {"$match": {"user_id": user_oid, "date_time": {"$gte": start_date, "$lte": end_date}}},
        {"$project": {"date": "$date_time", "amount": "$total_amount", "product": "$product_name", "quantity": "$quantity"}}
    ]
    pos_data = await db["transactions"].aggregate(pos_pipeline).to_list(length=10000)

    # B. Manual Invoices Data (Only Valid/Paid ones)
    # We assume 'DRAFT' and 'CANCELLED' should not count towards analytics yet, or maybe just CANCELLED.
    # Let's include everything except CANCELLED to be generous with the dashboard.
    inv_pipeline = [
        {"$match": {
            "user_id": user_oid, 
            "issue_date": {"$gte": start_date, "$lte": end_date},
            "status": {"$ne": "CANCELLED"}
        }},
        {"$project": {"date": "$issue_date", "items": 1}}
    ]
    inv_data = await db["invoices"].aggregate(inv_pipeline).to_list(length=5000)

    # --- 2. DATA PROCESSING & MERGING ---
    
    total_rev = 0.0
    total_count = len(pos_data) + len(inv_data)
    
    # Dictionaries for aggregation
    trend_map = {} # "YYYY-MM-DD" -> amount
    product_map = {} # "Product Name" -> {quantity, revenue}

    # Process POS Data
    for t in pos_data:
        amt = float(t.get("amount", 0))
        total_rev += amt
        
        # Trend
        date_key = t["date"].strftime("%Y-%m-%d")
        trend_map[date_key] = trend_map.get(date_key, 0.0) + amt
        
        # Products
        prod = t.get("product", "Unknown")
        if prod not in product_map: product_map[prod] = {"qty": 0, "rev": 0.0}
        product_map[prod]["qty"] += float(t.get("quantity", 0))
        product_map[prod]["rev"] += amt

    # Process Manual Invoices (Unwind items)
    for inv in inv_data:
        # Date for trend
        date_key = inv["date"].strftime("%Y-%m-%d")
        
        for item in inv.get("items", []):
            # Handle item as dict (if raw) or object
            # Aggregation returns dicts usually
            i_qty = float(item.get("quantity", 1))
            i_price = float(item.get("unit_price", 0))
            i_total = i_qty * i_price
            i_name = item.get("description", "Shërbim")
            
            total_rev += i_total
            trend_map[date_key] = trend_map.get(date_key, 0.0) + i_total
            
            if i_name not in product_map: product_map[i_name] = {"qty": 0, "rev": 0.0}
            product_map[i_name]["qty"] += i_qty
            product_map[i_name]["rev"] += i_total

    # --- 3. FORMATTING RESULTS ---

    # Sort Trend by Date
    sales_trend = [
        SalesTrendPoint(date=k, amount=round(v, 2)) 
        for k, v in sorted(trend_map.items())
    ]

    # Sort Products by Revenue (Top 5)
    sorted_products = sorted(
        product_map.items(), 
        key=lambda item: item[1]['rev'], 
        reverse=True
    )[:5]
    
    top_products = [
        TopProductItem(
            product_name=k, 
            total_quantity=v['qty'], 
            total_revenue=round(v['rev'], 2)
        ) 
        for k, v in sorted_products
    ]

    return AnalyticsDashboardData(
        total_revenue_period=round(total_rev, 2),
        total_transactions_period=total_count,
        sales_trend=sales_trend,
        top_products=top_products
    )

# --- POS IMPORT ENDPOINTS ---
@router.post("/import-pos", status_code=status.HTTP_202_ACCEPTED)
async def initiate_pos_import(
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    db: Any = Depends(get_async_db),
    redis_client: redis.Redis = Depends(get_sync_redis),
    file: UploadFile = File(...)
):
    if not file.filename or not (file.filename.lower().endswith(('.csv', '.xlsx', '.xls'))):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file format.")
    
    content = await file.read()
    
    try:
        headers = PosParsingService.get_headers_from_file(content, file.filename)
        signature = ",".join(sorted(headers))
        saved_mapping_rule = await db["column_mappings"].find_one({"user_id": current_user.id, "source_signature": signature})
        
        mapping_to_use = None
        if saved_mapping_rule:
            mapping_to_use = saved_mapping_rule.get("mapping")
        else:
            keyword_mapping = PosParsingService.map_columns_with_keywords(headers)
            if all(field in keyword_mapping.values() for field in REQUIRED_FIELDS):
                mapping_to_use = keyword_mapping

        if mapping_to_use:
            df = pd.read_csv(io.BytesIO(content)) if file.filename.lower().endswith('.csv') else pd.read_excel(io.BytesIO(content))
            transactions_data, total_volume = PosParsingService.process_dataframe(df, mapping_to_use)

            if not transactions_data: raise ValueError("No valid transaction rows found in the file.")

            batch_record = ImportBatchInDB(user_id=current_user.id, filename=file.filename, status="PROCESSED", row_count=len(transactions_data), total_volume=total_volume)
            new_batch = await db["import_batches"].insert_one(batch_record.model_dump(by_alias=True))
            batch_id = new_batch.inserted_id

            transactions_to_insert = [TransactionInDB(**tx, user_id=current_user.id, batch_id=batch_id).model_dump(by_alias=True) for tx in transactions_data]
            if transactions_to_insert:
                await db["transactions"].insert_many(transactions_to_insert)

            response_data = {
                "_id": batch_id,
                "user_id": current_user.id,
                "filename": file.filename,
                "status": "PROCESSED",
                "row_count": len(transactions_data),
                "total_volume": total_volume,
                "created_at": datetime.utcnow()
            }
            return JSONResponse(
                content=json.loads(ImportBatchOut(**response_data).model_dump_json(by_alias=True)),
                status_code=status.HTTP_201_CREATED
            )

        upload_id = uuid.uuid4().hex
        cached_data = {"content": content.hex(), "filename": file.filename, "headers": headers}
        redis_client.set(f"import_cache:{upload_id}", json.dumps(cached_data).encode('utf-8'), ex=3600)
        return {"mapping_required": True, "upload_id": upload_id, "detected_headers": headers, "system_fields": list(PosParsingService.ALL_FIELDS.keys())}
        
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

@router.post("/import-pos/{upload_id}/map", response_model=ImportBatchOut, status_code=status.HTTP_201_CREATED)
async def finalize_pos_import_with_mapping(
    upload_id: str,
    mapping_data: ColumnMappingCreate,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    db: Any = Depends(get_async_db),
    redis_client: redis.Redis = Depends(get_sync_redis)
):
    cached_data_raw = cast(Union[str, bytes, None], redis_client.get(f"import_cache:{upload_id}"))
    if not cached_data_raw: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import session has expired or is invalid.")
    
    cached_data = json.loads(cached_data_raw)
    content, filename, headers = bytes.fromhex(cached_data["content"]), cached_data["filename"], cached_data["headers"]

    if not all(field in mapping_data.mappings.values() for field in REQUIRED_FIELDS):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Mapping is incomplete. 'Product' and 'Total' fields are required.")

    df = pd.read_csv(io.BytesIO(content)) if filename.lower().endswith('.csv') else pd.read_excel(io.BytesIO(content))
    transactions_data, total_volume = PosParsingService.process_dataframe(df, mapping_data.mappings)
    
    if not transactions_data: raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No valid transaction rows found in the file with the provided mapping.")

    batch_record = ImportBatchInDB(user_id=current_user.id, filename=filename, status="PROCESSED", row_count=len(transactions_data), total_volume=total_volume)
    new_batch = await db["import_batches"].insert_one(batch_record.model_dump(by_alias=True))
    batch_id = new_batch.inserted_id

    transactions_to_insert = [TransactionInDB(**tx, user_id=current_user.id, batch_id=batch_id).model_dump(by_alias=True) for tx in transactions_data]
    if transactions_to_insert:
        await db["transactions"].insert_many(transactions_to_insert)

    signature = ",".join(sorted(headers))
    rule = ColumnMappingRuleInDB(user_id=current_user.id, source_signature=signature, mapping=mapping_data.mappings)
    await db["column_mappings"].update_one({"user_id": current_user.id, "source_signature": signature}, {"$set": rule.model_dump(by_alias=False)}, upsert=True)

    return ImportBatchOut(
        _id=batch_id,
        user_id=current_user.id,
        filename=filename, 
        status="PROCESSED", 
        row_count=len(transactions_data), 
        total_volume=total_volume, 
        created_at=datetime.utcnow()
    )

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
def update_invoice(
    invoice_id: str, 
    invoice_update: InvoiceUpdate, 
    current_user: Annotated[UserInDB, Depends(get_current_user)], 
    db: Database = Depends(get_db)
):
    return FinanceService(db).update_invoice(str(current_user.id), invoice_id, invoice_update)

@router.put("/invoices/{invoice_id}/status", response_model=InvoiceOut)
def update_invoice_status(invoice_id: str, status_update: InvoiceUpdate, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    if not status_update.status: raise HTTPException(status_code=400, detail="Status is required")
    return FinanceService(db).update_invoice_status(str(current_user.id), invoice_id, status_update.status)

@router.delete("/invoices/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_invoice(invoice_id: str, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    FinanceService(db).delete_invoice(str(current_user.id), invoice_id)

@router.get("/invoices/{invoice_id}/pdf")
def download_invoice_pdf(
    invoice_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db),
    lang: Optional[str] = Query("sq")
):
    service = FinanceService(db)
    invoice = service.get_invoice(str(current_user.id), invoice_id)
    pdf_buffer = report_service.generate_invoice_pdf(invoice, db, str(current_user.id), lang=lang or "sq")
    
    filename = f"Invoice_{invoice.invoice_number}.pdf"
    headers = {'Content-Disposition': f'inline; filename="{filename}"'}
    return StreamingResponse(pdf_buffer, media_type="application/pdf", headers=headers)

@router.post("/invoices/{invoice_id}/archive", response_model=ArchiveItemOut)
async def archive_invoice(
    invoice_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db),
    case_id: Optional[str] = Query(None),
    lang: Optional[str] = Query("sq")
):
    finance_service = FinanceService(db)
    archive_service = ArchiveService(db)
    
    invoice = finance_service.get_invoice(str(current_user.id), invoice_id)
    pdf_buffer = report_service.generate_invoice_pdf(invoice, db, str(current_user.id), lang=lang or "sq")
    pdf_content = pdf_buffer.getvalue()
    
    filename = f"Invoice_{invoice.invoice_number}.pdf"
    title = f"Fatura #{invoice.invoice_number} - {invoice.client_name}"
    
    archived_item = await archive_service.save_generated_file(
        user_id=str(current_user.id),
        filename=filename,
        content=pdf_content,
        category="INVOICE",
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
def update_expense(
    expense_id: str, 
    expense_update: ExpenseUpdate, 
    current_user: Annotated[UserInDB, Depends(get_current_user)], 
    db: Database = Depends(get_db)
):
    return FinanceService(db).update_expense(str(current_user.id), expense_id, expense_update)

@router.delete("/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(expense_id: str, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    FinanceService(db).delete_expense(str(current_user.id), expense_id)

@router.put("/expenses/{expense_id}/receipt", status_code=status.HTTP_200_OK)
def upload_expense_receipt(
    expense_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    file: UploadFile = File(...),
    db: Database = Depends(get_db)
):
    service = FinanceService(db)
    storage_key = service.upload_expense_receipt(str(current_user.id), expense_id, file)
    return {"status": "success", "storage_key": storage_key}