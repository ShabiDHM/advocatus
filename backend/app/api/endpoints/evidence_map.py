# FILE: backend/app/api/endpoints/evidence_map.py
# PHOENIX PROTOCOL - EVIDENCE MAP ENDPOINTS
# 1. ROUTES: GET/PUT for Map State.
# 2. AUTH: Protected by 'get_current_user'.

from fastapi import APIRouter, Depends
from app.api.endpoints.dependencies import get_current_user
from app.models.user import UserInDB
from app.models.evidence_map import EvidenceMapInDB, EvidenceMapUpdate
from app.services.evidence_map_service import evidence_map_service

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