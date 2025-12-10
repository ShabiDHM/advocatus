# FILE: backend/app/api/endpoints/finance_wizard.py
# PHOENIX PROTOCOL - FINANCE WIZARD ENDPOINT v2.1 (LOCALIZATION)
# 1. FIX: Translated Audit Messages to Albanian (SQ).
# 2. LOGIC: Maintains YTD calculation and Tax Regime logic.

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from typing import List
from datetime import datetime

# ABSOLUTE IMPORTS
from app.models.user import UserInDB
from app.api.endpoints.auth import get_current_user
from app.services.finance_service import FinanceService
from app.core.db import db_instance
from app.models.finance import WizardState, AuditIssue, TaxCalculation
from app.modules.finance.tax_engine.kosovo_adapter import KosovoTaxAdapter
from app.modules.finance.reporting import generate_monthly_report_pdf

router = APIRouter()
tax_adapter = KosovoTaxAdapter()

# Instantiate Service
def get_finance_service():
    return FinanceService(db_instance)

def _filter_by_month(items: list, month: int, year: int) -> list:
    filtered = []
    for item in items:
        date_val = getattr(item, "issue_date", getattr(item, "date", None))
        if date_val and date_val.month == month and date_val.year == year:
            filtered.append(item)
    return filtered

def _calculate_annual_turnover(invoices: list, current_year: int) -> float:
    """
    Calculates total gross sales from Jan 1st to the end of the current year.
    Used to check the €30,000 threshold.
    """
    total = 0.0
    for inv in invoices:
        # Skip cancelled invoices
        if inv.status == 'CANCELLED': 
            continue
            
        if inv.issue_date.year == current_year:
            total += inv.total_amount
    return total

def _run_audit_rules(invoices: list, expenses: list) -> List[AuditIssue]:
    issues = []
    
    # Rule 1: Missing Receipts (Mungon Fatura)
    for exp in expenses:
        if exp.amount > 10.0 and not exp.receipt_url:
            issues.append(AuditIssue(
                id=f"missing_receipt_{exp.id}",
                severity="WARNING",
                message=f"Shpenzimi '{exp.category}' prej €{exp.amount} nuk ka faturë të bashkangjitur.",
                related_item_id=str(exp.id),
                item_type="EXPENSE"
            ))
    
    # Rule 2: Unbilled Court Fees (Tarifat Gjyqësore të Pafaturuara)
    for exp in expenses:
        cat_lower = exp.category.lower() if exp.category else ""
        if "court" in cat_lower and not exp.related_case_id:
            issues.append(AuditIssue(
                id=f"unlinked_court_fee_{exp.id}",
                severity="CRITICAL",
                message=f"Taksa Gjyqësore prej €{exp.amount} nuk është lidhur me një Rast Klienti (E pafaturuar).",
                related_item_id=str(exp.id),
                item_type="EXPENSE"
            ))

    # Rule 3: Draft Invoices (Fatura në Draft)
    for inv in invoices:
        if inv.status == "DRAFT":
            issues.append(AuditIssue(
                id=f"draft_invoice_{inv.id}",
                severity="WARNING",
                message=f"Fatura #{inv.invoice_number or '???'} është ende në statusin DRAFT (E pa lëshuar).",
                related_item_id=str(inv.id),
                item_type="INVOICE"
            ))
    return issues

def _get_wizard_data(month: int, year: int, user: UserInDB) -> WizardState:
    """
    Shared logic to fetch data, calculate tax, and run audits.
    """
    service = get_finance_service()
    
    # 1. Fetch ALL data for the user
    all_invoices = service.get_invoices(str(user.id))
    all_expenses = service.get_expenses(str(user.id))
    
    # 2. Filter for current month view
    period_invoices = _filter_by_month(all_invoices, month, year)
    period_expenses = _filter_by_month(all_expenses, month, year)

    # 3. Calculate Annual Turnover (YTD)
    annual_turnover = _calculate_annual_turnover(all_invoices, year)

    # 4. Run Tax Logic
    calculation_result = tax_adapter.analyze_month(
        period_invoices, 
        period_expenses, 
        month, 
        year, 
        annual_turnover
    )
    
    tax_calc = TaxCalculation(**calculation_result)

    # 5. Run Audits
    audit_issues = _run_audit_rules(period_invoices, period_expenses)
    critical_count = len([i for i in audit_issues if i.severity == "CRITICAL"])
    
    return WizardState(
        calculation=tax_calc,
        issues=audit_issues,
        ready_to_close=(critical_count == 0)
    )

@router.get("/state", response_model=WizardState)
def get_wizard_state(
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2000, le=2100),
    current_user: UserInDB = Depends(get_current_user)
):
    """Returns the JSON state for the frontend wizard UI."""
    return _get_wizard_data(month, year, current_user)

@router.get("/report/pdf")
def download_monthly_report(
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2000, le=2100),
    current_user: UserInDB = Depends(get_current_user)
):
    """Generates and downloads the PDF report."""
    # 1. Get the data
    state = _get_wizard_data(month, year, current_user)
    
    # 2. Generate PDF
    pdf_buffer = generate_monthly_report_pdf(state, current_user, month, year)
    
    filename = f"Raporti_Financiar_{month}_{year}.pdf"
    
    # 3. Stream response
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )