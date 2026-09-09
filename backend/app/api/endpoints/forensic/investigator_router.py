# FILE: backend/app/api/endpoints/forensic/investigator_router.py
# PHOENIX PROTOCOL - FORENSIC INVESTIGATOR LOG ROUTER V1.1 (CLEAN PROFESSIONAL TONE)

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pymongo.database import Database
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from app.core.db import get_db
from app.api.endpoints.dependencies import get_current_forensic_user
from app.models.user import UserInDB
from app.services.forensic.forensic_llm_service import call_forensic_llm
from app.services.forensic.forensic_audit_service import log_forensic_action

router = APIRouter()

INVESTIGATOR_FINDINGS_COLLECTION = "forensic_investigator_findings"

class RunInvestigationRequest(BaseModel):
    case_id: str
    case_context: str = Field(..., min_length=10)
    focus_evidence: Optional[List[str]] = Field(default_factory=list)

@router.get("/investigate/{case_id}/findings")
def get_investigator_findings(
    case_id: str,
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db)
):
    """Merr të gjitha gjetjet e regjistruara në ditarin e hetuesit për këtë lëndë."""
    cursor = db[INVESTIGATOR_FINDINGS_COLLECTION].find(
        {"case_id": str(case_id)}
    ).sort("created_at", -1)

    findings = []
    for f in cursor:
        f["_id"] = str(f["_id"])
        if isinstance(f.get("created_at"), datetime):
            f["created_at"] = f["created_at"].isoformat()
        findings.append(f)
    return {"case_id": case_id, "findings": findings}

@router.post("/investigate")
def run_investigation_analysis(
    payload: RunInvestigationRequest,
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db)
):
    """
    Ekzekuton analizën hetimore duke simuluar këndvështrime të ndryshme profesionale.
    """
    user_id = str(current_user.id)

    system_prompt = """Ju jeni një analist ligjor i pavarur. Kryeni një analizë të thellë të provave dhe kontekstit të çështjes sipas legjislacionit të Republikës së Kosovës.
Jepni rezultatin në formatin e mëposhtëm JSON:
{
  "investigation_summary": "Përmbledhje e përgjithshme",
  "police_perspective": {
    "factual_gaps": ["Zbrazëtira faktike"],
    "evidence_chain_integrity": "Vlerësimi i zinxhirit të provave",
    "recommended_actions": ["Veprime të rekomanduara"]
  },
  "prosecutor_perspective": {
    "elements_of_offense_met": ["Elemente të veprës penale të plotësuara"],
    "missing_corpus_delicti": ["Mungesa për aktakuzë"],
    "indictment_vulnerability": "Pika e dobët e aktakuzës"
  },
  "judge_perspective": {
    "procedural_violations": ["Shkelje procedurale"],
    "in_dubio_pro_reo_assessment": "Vlerësimi i dyshimit të arsyeshëm",
    "admissibility_verdict": "Pranueshmëria e provave"
  },
  "tactical_masterstroke": "Rekomandim taktik"
}"""

    import json
    user_content = f"""KONTEKSTI I LËNDËS:
{payload.case_context}

PROVAT SPECIFIKE NË SHQYRTIM:
{json.dumps(payload.focus_evidence, ensure_ascii=False, indent=2)}"""

    raw_response = call_forensic_llm(
        system_prompt=system_prompt,
        user_content=user_content,
        json_mode=True,
        temperature=0.0
    )

    try:
        from app.services.llm.llm_client import clean_and_parse_json
        parsed = clean_and_parse_json(raw_response)
        if not parsed:
            raise ValueError("JSON i pavlefshëm nga LLM")
    except Exception:
        parsed = {
            "investigation_summary": raw_response,
            "police_perspective": {"factual_gaps": [], "evidence_chain_integrity": "N/A", "recommended_actions": []},
            "prosecutor_perspective": {"elements_of_offense_met": [], "missing_corpus_delicti": [], "indictment_vulnerability": "N/A"},
            "judge_perspective": {"procedural_violations": [], "in_dubio_pro_reo_assessment": "N/A", "admissibility_verdict": "N/A"},
            "tactical_masterstroke": "Rishikoni me kujdes provat materiale."
        }

    doc = {
        "case_id": str(payload.case_id),
        "user_id": user_id,
        "findings": parsed,
        "created_at": datetime.now(timezone.utc)
    }
    result = db[INVESTIGATOR_FINDINGS_COLLECTION].insert_one(doc)

    log_forensic_action(
        db=db,
        user_id=user_id,
        case_id=payload.case_id,
        action="INVESTIGATOR_ANALYSIS_EXECUTED"
    )

    return {
        "_id": str(result.inserted_id),
        "case_id": payload.case_id,
        "findings": parsed,
        "created_at": doc["created_at"].isoformat()
    }