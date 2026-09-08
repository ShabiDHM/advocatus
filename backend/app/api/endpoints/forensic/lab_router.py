# FILE: backend/app/api/endpoints/forensic/lab_router.py
# PHOENIX PROTOCOL - FORENSIC MULTI-LABORATORY ROUTER V1.0

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from pymongo.database import Database
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

from app.core.db import get_db
from app.api.endpoints.dependencies import get_current_forensic_user
from app.models.user import UserInDB
from app.services.forensic.forensic_audit_service import log_forensic_action

from app.services.forensic.forensic_audio_service import process_audio_file
from app.services.forensic.forensic_visual_service import process_visual_evidence
from app.services.forensic.forensic_finance_service import (
    calculate_lmd_interest,
    analyze_financial_spreadsheet,
    generate_financial_forensic_opinion
)
from app.services.forensic.forensic_rag_service import (
    synthesize_war_room_intelligence,
    query_legal_knowledge_graph
)

router = APIRouter()

# --- DTOs PËR FINANCË DHE WAR ROOM ---
class LegalInterestRequest(BaseModel):
    principal: float = Field(..., gt=0, description="Kryegjëja e borxhit kryesor")
    start_date: str = Field(..., description="Data e fillimit të vonesës (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="Data e përfundimit (YYYY-MM-DD), default sot")
    rate_percent: Optional[float] = Field(8.0, description="Norma vjetore e kamatës (default 8% sipas LMD)")
    case_id: Optional[str] = None

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
# 1. LABORATORI I AUDIOS (DIARIZIM + ANALIZË STRESI)
# ==========================================================
@router.post("/audio/analyze")
async def analyze_audio_lab(
    case_id: str = Form(...),
    case_context: str = Form(""),
    file: UploadFile = File(...),
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db)
):
    """
    Ekzekuton diarizimin e folësve dhe analizën e stresit përmes AssemblyAI & Claude Sonnet 4.6.
    """
    user_id = str(current_user.id)
    try:
        content_bytes = await file.read()
        if not content_bytes:
            raise HTTPException(status_code=400, detail="Skedari audio është i zbrazët.")

        result = process_audio_file(
            audio_bytes=content_bytes,
            case_context=case_context
        )

        log_forensic_action(
            db=db,
            user_id=user_id,
            case_id=case_id,
            action="AUDIO_ANALYSIS_COMPLETED",
            details={
                "file_name": file.filename,
                "segments_count": len(result.get("segments", [])),
                "threat_level": result.get("forensic_intelligence", {}).get("threat_level", "N/A")
            }
        )

        return {
            "success": True,
            "file_name": file.filename,
            "data": result
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dështoi analiza e audios: {str(e)}"
        )

# ==========================================================
# 2. LABORATORI VIZUAL (EXIF/GPS + ELA + GOOGLE VISION)
# ==========================================================
@router.post("/visual/analyze")
async def analyze_visual_lab(
    case_id: str = Form(...),
    case_context: str = Form(""),
    file: UploadFile = File(...),
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db)
):
    """
    Ekzekuton analizën e thellë vizuale: EXIF, GPS, manipulim ELA dhe njohje objektesh me Claude Sonnet 4.6.
    """
    user_id = str(current_user.id)
    try:
        content_bytes = await file.read()
        if not content_bytes:
            raise HTTPException(status_code=400, detail="Skedari i imazhit është i zbrazët.")

        result = process_visual_evidence(
            image_bytes=content_bytes,
            case_context=case_context
        )

        log_forensic_action(
            db=db,
            user_id=user_id,
            case_id=case_id,
            action="VISUAL_ANALYSIS_COMPLETED",
            details={
                "file_name": file.filename,
                "has_gps": result.get("exif_metadata", {}).get("has_gps", False),
                "manipulation_score": result.get("tamper_analysis", {}).get("manipulation_risk_score", 0.0)
            }
        )

        return {
            "success": True,
            "file_name": file.filename,
            "data": result
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dështoi analiza vizuale: {str(e)}"
        )

