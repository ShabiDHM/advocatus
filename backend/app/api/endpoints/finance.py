# FILE: backend/app/api/endpoints/finance.py
# PHOENIX PROTOCOL - FINANCE ROUTER V53.2 (ONE-TIME PASS REMOVED)
# V53.2: Hequr `DEFAULT_UNLOCK_PRICE_EUR` (dead constant — nuk përdorej
#        askund pas heqjes së One-Time Pass).
# V53.1: PARAM ORDER — Non-default arguments tani vijnë PARA atyre me default.
# V53.0: FULL RESTORATION (endpoints /finance/* u rikthyen).

import os
import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import List, Annotated, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from pymongo.database import Database
from bson import ObjectId

from app.models.user import UserInDB
from app.models.finance import (
    InvoiceCreate, InvoiceOut, InvoiceUpdate,
    ExpenseCreate, ExpenseOut, ExpenseUpdate,
    AnalyticsDashboardData, SalesTrendPoint, TopProductItem,
    CaseFinancialSummary,
)
from app.models.archive import ArchiveItemOut
from app.services.finance_service import FinanceService
from app.services.report_service import generate_invoice_pdf
from app.services.ocr_service import extract_text_from_image_bytes
from app.services.llm_service import extract_expense_details_from_text
from app.api.endpoints.dependencies import get_current_user, get_db

router = APIRouter(tags=["Finance"])
logger = logging.getLogger(__name__)

BANK_NAME = os.getenv("COMPANY_BANK_NAME", "Raiffeisen Bank Kosova")
BANK_ACCOUNT_HOLDER = os.getenv("COMPANY_ACCOUNT_HOLDER", "Juristi AI / Advocatus SH.P.K.")
BANK_IBAN = os.getenv("RAIFFEISEN_IBAN", "XK051501001000000000")
BANK_SWIFT = os.getenv("RAIFFEISEN_SWIFT", "RBKOXKPR")

ADMIN_ROLES = {"ADMIN", "SUPERADMIN", "STAFF"}

MAX_RECEIPT_SIZE_BYTES = 20 * 1024 * 1024


def _get_service(db: Database) -> FinanceService:
    return FinanceService(db)


# =========================================================================
# 📄 INVOICES
# =========================================================================

@router.get("/invoices", response_model=List[InvoiceOut])
async def list_invoices(
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db),
):
    service = _get_service(db)
    return await asyncio.to_thread(service.get_invoices, str(current_user.id))


@router.post("/invoices", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED)
async def create_invoice_endpoint(
    data: InvoiceCreate,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db),
):
    service = _get_service(db)
    return await asyncio.to_thread(service.create_invoice, str(current_user.id), data)


@router.get("/invoices/{invoice_id}", response_model=InvoiceOut)
async def get_invoice_endpoint(
    invoice_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db),
):
    service = _get_service(db)
    return await asyncio.to_thread(service.get_invoice, str(current_user.id), invoice_id)


@router.put("/invoices/{invoice_id}", response_model=InvoiceOut)
async def update_invoice_endpoint(
    invoice_id: str,
    data: InvoiceUpdate,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db),
):
    service = _get_service(db)
    return await asyncio.to_thread(service.update_invoice, str(current_user.id), invoice_id, data)


@router.put("/invoices/{invoice_id}/status", response_model=InvoiceOut)
async def update_invoice_status_endpoint(
    invoice_id: str,
    body: Dict[str, Any],
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db),
):
    status_val = (body or {}).get("status")
    if not status_val:
        raise HTTPException(status_code=400, detail="Mungon fusha 'status'.")
    service = _get_service(db)
    return await asyncio.to_thread(
        service.update_invoice_status, str(current_user.id), invoice_id, str(status_val)
    )


@router.delete("/invoices/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice_endpoint(
    invoice_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db),
):
    service = _get_service(db)
    await asyncio.to_thread(service.delete_invoice, str(current_user.id), invoice_id)
    return None


