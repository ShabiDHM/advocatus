# FILE: backend/app/services/analysis_service.py
# PHOENIX PROTOCOL - ANALYSIS SERVICE V8.5 (DATA FALLBACK)
# 1. LOGIC: Added 'extracted_text' fallback. If AI findings aren't ready, we use raw OCR text.
# 2. SAFETY: Ensures the LLM always gets data if the document exists.

import structlog
from typing import Dict, Any
from pymongo.database import Database
from bson import ObjectId

# Import the central intelligence engine
from . import llm_service

logger = structlog.get_logger(__name__)

def _get_full_case_text(db: Database, case_id: str) -> str:
    """
    Aggregates all available text for a case.
    Priority: Findings (Best) -> Summary (Good) -> Raw Text (Fallback).
    """
    try:
        case_oid = ObjectId(case_id)
        # Fetch both ObjectId and String IDs to be safe
        documents = list(db.documents.find({"case_id": {"$in": [case_oid, case_id]}}))
        
        context_buffer = []
        for doc in documents:
            name = doc.get("file_name", "Unknown Document")
            doc_id = doc["_id"]
            
            # STRATEGY 1: Look for Verified Findings (High Quality)
            findings = list(db.findings.find({"document_id": doc_id}))
            
            if findings:
                findings_text = "\n".join([f"- {f.get('finding_text', '')}" for f in findings])
                doc_context = f"--- DOKUMENTI: {name} (Fakte të Gjetura) ---\n{findings_text}\n\n"
                context_buffer.append(doc_context)
            else:
                # STRATEGY 2: Fallback to Summary
                summary = doc.get("summary", "")
                if summary:
                    context_buffer.append(f"--- DOKUMENTI: {name} (Përmbledhje) ---\n{summary}\n\n")
                else:
                    # STRATEGY 3: Fallback to Raw OCR Text (Emergency Mode)
                    # This prevents "Empty Context" errors if background tasks are slow
                    raw_text = doc.get("extracted_text", "") or doc.get("text", "")
                    if raw_text:
                        # Limit raw text to avoid token overflow, but give enough to work with
                        truncated_text = raw_text[:3000] 
                        context_buffer.append(f"--- DOKUMENTI: {name} (Tekst i Papërpunuar) ---\n{truncated_text}\n\n")

        return "".join(context_buffer)
    except Exception as e:
        logger.error("analysis.context_build_failed", error=str(e))
        return ""

def cross_examine_case(db: Database, case_id: str) -> Dict[str, Any]:
    log = logger.bind(case_id=case_id)
    
    # 1. Gather Data
    full_case_text = _get_full_case_text(db, case_id)
    
    # 2. Safety Check
    if not full_case_text or len(full_case_text) < 50:
        return {
            "summary": "Nuk ka të dhëna.",
            "risks": [],
            "contradictions": [],
            "missing_info": [],
            "error": "Nuk ka mjaftueshëm të dhëna për analizë. Ju lutem prisni që OCR të përfundojë."
        }
    
    # 3. DELEGATE to the "Debate Judge" in llm_service
    try:
        analysis_result = llm_service.analyze_case_contradictions(full_case_text)
    except Exception as e:
        log.error("analysis.llm_call_failed", error=str(e))
        return {"error": "Analiza dështoi për shkaqe teknike."}

    if not analysis_result:
        return {"error": "Inteligjenca Artificiale nuk ktheu përgjigje."}

    return analysis_result