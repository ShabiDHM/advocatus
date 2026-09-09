# FILE: backend/app/api/endpoints/forensic/finance_router.py
# PHOENIX PROTOCOL - FORENSIC DEDICATED FINANCE ROUTER V1.1 (PERSISTENT LMD & DOCUMENT STORAGE)
# 100% COMPLETE CODE • ZERO CLIENT INTERFERENCE • RBAC PROTECTED

import io
import os
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from pymongo.database import Database
from pydantic import BaseModel, Field

from app.core.db import get_db
from app.api.endpoints.dependencies import get_current_forensic_user
from app.models.user import UserInDB
from app.services import storage_service
from app.services.forensic.forensic_chain_of_custody import generate_evidence_hash, create_custody_stamp
from app.services.forensic.forensic_audit_service import log_forensic_action
from app.services.forensic.forensic_finance_service import (
    calculate_lmd_interest,
    analyze_financial_spreadsheet,
    generate_financial_forensic_opinion
)

router = APIRouter(prefix="/finance", tags=["Forensic Finance"])
logger = logging.getLogger(__name__)

FORENSIC_FINANCE_COLLECTION = "forensic_financial_records"
FORENSIC_DOCS_COLLECTION = "forensic_documents"

class LegalInterestRequest(BaseModel):
    principal: float = Field(..., gt=0, description="Kryegjëja e borxhit kryesor")
    start_date: str = Field(..., description="Data e fillimit të vonesës (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="Data e përfundimit (YYYY-MM-DD), default sot")
    rate_percent: Optional[float] = Field(8.0, description="Norma vjetore e kamatës (default 8% sipas LMD)")
    case_id: Optional[str] = None

# ==========================================================
# 1. LLOGARITJA E KAMATËS STATUTORE (LMD NENI 265)
# ==========================================================
@router.post("/calculate-interest")
def calculate_interest_endpoint(
    payload: LegalInterestRequest,
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db)
):
    user_id = str(current_user.id)
    try:
        interest_res = calculate_lmd_interest(
            principal=payload.principal,
            start_date_str=payload.start_date,
            end_date_str=payload.end_date,
            rate_percent=payload.rate_percent or 8.0
        )

        # ✅ RUAJ REZULTATIN NË HISTORIK (për t'u ngarkuar pas refresh)
        record_doc = {
            "case_id": str(payload.case_id) if payload.case_id else "",
            "owner_id": user_id,
            "record_type": "LMD_CALCULATION",
            "payload": {
                "principal": payload.principal,
                "start_date": payload.start_date,
                "end_date": payload.end_date,
                "rate_percent": payload.rate_percent or 8.0
            },
            "result": interest_res,
            "created_at": datetime.now(timezone.utc)
        }
        db[FORENSIC_FINANCE_COLLECTION].insert_one(record_doc)

        if payload.case_id:
            log_forensic_action(
                db=db,
                user_id=user_id,
                case_id=payload.case_id,
                action="LMD_ARTICLE_265_INTEREST_SEALED",
                details={
                    "principal": payload.principal,
                    "days": interest_res["days_elapsed"],
                    "interest_amount": interest_res["interest_amount"],
                    "total": interest_res["total_obligation"]
                }
            )

        return {"success": True, "data": interest_res}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ==========================================================
# 2. AUDITIMI I PASQYRAVE ME PANDAS DHE VULË CUSTODY
# ==========================================================
@router.post("/analyze-spreadsheet")
async def analyze_spreadsheet_endpoint(
    case_id: str = Form(...),
    claimed_amount: Optional[float] = Form(None),
    case_context: str = Form(""),
    file: UploadFile = File(...),
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db)
):
    user_id = str(current_user.id)
    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Skedari tabelor është i zbrazët.")

    filename = storage_service.sanitize_filename(file.filename or "financial_spreadsheet.xlsx")
    evidence_hash = generate_evidence_hash(raw_bytes)

    # ✅ Ngarko skedarin në storage si dokument forenzik
    storage_key = await asyncio.to_thread(
        storage_service.upload_bytes_as_file,
        io.BytesIO(raw_bytes),
        filename,
        user_id,
        case_id,
        file.content_type or "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    custody_stamp = create_custody_stamp(
        user_id=user_id,
        case_id=case_id,
        action="FINANCIAL_SPREADSHEET_SECURED",
        evidence_ids=[evidence_hash],
        metadata={"filename": filename, "file_size_bytes": len(raw_bytes)}
    )

    try:
        spreadsheet_analysis = analyze_financial_spreadsheet(
            file_bytes=raw_bytes,
            file_name=filename,
            claimed_amount=claimed_amount
        )

        opinion = generate_financial_forensic_opinion(
            spreadsheet_analysis=spreadsheet_analysis,
            case_context=case_context
        )

        now = datetime.now(timezone.utc)

        # Ruaj rekordin financiar
        record_doc = {
            "case_id": str(case_id),
            "owner_id": user_id,
            "record_type": "SPREADSHEET_ANALYSIS",
            "filename": filename,
            "storage_key": storage_key,
            "evidence_hash": evidence_hash,
            "custody_stamp": custody_stamp,
            "spreadsheet_analysis": spreadsheet_analysis,
            "forensic_opinion": opinion,
            "created_at": now
        }
        db[FORENSIC_FINANCE_COLLECTION].insert_one(record_doc)

        # ✅ KRIJO HYRJE NË DOKUMENTET FORENZIKE (që të shfaqet në panelin e dokumenteve)
        doc_entry = {
            "case_id": str(case_id),
            "owner_id": user_id,
            "file_name": filename,
            "storage_key": storage_key,
            "mime_type": file.content_type or "application/octet-stream",
            "status": "READY",
            "evidence_sha256": evidence_hash,
            "custody_stamp": custody_stamp,
            "extracted_text": "",
            "forensic_pillars": {},
            "created_at": now,
            "updated_at": now,
            "financial_record_id": str(record_doc["_id"])
        }
        db[FORENSIC_DOCS_COLLECTION].insert_one(doc_entry)

        log_forensic_action(
            db=db,
            user_id=user_id,
            case_id=case_id,
            action="FINANCIAL_FORENSIC_AUDIT_COMPLETED",
            details={
                "filename": filename,
                "total_documented": spreadsheet_analysis.get("total_documented_amount", 0.0),
                "custody_hash": custody_stamp["custody_hash"]
            }
        )

        return {
            "success": True,
            "custody_stamp": custody_stamp,
            "spreadsheet_analysis": spreadsheet_analysis,
            "forensic_opinion": opinion
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Dështoi analiza financiare: {str(e)}")

# ==========================================================
# 3. HISTORIKU I EKSPERTIZAVE FINANCIARE
# ==========================================================
@router.get("/{case_id}/records")
def get_case_financial_records(
    case_id: str,
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db)
):
    cursor = db[FORENSIC_FINANCE_COLLECTION].find({"case_id": str(case_id)}).sort("created_at", -1)
    records = []
    for r in cursor:
        r["_id"] = str(r["_id"])
        if isinstance(r.get("created_at"), datetime):
            r["created_at"] = r["created_at"].isoformat()
        records.append(r)
    return {"case_id": case_id, "records": records}