# ==========================================================
# 3. LABORATORI FINANCIAR (LMD NENI 265 + PANDAS SPREADSHEET)
# ==========================================================
@router.post("/finance/calculate-interest")
def calculate_interest_endpoint(
    payload: LegalInterestRequest,
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db)
):
    """Llogarit kamatëvonesën ligjore sipas Nenit 265 të LMD-së (8%)."""
    user_id = str(current_user.id)
    try:
        interest_res = calculate_lmd_interest(
            principal=payload.principal,
            start_date_str=payload.start_date,
            end_date_str=payload.end_date,
            rate_percent=payload.rate_percent or 8.0
        )

        if payload.case_id:
            log_forensic_action(
                db=db,
                user_id=user_id,
                case_id=payload.case_id,
                action="LMD_INTEREST_CALCULATED",
                details={
                    "principal": payload.principal,
                    "interest_amount": interest_res["interest_amount"],
                    "total_obligation": interest_res["total_obligation"]
                }
            )

        return {"success": True, "data": interest_res}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/finance/analyze-spreadsheet")
async def analyze_spreadsheet_endpoint(
    case_id: str = Form(...),
    claimed_amount: Optional[float] = Form(None),
    case_context: str = Form(""),
    file: UploadFile = File(...),
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db)
):
    """Analizon pasqyrat financiare Excel/CSV me Pandas dhe jep ekspertizën me Claude Sonnet 4.6."""
    user_id = str(current_user.id)
    try:
        content_bytes = await file.read()
        if not content_bytes:
            raise HTTPException(status_code=400, detail="Skedari tabelor është i zbrazët.")

        spreadsheet_analysis = analyze_financial_spreadsheet(
            file_bytes=content_bytes,
            file_name=file.filename,
            claimed_amount=claimed_amount
        )

        opinion = generate_financial_forensic_opinion(
            spreadsheet_analysis=spreadsheet_analysis,
            case_context=case_context
        )

        log_forensic_action(
            db=db,
            user_id=user_id,
            case_id=case_id,
            action="FINANCIAL_SPREADSHEET_AUDITED",
            details={
                "file_name": file.filename,
                "total_documented": spreadsheet_analysis.get("total_documented_amount", 0.0),
                "verdict": opinion.get("financial_audit_verdict", "")
            }
        )

        return {
            "success": True,
            "spreadsheet_analysis": spreadsheet_analysis,
            "forensic_opinion": opinion
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Dështoi analiza financiare: {str(e)}")

# ==========================================================
# 4. WAR ROOM INTERAKTIV DHE GRAPHRAG
# ==========================================================
@router.post("/war-room/synthesize")
def synthesize_war_room_endpoint(
    payload: WarRoomSynthesisRequest,
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db)
):
    """Gjeneron sintezën madhore të War Room dhe pyetjet tërthore (Cross-Examination) me Claude Sonnet 4.6."""
    user_id = str(current_user.id)
    graph_data = []
    if payload.search_graph_term:
        graph_data = query_legal_knowledge_graph(payload.search_graph_term)

    synthesis = synthesize_war_room_intelligence(
        case_title=payload.case_title,
        audio_findings=payload.audio_findings,
        visual_findings=payload.visual_findings,
        financial_findings=payload.financial_findings,
        document_excerpts=payload.document_excerpts,
        graph_context=graph_data
    )

    log_forensic_action(
        db=db,
        user_id=user_id,
        case_id=payload.case_id,
        action="WAR_ROOM_SYNTHESIS_GENERATED",
        details={"case_title": payload.case_title}
    )

    return {"success": True, "data": synthesis}

@router.post("/war-room/graph-query")
def graph_query_endpoint(
    payload: GraphQueryRequest,
    current_user: UserInDB = Depends(get_current_forensic_user)
):
    """Pyet rrjetin grafik Neo4j për nene ligjore dhe precedentë."""
    results = query_legal_knowledge_graph(payload.term)
    return {"query": payload.term, "results": results}