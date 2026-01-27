# FILE: backend/app/api/endpoints/evidence_map.py
# PHOENIX PROTOCOL - EVIDENCE MAP ENDPOINTS V3.0 (GLOBAL RAG INTEGRATION)
# 1. ADDED: POST /gkb-claims endpoint for Global Knowledge Base (RAG) query.
# 2. FIX: Corrected access to case details (now stable).

import io
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List

from app.api.endpoints.dependencies import get_current_user
from app.models.user import UserInDB
from app.models.evidence_map import EvidenceMapInDB, EvidenceMapUpdate
from app.services.evidence_map_service import evidence_map_service, ClaimSuggestion
from app.services.report_service import generate_evidence_map_report
from datetime import datetime

# PHOENIX: Request and Response Models for GKB Query
class GKBQueryRequest(BaseModel):
    query: str = Field(..., description="The user's query to search the Global Knowledge Base for claims.")

class GKBQueryResponse(BaseModel):
    suggestions: List[ClaimSuggestion]
    
router = APIRouter()

@router.get("/cases/{case_id}/evidence-map", response_model=EvidenceMapInDB)
def get_evidence_map(
    case_id: str,
    current_user: UserInDB = Depends(get_current_user)
):
    """
    Get the current visual graph for a case.
    """
    return evidence_map_service.get_map_by_case(case_id, current_user)

@router.put("/cases/{case_id}/evidence-map", response_model=EvidenceMapInDB)
def save_evidence_map(
    case_id: str,
    map_data: EvidenceMapUpdate,
    current_user: UserInDB = Depends(get_current_user)
):
    """
    Save the visual graph state (Auto-save).
    """
    return evidence_map_service.save_map(case_id, map_data, current_user)

@router.post("/cases/{case_id}/evidence-map/report")
def export_evidence_map_pdf(
    case_id: str,
    map_data: EvidenceMapUpdate,
    current_user: UserInDB = Depends(get_current_user)
):
    """
    Generates and streams a structured PDF report of the evidence map (claims and connections).
    """
    # 1. Retrieve case details from DB for the title
    case_oid = evidence_map_service.get_map_by_case(case_id, current_user).case_id
    case_details = evidence_map_service.db.cases.find_one({"_id": case_oid})
    case_title = case_details.get('title') if case_details else case_id
    
    # 2. Generate the PDF
    pdf_buffer = generate_evidence_map_report(
        case_id=case_id,
        map_data=map_data.model_dump(),
        case_title=case_title,
        lang='sq' 
    )

    # 3. Stream the response
    filename = f"EvidenceMap_Report_{case_id}_{datetime.now().strftime('%Y%m%d')}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_buffer.read()),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Content-Type-Options": "nosniff"
        }
    )

# PHOENIX NEW: Global Knowledge Base RAG Query Endpoint
@router.post("/gkb-claims", response_model=GKBQueryResponse)
def get_gkb_claims(
    request: GKBQueryRequest,
    current_user: UserInDB = Depends(get_current_user)
):
    """
    Queries the Global Knowledge Base (ChromaDB) for legal claims/elements related to the query.
    """
    suggestions = evidence_map_service.query_gkb_for_claims(request.query)
    return {"suggestions": suggestions}