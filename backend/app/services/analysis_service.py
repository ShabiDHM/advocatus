# FILE: backend/app/services/analysis_service.py
# PHOENIX PROTOCOL - ANALYSIS SERVICE V10.1 (STORAGE API FIX)
# 1. FIXED: Replaced 'get_file_content' with 'download_processed_text'.
# 2. FIXED: Added .decode('utf-8') for byte content handling.
# 3. STATUS: Crash resolved.

import structlog
from typing import Dict, Any, List, Optional
from pymongo.database import Database
from bson import ObjectId

# Import central intelligence & services
from . import llm_service
from .graph_service import graph_service
from . import storage_service # Required to fetch full text of the target

logger = structlog.get_logger(__name__)

def _get_full_case_text(db: Database, case_id: str) -> str:
    """
    Aggregates all available text for a case.
    Priority: Findings (Best) -> Summary (Good) -> Raw Text (Fallback).
    """
    try:
        case_oid = ObjectId(case_id)
        documents = list(db.documents.find({"case_id": {"$in": [case_oid, case_id]}}))
        
        context_buffer = []
        for doc in documents:
            name = doc.get("file_name", "Unknown Document")
            doc_id = str(doc["_id"])
            
            findings = list(db.findings.find({"document_id": doc_id}))
            if not findings:
                findings = list(db.findings.find({"document_id": doc["_id"]}))
            
            if findings:
                findings_text = "\n".join([f"- {f.get('finding_text', '')}" for f in findings])
                doc_context = f"--- DOKUMENTI: {name} (Fakte të Gjetura) ---\n{findings_text}\n\n"
                context_buffer.append(doc_context)
            else:
                summary = doc.get("summary", "")
                if summary:
                    context_buffer.append(f"--- DOKUMENTI: {name} (Përmbledhje) ---\n{summary}\n\n")
                else:
                    raw_text = doc.get("extracted_text", "") or doc.get("text", "")
                    if raw_text:
                        truncated_text = raw_text[:3000] 
                        context_buffer.append(f"--- DOKUMENTI: {name} (Tekst i Papërpunuar) ---\n{truncated_text}\n\n")

        return "".join(context_buffer)
    except Exception as e:
        logger.error("analysis.context_build_failed", error=str(e))
        return ""

def _find_adversarial_target(documents: List[Dict]) -> Optional[Dict]:
    """
    Scans documents to find the primary legal attack (Lawsuit/Complaint).
    """
    keywords = ["padi", "kerkese", "kërkesë", "aktakuz", "ankes", "lawsuit", "complaint"]
    
    for doc in documents:
        fname = doc.get("file_name", "").lower()
        if any(k in fname for k in keywords):
            return doc
    return None

def cross_examine_case(db: Database, case_id: str) -> Dict[str, Any]:
    """
    SMART ANALYSIS:
    1. Look for a 'Target Document' (Lawsuit).
    2. If found -> Run Litigation Engine (Target vs Context).
    3. If NOT found -> Run General Analysis (Context vs Context).
    """
    log = logger.bind(case_id=case_id)
    
    try:
        case_oid = ObjectId(case_id)
        documents = list(db.documents.find({"case_id": {"$in": [case_oid, case_id]}}))
        
        # 1. Attempt Auto-Targeting
        target_doc = _find_adversarial_target(documents)
        
        if target_doc:
            log.info("analysis.auto_target_found", target_id=str(target_doc["_id"]))
            
            # Fetch Target Text (Full)
            key = target_doc.get("processed_text_storage_key")
            target_text = ""
            
            # PHOENIX FIX: Correct Storage API Call
            if key:
                raw_bytes = storage_service.download_processed_text(key)
                if raw_bytes:
                    target_text = raw_bytes.decode('utf-8', errors='ignore')
            
            if target_text and len(target_text) > 100:
                # Prepare Context (Summaries of OTHER docs)
                other_docs = [d for d in documents if str(d["_id"]) != str(target_doc["_id"])]
                context_summaries = [f"[{d.get('file_name')}]: {d.get('summary', 'Ska përmbledhje')}" for d in other_docs]
                
                # Run The Engine
                result = llm_service.perform_litigation_cross_examination(target_text, context_summaries)
                
                # CRITICAL: Attach the ID so Frontend enables the "Draft" button
                result["target_document_id"] = str(target_doc["_id"])
                return result

        # 2. Fallback: GENERAL SUMMARY MODE
        log.info("analysis.general_mode")
        full_case_text = _get_full_case_text(db, case_id)
        
        graph_evidence = ""
        try:
            graph_contradictions = graph_service.find_contradictions(case_id)
            if graph_contradictions and "No direct" not in graph_contradictions:
                graph_evidence = f"--- INTELIGJENCA NGA GRAFI ---\n{graph_contradictions}\n\n"
        except Exception: pass

        total_context = graph_evidence + full_case_text
        if not total_context or len(total_context) < 50:
            return {"summary_analysis": "Nuk ka mjaftueshëm të dhëna për analizë."}
        
        return llm_service.analyze_case_contradictions(total_context)

    except Exception as e:
        log.error("analysis.failed", error=str(e))
        return {"error": "Analiza dështoi."}