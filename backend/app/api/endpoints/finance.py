# FILE: backend/app/api/endpoints/finance.py
# PHOENIX PROTOCOL - FINANCE API V2 (EXPENSE ENDPOINTS)
# 1. ADDED: Endpoints for creating, listing, and deleting expenses.
# 2. STATUS: Fully integrated with FinanceService.

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from typing import List, Annotated, Optional
from pymongo.database import Database

from ...models.user import UserInDB
# PHOENIX NEW: Added ExpenseCreate and ExpenseOut
from ...models.finance import InvoiceCreate, InvoiceOut, InvoiceUpdate, ExpenseCreate, ExpenseOut
from ...models.archive import ArchiveItemOut 
from ...services.finance_service import FinanceService
from ...services.archive_service import ArchiveService
from ...services.report_service import generate_invoice_pdf
from .dependencies import get_current_user, get_db

router = APIRouter(tags=["Finance"])

# --- INVOICES ---
@router.get("/invoices", response_model=List[InvoiceOut])
def get_invoices(
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    service = FinanceService(db)
    return service.get_invoices(str(current_user.id))

@router.post("/invoices", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED)
def create_invoice(
    invoice_in: InvoiceCreate,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    service = FinanceService(db)
    return service.create_invoice(str(current_user.id), invoice_in)

@router.get("/invoices/{invoice_id}", response_model=InvoiceOut)
def get_invoice_details(
    invoice_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    service = FinanceService(db)
    return service.get_invoice(str(current_user.id), invoice_id)

@router.put("/invoices/{invoice_id}/status", response_model=InvoiceOut)
def update_invoice_status(
    invoice_id: str,
    status_update: InvoiceUpdate,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    service = FinanceService(db)
    if not status_update.status:
        raise HTTPException(status_code=400, detail="Status is required")
    return service.update_invoice_status(str(current_user.id), invoice_id, status_update.status)

@router.delete("/invoices/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_invoice(
    invoice_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    service = FinanceService(db)
    service.delete_invoice(str(current_user.id), invoice_id)

@router.get("/invoices/{invoice_id}/pdf")
def download_invoice_pdf(
    invoice_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db),
    lang: Optional[str] = Query("sq", description="Language code (sq, en, sr)")
):
    service = FinanceService(db)
    invoice = service.get_invoice(str(current_user.id), invoice_id)
    # Uses ID for reliable branding lookup
    pdf_buffer = generate_invoice_pdf(invoice, db, str(current_user.id), lang=lang or "sq")
    
    filename = f"Invoice_{invoice.invoice_number}.pdf"
    headers = {'Content-Disposition': f'inline; filename="{filename}"'}
    return StreamingResponse(pdf_buffer, media_type="application/pdf", headers=headers)

@router.post("/invoices/{invoice_id}/archive", response_model=ArchiveItemOut)
async def archive_invoice(
    invoice_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db),
    case_id: Optional[str] = Query(None, description="Optional Case ID to link the invoice"),
    lang: Optional[str] = Query("sq", description="Language for the PDF")
):
    finance_service = FinanceService(db)
    archive_service = ArchiveService(db)
    
    invoice = finance_service.get_invoice(str(current_user.id), invoice_id)
    pdf_buffer = generate_invoice_pdf(invoice, db, str(current_user.id), lang=lang or "sq")
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

# --- EXPENSES (NEW) ---
@router.post("/expenses", response_model=ExpenseOut, status_code=status.HTTP_201_CREATED)
def create_expense(
    expense_in: ExpenseCreate,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    service = FinanceService(db)
    return service.create_expense(str(current_user.id), expense_in)

@router.get("/expenses", response_model=List[ExpenseOut])
def get_expenses(
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    service = FinanceService(db)
    return service.get_expenses(str(current_user.id))

@router.delete("/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(
    expense_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    service = FinanceService(db)
    service.delete_expense(str(current_user.id), expense_id)