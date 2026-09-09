# FILE: backend/app/api/endpoints/forensic/investigator_router.py
# PHOENIX PROTOCOL - FORENSIC INVESTIGATOR LOG ROUTER V1.2 (RAG + STREAMING)
# 100% COMPLETE CODE • ZERO PY WARNINGS • MULTI-DEVICE SYNC

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pymongo.database import Database
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field
import logging
import json

from app.core.db import get_db
from app.api.endpoints.dependencies import get_current_forensic_user
from app.models.user import UserInDB
from app.services.forensic.forensic_llm_service import call_forensic_llm, stream_forensic_llm_async
from app.services.forensic.forensic_audit_service import log_forensic_action
from app.services.vector_store_service import query_case_knowledge_base, query_global_knowledge_base

router = APIRouter()
logger = logging.getLogger(__name__)

INVESTIGATOR_FINDINGS_COLLECTION = "forensic_investigator_findings"

class RunInvestigationRequest(BaseModel):
    case_id: str
    case_context: str = Field(..., min_length=10)
    focus_evidence: Optional[List[str]] = Field(default_factory=list)

def _build_system_prompt(case_context: str, focus_evidence: List[str], case_chunks: List, knowledge_chunks: List) -> str:
    case_context_text = "\n".join([
        f"📄 {c.get('source','Dokument')} (Faqe {c.get('page','?')}): {c.get('text','')}"
        for c in case_chunks if c.get("text")
    ]) if case_chunks else "Nuk ka pjesë relevante nga dokumentet e lëndës."

    knowledge_context_text = "\n".join([
        f"{c.get('source','Ligj')}: {c.get('text','')}"
        for c in knowledge_chunks if c.get("text")
    ]) if knowledge_chunks else "Nuk ka referenca ligjore relevante."

    return f"""Ju jeni një analist ligjor i pavarur. Kryeni një analizë të thellë të provave dhe kontekstit të çështjes sipas legjislacionit të Republikës së Kosovës.
Jepni rezultatin në formatin e mëposhtëm JSON:
{{
  "investigation_summary": "Përmbledhje e përgjithshme",
  "police_perspective": {{
    "factual_gaps": ["Zbrazëtira faktike"],
    "evidence_chain_integrity": "Vlerësimi i zinxhirit të provave",
    "recommended_actions": ["Veprime të rekomanduara"]
  }},
  "prosecutor_perspective": {{
    "elements_of_offense_met": ["Elemente të veprës penale të plotësuara"],
    "missing_corpus_delicti": ["Mungesa për aktakuzë"],
    "indictment_vulnerability": "Pika e dobët e aktakuzës"
  }},
  "judge_perspective": {{
    "procedural_violations": ["Shkelje procedurale"],
    "in_dubio_pro_reo_assessment": "Vlerësimi i dyshimit të arsyeshëm",
    "admissibility_verdict": "Pranueshmëria e provave"
  }},
  "tactical_masterstroke": "Rekomandim taktik"
}}

KONTEKSTI I LËNDËS:
{case_context}

PROVAT SPECIFIKE NË SHQYRTIM:
{json.dumps(focus_evidence, ensure_ascii=False, indent=2)}

PJESËT RELEVANTE NGA DOKUMENTET E LËNDËS (CASE BASE):
{case_context_text}

REFERENCAT LIGJORE DHE PRAKTIKA E GJYKATËS SUPREME (KNOWLEDGE BASE):
{knowledge_context_text}"""

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
    """Non-streaming endpoint për përputhshmëri."""
    user_id = str(current_user.id)
    case_id_str = str(payload.case_id)

    # RAG
    case_chunks = []
    try:
        case_chunks = query_case_knowledge_base(
            user_id=user_id,
            query_text=payload.case_context,
            n_results=6,
            case_id=case_id_str
        )
    except Exception as e:
        logger.warning(f"Case base retrieval failed: {e}")

    knowledge_chunks = []
    try:
        knowledge_chunks = query_global_knowledge_base(
            query_text=payload.case_context,
            n_results=8
        )
    except Exception as e:
        logger.warning(f"Knowledge base retrieval failed: {e}")

    system_prompt = _build_system_prompt(payload.case_context, payload.focus_evidence, case_chunks, knowledge_chunks)

    raw_response = call_forensic_llm(
        system_prompt=system_prompt,
        user_content="",
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
        "case_id": case_id_str,
        "user_id": user_id,
        "findings": parsed,
        "created_at": datetime.now(timezone.utc)
    }
    result = db[INVESTIGATOR_FINDINGS_COLLECTION].insert_one(doc)

    log_forensic_action(
        db=db,
        user_id=user_id,
        case_id=case_id_str,
        action="INVESTIGATOR_ANALYSIS_EXECUTED"
    )

    return {
        "_id": str(result.inserted_id),
        "case_id": case_id_str,
        "findings": parsed,
        "created_at": doc["created_at"].isoformat()
    }

@router.post("/investigate/stream")
async def stream_investigator_analysis(
    payload: RunInvestigationRequest,
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db)
):
    """Streaming endpoint për ditarin e hetuesit."""
    user_id = str(current_user.id)
    case_id_str = str(payload.case_id)
    now_utc = datetime.now(timezone.utc)

    # RAG
    case_chunks = []
    try:
        case_chunks = query_case_knowledge_base(
            user_id=user_id,
            query_text=payload.case_context,
            n_results=6,
            case_id=case_id_str
        )
    except Exception as e:
        logger.warning(f"Case base retrieval failed: {e}")

    knowledge_chunks = []
    try:
        knowledge_chunks = query_global_knowledge_base(
            query_text=payload.case_context,
            n_results=8
        )
    except Exception as e:
        logger.warning(f"Knowledge base retrieval failed: {e}")

    system_prompt = _build_system_prompt(payload.case_context, payload.focus_evidence, case_chunks, knowledge_chunks)

    async def generate():
        full_response = ""
        try:
            async for token in stream_forensic_llm_async(
                system_prompt=system_prompt,
                user_content="",
                temperature=0.0,
                max_tokens=16384
            ):
                full_response += token
                yield token
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"\n\n[GABIM: {str(e)}]"
        finally:
            if full_response:
                try:
                    from app.services.llm.llm_client import clean_and_parse_json
                    parsed = clean_and_parse_json(full_response)
                    if not parsed:
                        raise ValueError("JSON i pavlefshëm")
                except Exception:
                    parsed = {
                        "investigation_summary": full_response,
                        "police_perspective": {"factual_gaps": [], "evidence_chain_integrity": "N/A", "recommended_actions": []},
                        "prosecutor_perspective": {"elements_of_offense_met": [], "missing_corpus_delicti": [], "indictment_vulnerability": "N/A"},
                        "judge_perspective": {"procedural_violations": [], "in_dubio_pro_reo_assessment": "N/A", "admissibility_verdict": "N/A"},
                        "tactical_masterstroke": "Rishikoni me kujdes provat materiale."
                    }

                doc = {
                    "case_id": case_id_str,
                    "user_id": user_id,
                    "findings": parsed,
                    "created_at": datetime.now(timezone.utc)
                }
                db[INVESTIGATOR_FINDINGS_COLLECTION].insert_one(doc)

                log_forensic_action(
                    db=db,
                    user_id=user_id,
                    case_id=case_id_str,
                    action="INVESTIGATOR_ANALYSIS_EXECUTED"
                )

    return StreamingResponse(
        generate(),
        media_type="text/plain; charset=utf-8",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )