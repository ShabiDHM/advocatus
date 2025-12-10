# FILE: backend/app/services/analysis_service.py
# PHOENIX PROTOCOL - ANALYSIS SERVICE V8.2 (LOGGING VERIFICATION)
# 1. LOGIC: Delegates strictly to 'llm_service.analyze_case_contradictions'.
# 2. VERIFICATION: Added log to confirm the new service is active.

import structlog
from typing import Dict, Any
from pymongo.database import Database
from bson import ObjectId

# PHOENIX: Import the central intelligence engine
from . import llm_service

logger = structlog.get_logger(__name__)

def _get_full_case_text(db: Database, case_id: str) -> str:
    try:
        case_oid = ObjectId(case_id)
        documents = list(db.documents.find({"case_id": {"$in": [case_oid, case_id]}}))
        
        context_buffer = []
        for doc in documents:
            name = doc.get("file_name", "Unknown Document")
            # Prefer finding text (evidence) over raw summaries
            findings = list(db.findings.find({"document_id": doc["_id"]}))
            
            if findings:
                findings_text = "\n".join([f"- {f.get('finding_text', '')}" for f in findings])
                doc_context = f"--- DOKUMENTI: {name} ---\nFAKTET E GJETURA:\n{findings_text}\n\n"
                context_buffer.append(doc_context)
            else:
                summary = doc.get("summary", "")
                if summary:
                    context_buffer.append(f"--- DOKUMENTI: {name} ---\n{summary}\n\n")

        return "".join(context_buffer)
    except Exception as e:
        logger.error("analysis.context_build_failed", error=str(e))
        return ""

def cross_examine_case(db: Database, case_id: str) -> Dict[str, Any]:
    log = logger.bind(case_id=case_id)
    
    # DEBUG LOG: Verify new code is running
    print(f"🔥 PHOENIX_NEW_LOGIC: Starting Debate Analysis for Case {case_id}")
    
    # 1. Gather Data
    full_case_text = _get_full_case_text(db, case_id)
    if not full_case_text or len(full_case_text) < 50:
        return {"error": "Nuk ka mjaftueshëm të dhëna për analizë. Sigurohuni që dokumentet janë ngarkuar dhe procesuar."}
    
    # 2. DELEGATE to the "Debate Judge"
    try:
        # This calls the V5.2 Prompt in llm_service
        analysis_result = llm_service.analyze_case_contradictions(full_case_text)
    except Exception as e:
        log.error("analysis.llm_call_failed", error=str(e))
        return {"error": "Analiza dështoi për shkaqe teknike."}

    if not analysis_result:
        return {"error": "Inteligjenca Artificiale nuk ktheu përgjigje."}

    return analysis_result