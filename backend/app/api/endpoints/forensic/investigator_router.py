# FILE: backend/app/api/endpoints/forensic/investigator_router.py
# PHOENIX PROTOCOL - FORENSIC INVESTIGATOR LOG ROUTER V1.0 (MULTI-ROLE SYNTHESIS)

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
    Ekzekuton hetimin e thelluar duke simuluar 3 role thelbësore të drejtësisë:
    1. Hetuesi Policor (Faktet materiale, gjurmët dhe vlefshmëria e sekuestrimit)
    2. Prokurori i Shtetit (Barra e provës, elementet e veprës penale dhe kualifikimi)
    3. Gjyqtari (Rregullsia procedurale, In Dubio Pro Reo, dhe standardi i provueshmërisë)
    """
    user_id = str(current_user.id)

    system_prompt = """EKSPERTIZA E DITARIT TË HETUESIT (3-ROLËSH) - CLAUDE SONNET 4.6:
Ju jeni një trup i pavarur hetimor i përbërë nga:
- HETUES POLICOR I KRIMEVE TË RËNDA
- PROKUROR SPECIAL I SHTETIT
- GJYQTAR I PROCEDURËS PARAPRAKE

Analizoni provat e dhëna dhe identifikoni pikat më të ndjeshme, shkeljet procedurale dhe kontradiktat.

Kthe përgjigjen VETËM në format të pastër JSON:
{
  "investigation_summary": "Përmbledhje e përgjithshme e situatës hetimore",
  "police_perspective": {
    "factual_gaps": ["Zbrazëtira faktike 1", "Zbrazëtira faktike 2"],
    "evidence_chain_integrity": "Vlerësimi mbi sigurimin e vendit të ngjarjes dhe provave",
    "recommended_actions": ["Veprim operativ 1", "Veprim operativ 2"]
  },
  "prosecutor_perspective": {
    "elements_of_offense_met": ["Cilat elemente të veprës plotësohen"],
    "missing_corpus_delicti": ["Çfarë mungon për të ngritur aktakuzë të qëndrueshme"],
    "indictment_vulnerability": "Pika ku aktakuza mund të rrëzohet me lehtësi"
  },
  "judge_perspective": {
    "procedural_violations": ["Shkelje procedurale të mundshme (p.sh. bastisje e paligjshme)"],
    "in_dubio_pro_reo_assessment": "Pikët ku dyshimi i arsyeshëm duhet të shkojë në favor të të pandehurit",
    "admissibility_verdict": "A janë provat të pranueshme sipas KPP të Kosovës?"
  },
  "tactical_masterstroke": "Këshilla supreme e mbrojtjes për të fituar lëndën"
}"""

    import json
    user_content = f"""KONTEKSTI I LËNDËS DHE DËSHMITË:
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