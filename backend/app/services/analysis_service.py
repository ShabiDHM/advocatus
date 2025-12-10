# FILE: backend/app/services/analysis_service.py
# PHOENIX PROTOCOL - ANALYSIS SERVICE V8.0 (UNIFIED INTELLIGENCE)
# 1. DEPRECATION: Removed all local prompts and LLM call logic.
# 2. DELEGATION: This service no longer performs analysis. It now acts as a controller that calls the central 'llm_service'.
# 3. UNIFICATION: Ensures the 'Analizo Rastin' button uses the same "Debate Judge" brain as the rest of the system.

import structlog
from typing import Dict, Any
from pymongo.database import Database
from bson import ObjectId

# PHOENIX: Import the *actual brain* of the application
from . import llm_service
from .graph_service import graph_service

logger = structlog.get_logger(__name__)

def _get_full_case_text(db: Database, case_id: str) -> str:
    """
    Gathers all raw text from all documents in a case into a single string.
    This is used to provide the complete context to the analysis engine.
    """
    try:
        # PHOENIX: Use a more robust query to handle both ObjectId and string case_ids
        case_oid = ObjectId(case_id)
        documents = list(db.documents.find({"case_id": {"$in": [case_oid, case_id]}}))
        
        context_buffer = []
        for doc in documents:
            name = doc.get("file_name", "Unknown Document")
            # We will use the raw text from findings, not summaries, for deeper analysis
            findings = list(db.findings.find({"document_id": doc["_id"]}))
            
            if findings:
                # Use the source text from findings as it's the most direct evidence
                findings_text = "\n".join([f.get('source_text', '') for f in findings])
                doc_context = f"--- DOKUMENTI: {name} ---\n{findings_text}\n\n"
                context_buffer.append(doc_context)

        return "".join(context_buffer)
    except Exception as e:
        logger.error("analysis.context_build_failed", error=str(e))
        return ""

def cross_examine_case(db: Database, case_id: str) -> Dict[str, Any]:
    """
    Orchestrates the case analysis by delegating to the central llm_service.
    """
    log = logger.bind(case_id=case_id)
    
    # 1. Aggregate all text content for the case.
    full_case_text = _get_full_case_text(db, case_id)
    if not full_case_text or not full_case_text.strip():
        log.warning("analysis.no_content", message="No text content found for case analysis.")
        return {"error": "Nuk ka përmbajtje tekstuale në dosje për të kryer analizën."}
    
    # 2. DELEGATE analysis to the unified, powerful llm_service.
    # This calls the "Debate Judge" prompt we engineered.
    try:
        analysis_result = llm_service.analyze_case_contradictions(full_case_text)
    except Exception as e:
        log.error("analysis.llm_service_call_failed", error=str(e))
        return {"error": "Shërbimi i inteligjencës artificiale dështoi."}

    if not analysis_result:
        log.warning("analysis.empty_result", message="LLM service returned an empty analysis.")
        return {"error": "Analiza nuk prodhoi asnjë rezultat."}

    # 3. (Optional) Ingest key findings into the graph for visualization.
    # This can be expanded later. For now, we focus on returning the correct analysis.
    try:
        if "contradictions" in analysis_result and analysis_result["contradictions"]:
            # Example of how you might add graph data in the future
            graph_items = [
                {"type": "CONTRADICTION", "source": "Pala A", "target": "Pala B", "text": c} 
                for c in analysis_result["contradictions"]
            ]
            # graph_service.ingest_legal_analysis(case_id, f"ANALYSIS_{case_id}", graph_items)
    except Exception as e:
        log.error("analysis.graph_ingest_failed", error=str(e))

    return analysis_result