@router.get("/invoices/{invoice_id}/pdf")
async def download_invoice_pdf_endpoint(
    invoice_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db),
    lang: str = Query("sq", pattern="^(sq|en)$"),
):
    service = _get_service(db)
    invoice = await asyncio.to_thread(service.get_invoice, str(current_user.id), invoice_id)

    try:
        pdf_buffer = await asyncio.to_thread(generate_invoice_pdf, invoice, current_user, lang)
    except Exception as e:
        logger.error(f"Invoice PDF generation failed for {invoice_id}: {e}")
        raise HTTPException(status_code=500, detail="Dështoi gjenerimi i PDF-së.")

    filename = f"Fatura_{getattr(invoice, 'invoice_number', None) or invoice_id}.pdf"
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.post("/invoices/{invoice_id}/archive", response_model=ArchiveItemOut)
async def archive_invoice_endpoint(
    invoice_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db),
    case_id: Optional[str] = Query(None),
):
    service = _get_service(db)
    invoice = await asyncio.to_thread(service.get_invoice, str(current_user.id), invoice_id)

    now = datetime.now(timezone.utc)
    uid = str(current_user.id)
    archive_doc: Dict[str, Any] = {
        "title": f"Fatura {getattr(invoice, 'invoice_number', None) or invoice_id}",
        "item_type": "FILE",
        "parent_id": None,
        "file_type": "PDF",
        "category": "INVOICE",
        "storage_key": None,
        "file_size": 0,
        "description": f"Klienti: {getattr(invoice, 'client_name', '—')} — Totali: {getattr(invoice, 'total_amount', 0)}€",
        "case_id": ObjectId(case_id) if (case_id and ObjectId.is_valid(case_id)) else None,
        "original_doc_id": ObjectId(invoice_id) if ObjectId.is_valid(invoice_id) else None,
        "is_shared": False,
        "user_id": ObjectId(uid) if ObjectId.is_valid(uid) else uid,
        "created_at": now,
    }
    result = await asyncio.to_thread(db.archives.insert_one, archive_doc)
    archive_doc["id"] = result.inserted_id
    return ArchiveItemOut.model_validate(archive_doc)


# =========================================================================
# 💸 EXPENSES
# =========================================================================

@router.get("/expenses", response_model=List[ExpenseOut])
async def list_expenses(
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db),
):
    service = _get_service(db)
    return await asyncio.to_thread(service.get_expenses, str(current_user.id))


@router.post("/expenses/analyze-receipt")
async def analyze_receipt_endpoint(
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    file: UploadFile = File(...),
):
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Skedari është bosh.")
    if len(content) > MAX_RECEIPT_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="Skedari është shumë i madh (max 20 MB).")

    try:
        text = await asyncio.to_thread(extract_text_from_image_bytes, content)
    except Exception as e:
        logger.warning(f"OCR failed for receipt: {e}")
        text = ""

    if not text or not text.strip():
        return {
            "category": "Të tjera",
            "amount": 0.0,
            "date": "",
            "description": "Nuk u lexua tekst nga fatura.",
        }

    try:
        details = await asyncio.to_thread(extract_expense_details_from_text, text)
    except Exception as e:
        logger.warning(f"LLM parse failed for receipt: {e}")
        details = {}

    if not isinstance(details, dict):
        details = {}

    return {
        "category": details.get("category", "Të tjera"),
        "amount": float(details.get("amount", 0) or 0),
        "date": details.get("date", ""),
        "description": details.get("description", (text or "")[:200]),
    }


@router.post("/expenses", response_model=ExpenseOut, status_code=status.HTTP_201_CREATED)
async def create_expense_endpoint(
    data: ExpenseCreate,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db),
):
    service = _get_service(db)
    return await asyncio.to_thread(service.create_expense, str(current_user.id), data)


@router.get("/expenses/{expense_id}", response_model=ExpenseOut)
async def get_expense_endpoint(
    expense_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db),
):
    service = _get_service(db)
    return await asyncio.to_thread(service.get_expense, str(current_user.id), expense_id)


@router.put("/expenses/{expense_id}", response_model=ExpenseOut)
async def update_expense_endpoint(
    expense_id: str,
    data: ExpenseUpdate,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db),
):
    service = _get_service(db)
    return await asyncio.to_thread(service.update_expense, str(current_user.id), expense_id, data)


@router.delete("/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expense_endpoint(
    expense_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db),
):
    service = _get_service(db)
    await asyncio.to_thread(service.delete_expense, str(current_user.id), expense_id)
    return None


@router.put("/expenses/{expense_id}/receipt")
async def upload_expense_receipt_endpoint(
    expense_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db),
    file: UploadFile = File(...),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Skedari nuk ka emër.")
    service = _get_service(db)
    storage_key = await asyncio.to_thread(
        service.upload_expense_receipt, str(current_user.id), expense_id, file
    )
    return {"status": "success", "storage_key": storage_key}


