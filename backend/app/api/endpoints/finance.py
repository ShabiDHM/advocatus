# FILE: backend/app/api/endpoints/finance.py
# PHOENIX PROTOCOL - FINANCE ROUTER V52.2 (PRICE 99.00)
# V52.2: DEFAULT_UNLOCK_PRICE_EUR default: 9.99 → 99.00.
# V52.1: FIX — admin_manual_unlock_case tani bllokon me 403 në vend të 'pass' bosh.
# V52.0: ORG-AWARE — checkout endpoints verifikojnë akses përmes _build_case_access_query.
# V51.0: Hequr endpoint-i /forensic-report/archive + klasa ArchiveForensicReportRequest.

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Body
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from typing import List, Annotated, Optional, Any, Dict
from datetime import datetime, timedelta, timezone
from bson import ObjectId
from pymongo.database import Database 
import asyncio
import os
import structlog

from app.core.config import settings
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
from app.services.report_service import generate_invoice_pdf
from app.services.ocr_service import extract_text_from_image_bytes
from app.services.llm_service import extract_expense_details_from_text
from app.api.endpoints.dependencies import get_current_user, get_db, get_current_active_user
from app.api.endpoints.cases.cases_helpers import validate_object_id
from app.services.case_service import _build_case_access_query

router = APIRouter(tags=["Finance"])
logger = structlog.get_logger(__name__)

# ========== KONFIGURIMI I PAGESAVE (KOSOVË) ==========
DEFAULT_UNLOCK_PRICE_EUR = float(os.getenv("CASE_UNLOCK_PRICE_EUR", "99.00"))   # V52.2
BANK_NAME = os.getenv("COMPANY_BANK_NAME", "Raiffeisen Bank Kosova")
BANK_ACCOUNT_HOLDER = os.getenv("COMPANY_ACCOUNT_HOLDER", "Juristi AI / Advocatus SH.P.K.")
BANK_IBAN = os.getenv("RAIFFEISEN_IBAN", "XK051501001000000000")
BANK_SWIFT = os.getenv("RAIFFEISEN_SWIFT", "RBKOXKPR")

# V52.1: Rolet e lejuara për veprime administrative
ADMIN_ROLES = {"ADMIN", "SUPERADMIN", "STAFF"}