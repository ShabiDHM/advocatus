# FILE: backend/app/api/endpoints/forensic/war_room_router.py
# PHOENIX PROTOCOL - FORENSIC DEDICATED WAR ROOM ROUTER V1.0 (GRAPHRAG & CROSS-EXAMINATION ENGINE)
# 100% COMPLETE CODE • ZERO CLIENT INTERFERENCE • RBAC PROTECTED

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.database import Database
from pydantic import BaseModel, Field

from app.core.db import get_db
from app.api.endpoints.dependencies import get_current_forensic_user
from app.models.user import UserInDB
from app.services.forensic.forensic_audit_service import log_forensic_action
from app.services.forensic.forensic_rag_service import (
    synthesize_war_room_intelligence,
    query_legal_knowledge_graph
)

router = APIRouter(prefix="/war-room", tags=["Forensic War Room"])
logger = logging.getLogger(__name__)

FORENSIC_WAR_ROOM_COLLECTION = "forensic_war_room_records"

class WarRoomSynthesisRequest(BaseModel):
    case_id: str
    case_title: str
    audio_findings: Optional[Dict[str, Any]] = None
    visual_findings: Optional[Dict[str, Any]] = None
    financial_findings: Optional[Dict[str, Any]] = None
    document_excerpts: Optional[List[str]] = None
    search_graph_term: Optional[str] = None

class GraphQueryRequest(BaseModel):
    term: str = Field(..., min_length=2)

# ==========================================================
# 1. KRYQËZIMI MULTIMODAL DHE PYETJET TËRTHORE (CLAUDE 4.6)
# ==========================================================
@router.post("/synthesize")
def synthesize_war_room_endpoint(
    payload: WarRoomSynthesisRequest,
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db)
):
    user_id = str(current_user.id)
    graph_data = []
    if payload.search_graph_term:
        graph_data = query_legal_knowledge_graph(payload.search_graph_term)

    # Ekzekutimi me Claude Sonnet 4.6
    synthesis = synthesize_war_room_intelligence(
        case_title=payload.case_title,
        audio_findings=payload.audio_findings,
        visual_findings=payload.visual_findings,
        financial_findings=payload.financial_findings,
        document_excerpts=payload.document_excerpts,
        graph_context=graph_data
    )

    now = datetime.now(timezone.utc)
    record_doc = {
        "case_id": str(payload.case_id),
        "owner_id": user_id,
        "case_title": payload.case_title,
        "synthesis": synthesis,
        "created_at": now
    }
    db[FORENSIC_WAR_ROOM_COLLECTION].insert_one(record_doc)

    log_forensic_action(
        db=db,
        user_id=user_id,
        case_id=payload.case_id,
        action="WAR_ROOM_SYNTHESIS_EXECUTED",
        details={
            "case_title": payload.case_title,
            "traps_count": len(synthesis.get("cross_examination_traps", []))
        }
    )

    return {"success": True, "data": synthesis}

# ==========================================================
# 2. GRAPHRAG (PYETJA E RRJETIT GRAFIK NEO4J)
# ==========================================================
@router.post("/graph-query")
def graph_query_endpoint(
    payload: GraphQueryRequest,
    current_user: UserInDB = Depends(get_current_forensic_user)
):
    results = query_legal_knowledge_graph(payload.term)
    return {"query": payload.term, "results": results}

# ==========================================================
# 3. SINTEZA MË E FUNDIT E RUAJTUR
# ==========================================================
@router.get("/{case_id}/latest")
def get_latest_war_room_synthesis(
    case_id: str,
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db)
):
    record = db[FORENSIC_WAR_ROOM_COLLECTION].find_one(
        {"case_id": str(case_id)},
        sort=[("created_at", -1)]
    )
    if not record:
        return {"has_record": False, "data": None}

    record["_id"] = str(record["_id"])
    if isinstance(record.get("created_at"), datetime):
        record["created_at"] = record["created_at"].isoformat()

    return {"has_record": True, "data": record.get("synthesis"), "created_at": record.get("created_at")}