@router.get("/expenses/{expense_id}/receipt")
async def download_expense_receipt_endpoint(
    expense_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db),
):
    service = _get_service(db)
    try:
        stream = await asyncio.to_thread(
            service.get_expense_receipt_stream, str(current_user.id), expense_id
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Receipt stream failed for {expense_id}: {e}")
        raise HTTPException(status_code=500, detail="Dështoi leximi i faturës.")

    filename = f"receipt-{expense_id}.pdf"
    return StreamingResponse(
        stream,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# =========================================================================
# 📊 ANALYTICS DASHBOARD
# =========================================================================

def _build_analytics(db: Database, user_id: str, days: int) -> AnalyticsDashboardData:
    uid = ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    try:
        invoices = list(db.invoices.find({
            "user_id": uid,
            "$or": [
                {"created_at": {"$gte": cutoff}},
                {"issue_date": {"$gte": cutoff}},
            ],
        }))
    except Exception as e:
        logger.warning(f"Analytics invoices query failed: {e}")
        invoices = []

    total_revenue = 0.0
    trend_map: Dict[str, float] = defaultdict(float)
    product_map: Dict[str, Dict[str, float]] = defaultdict(lambda: {"qty": 0.0, "rev": 0.0})

    for inv in invoices:
        try:
            amt = float(inv.get("total_amount", 0) or 0)
        except (ValueError, TypeError):
            amt = 0.0
        total_revenue += amt

        d = inv.get("issue_date") or inv.get("created_at")
        if isinstance(d, datetime):
            key = d.strftime("%Y-%m-%d")
            trend_map[key] += amt

        for item in (inv.get("items") or []):
            desc = (item.get("description") or "Pa emër").strip()
            try:
                qty = float(item.get("quantity", 0) or 0)
                rev = float(item.get("total", 0) or 0)
            except (ValueError, TypeError):
                continue
            product_map[desc]["qty"] += qty
            product_map[desc]["rev"] += rev

    sales_trend = [
        SalesTrendPoint(date=k, amount=round(v, 2))
        for k, v in sorted(trend_map.items())
    ]

    top_products = [
        TopProductItem(
            product_name=k,
            total_quantity=round(v["qty"], 2),
            total_revenue=round(v["rev"], 2),
        )
        for k, v in sorted(product_map.items(), key=lambda x: -x[1]["rev"])[:5]
    ]

    return AnalyticsDashboardData(
        total_revenue_period=round(total_revenue, 2),
        total_transactions_period=len(invoices),
        sales_trend=sales_trend,
        top_products=top_products,
    )


@router.get("/analytics/dashboard", response_model=AnalyticsDashboardData)
async def get_analytics_dashboard_endpoint(
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
):
    return await asyncio.to_thread(_build_analytics, db, str(current_user.id), days)


# =========================================================================
# 🏛️ CASE FINANCIAL SUMMARY
# =========================================================================

def _build_case_summaries(db: Database, user_id: str) -> List[CaseFinancialSummary]:
    uid = ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id

    inv_pipeline = [
        {"$match": {"user_id": uid, "related_case_id": {"$nin": [None, "", "None"]}}},
        {"$group": {"_id": "$related_case_id", "total": {"$sum": "$total_amount"}}},
    ]
    exp_pipeline = [
        {"$match": {"user_id": uid, "related_case_id": {"$nin": [None, "", "None"]}}},
        {"$group": {"_id": "$related_case_id", "total": {"$sum": "$amount"}}},
    ]

    try:
        inv_map = {str(r["_id"]): float(r.get("total", 0) or 0) for r in db.invoices.aggregate(inv_pipeline)}
    except Exception as e:
        logger.warning(f"Case summary invoices agg failed: {e}")
        inv_map = {}
    try:
        exp_map = {str(r["_id"]): float(r.get("total", 0) or 0) for r in db.expenses.aggregate(exp_pipeline)}
    except Exception as e:
        logger.warning(f"Case summary expenses agg failed: {e}")
        exp_map = {}

    all_case_ids = set(inv_map.keys()) | set(exp_map.keys())

    summaries: List[CaseFinancialSummary] = []
    for cid in all_case_ids:
        case_oid = ObjectId(cid) if ObjectId.is_valid(cid) else cid
        try:
            case_doc = db.cases.find_one({"_id": case_oid})
        except Exception:
            case_doc = None
        if not case_doc:
            continue

        total_billed = inv_map.get(cid, 0.0)
        total_exp = exp_map.get(cid, 0.0)

        summaries.append(CaseFinancialSummary(
            case_id=cid,
            case_title=case_doc.get("title") or case_doc.get("case_name") or "Lëndë pa titull",
            case_number=case_doc.get("case_number") or "—",
            total_billed=round(total_billed, 2),
            total_expenses=round(total_exp, 2),
            net_balance=round(total_billed - total_exp, 2),
        ))

    return summaries


@router.get("/case-summary", response_model=List[CaseFinancialSummary])
async def get_case_summaries_endpoint(
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db),
):
    return await asyncio.to_thread(_build_case_summaries, db, str(current_user.id))