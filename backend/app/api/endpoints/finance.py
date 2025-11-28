# FILE: backend/app/api/endpoints/finance.py
# PHOENIX PROTOCOL - FINANCE API
# 1. CRUD: Create, List, and Update Invoices.
# 2. PDF GENERATION: Endpoint to download the Branded Invoice.
# 3. SECURITY: Scoped strictly to the current user.

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from typing import List, Annotated
from pymongo.database import Database

from ...models.user import UserInDB
from ...models.finance import InvoiceCreate, InvoiceOut, InvoiceUpdate
from ...services.finance_service import FinanceService
from ...services.report_service import generate_invoice_pdf
from .dependencies import get_current_user, get_db

router = APIRouter(tags=["Finance"])

@router.get("/invoices", response_model=List[InvoiceOut])
def get_invoices(
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    """List all invoices for the current user."""
    service = FinanceService(db)
    return service.get_invoices(str(current_user.id))

@router.post("/invoices", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED)
def create_invoice(
    invoice_in: InvoiceCreate,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    """Create a new invoice (Auto-calculates totals)."""
    service = FinanceService(db)
    return service.create_invoice(str(current_user.id), invoice_in)

@router.get("/invoices/{invoice_id}", response_model=InvoiceOut)
def get_invoice_details(
    invoice_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    """Get single invoice details."""
    service = FinanceService(db)
    return service.get_invoice(str(current_user.id), invoice_id)

@router.put("/invoices/{invoice_id}/status", response_model=InvoiceOut)
def update_invoice_status(
    invoice_id: str,
    status_update: InvoiceUpdate,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    """Update status (e.g. mark as PAID)."""
    service = FinanceService(db)
    if not status_update.status:
        raise HTTPException(status_code=400, detail="Status is required")
    return service.update_invoice_status(str(current_user.id), invoice_id, status_update.status)

@router.get("/invoices/{invoice_id}/pdf")
def download_invoice_pdf(
    invoice_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    """Generates and streams the Branded PDF Invoice."""
    service = FinanceService(db)
    invoice = service.get_invoice(str(current_user.id), invoice_id)
    
    # Pass username to fetch the correct branding/logo
    pdf_buffer = generate_invoice_pdf(invoice, db, current_user.username)
    
    filename = f"Invoice_{invoice.invoice_number}.pdf"
    headers = {'Content-Disposition': f'inline; filename="{filename}"'}
    return StreamingResponse(pdf_buffer, media_type="application/pdf", headers=headers)