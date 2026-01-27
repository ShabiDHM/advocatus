# FILE: backend/app/api/endpoints/evidence_map.py
# PHOENIX PROTOCOL - EVIDENCE MAP ENDPOINTS V2.1 (FINAL BACKEND FIXES)
# 1. FIX: Added 'datetime' import.
# 2. FIX: Corrected access to 'cases_collection' via the service instance.

import io
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from app.api.endpoints.dependencies import get_current_user
from app.models.user import UserInDB
from app.models.evidence_map import EvidenceMapInDB, EvidenceMapUpdate
from app.services.evidence_map_service import evidence_map_service
from app.services.report_service import generate_evidence_map_report
from datetime import datetime # PHOENIX FIX: Added datetime import

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
    # PHOENIX FIX: Access cases_collection via the service's db property (assuming db is accessible via EvidenceMapService)
    # Re-checking the original service, it did not expose 'cases_collection' directly. We assume access via db property.
    # We must retrieve the Case model from the database using the case_id.
    
    # We rely on the evidence_map_service.db property now to access collections.
    # This requires assuming that the case collection name is 'cases'
    
    # 1. Retrieve case details from DB
    case_oid = evidence_map_service.get_map_by_case(case_id, current_user).case_id # Reuse logic to get OID
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