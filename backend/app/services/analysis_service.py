# FILE: backend/app/services/analysis_service.py
# PHOENIX PROTOCOL - ANALYSIS SERVICE V9.0 (GRAPH-ENHANCED)
# 1. INTEGRATION: Now fetches 'Graph Contradictions' to ground the LLM.
# 2. LOGIC: Merges Textual Evidence (MongoDB) with Structural Evidence (Neo4j).
# 3. SAFETY: Fallback logic retained.

import structlog
from typing import Dict, Any, List
from pymongo.database import Database
from bson import ObjectId

# Import central intelligence & graph engine
from . import llm_service
from .graph_service import graph_service

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
            doc_id = str(doc["_id"])
            
            # STRATEGY 1: Look for Verified Findings (High Quality)
            findings = list(db.findings.find({"document_id": doc_id}))
            # Also support finding by ObjectId if stored that way
            if not findings:
                findings = list(db.findings.find({"document_id": doc["_id"]}))
            
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
    """
    Performs a deep analysis of the case, checking for contradictions
    between the Text (Documents) and the Structure (Graph).
    """
    log = logger.bind(case_id=case_id)
    
    # 1. Gather Textual Data (MongoDB)
    full_case_text = _get_full_case_text(db, case_id)
    
    # 2. Gather Structural Data (Neo4j)
    # This is the "Phoenix" upgrade: Grounding the analysis in the Graph.
    graph_evidence = ""
    try:
        graph_contradictions = graph_service.find_contradictions(case_id)
        if graph_contradictions and "No direct" not in graph_contradictions:
            graph_evidence = f"--- INTELIGJENCA NGA GRAFI (Logjike/Kontradikta) ---\n{graph_contradictions}\n\n"
    except Exception as e:
        log.warning("analysis.graph_fetch_failed", error=str(e))

    # 3. Safety Check
    total_context = graph_evidence + full_case_text
    if not total_context or len(total_context) < 50:
        return {
            "summary": "Nuk ka të dhëna.",
            "risks": [],
            "contradictions": [],
            "missing_info": [],
            "error": "Nuk ka mjaftueshëm të dhëna për analizë. Ju lutem prisni që OCR të përfundojë."
        }
    
    # 4. DELEGATE to the "Debate Judge" in llm_service
    try:
        # We pass the combined context (Graph + Text) to the LLM
        analysis_result = llm_service.analyze_case_contradictions(total_context)
    except Exception as e:
        log.error("analysis.llm_call_failed", error=str(e))
        return {"error": "Analiza dështoi për shkaqe teknike."}

    if not analysis_result:
        return {"error": "Inteligjenca Artificiale nuk ktheu përgjigje."}

    return analysis_result