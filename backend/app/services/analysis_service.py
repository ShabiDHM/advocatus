# FILE: backend/app/services/analysis_service.py
# PHOENIX PROTOCOL - ANALYSIS SERVICE V10.4 (SMART CONTEXT PRIORITY)
# 1. LOGIC: Sorts documents by Legal Importance before sending to AI.
#    (Judgments/Lawsuits get priority over random evidence).
# 2. OPTIMIZATION: Ensures critical dates in main docs aren't truncated.
# 3. SAFETY: Maintains the Bad Data Filter.

import structlog
from typing import Dict, Any, List, Optional
from pymongo.database import Database
from bson import ObjectId

from . import llm_service
from .graph_service import graph_service
from . import storage_service 

logger = structlog.get_logger(__name__)

def _get_document_priority(doc_name: str) -> int:
    """
    Assigns priority score for context building. Lower is better/first.
    1. Judgments/Decisions (Official Facts)
    2. Lawsuits/Complaints (Core Claims)
    3. Evidence/Other
    """
    name = doc_name.lower()
    if "aktgjykim" in name or "vendim" in name or "aktvendim" in name:
        return 1
    if "padi" in name or "kërkesë" in name or "ankesë" in name or "kundërshtim" in name:
        return 2
    if "procesverbal" in name:
        return 3
    return 4

def _get_full_case_text(db: Database, case_id: str) -> str:
    """
    Aggregates all available text for a case, SORTED BY IMPORTANCE.
    """
    try:
        case_oid = ObjectId(case_id)
        documents = list(db.documents.find({"case_id": {"$in": [case_oid, case_id]}}))
        
        # PHOENIX FIX: Sort documents so AI sees the most important text first
        # This prevents the "Chronology" from missing key dates if the text is truncated.
        documents.sort(key=lambda x: _get_document_priority(x.get("file_name", "")))
        
        context_buffer = []
        for doc in documents:
            name = doc.get("file_name", "Unknown Document")
            doc_id = str(doc["_id"])
            
            # Quality check on summary/text
            summary = doc.get("summary", "")
            raw_text = doc.get("extracted_text", "")
            
            # Prefer findings -> summary -> raw text
            findings = list(db.findings.find({"document_id": doc_id}))
            
            if findings:
                # Findings are usually high-density facts
                findings_text = "\n".join([f"- {f.get('finding_text', '')}" for f in findings])
                context_buffer.append(f"--- DOKUMENTI PRIORITAR: {name} (Fakte) ---\n{findings_text}\n\n")
            elif raw_text and len(raw_text) > 50:
                # Raw text is better for detailed extraction if findings miss something
                # We limit per document to ensure variety in the context window
                context_buffer.append(f"--- DOKUMENTI: {name} (Tekst) ---\n{raw_text[:4000]}\n\n")
            elif summary and len(summary) > 20:
                context_buffer.append(f"--- DOKUMENTI: {name} (Përmbledhje) ---\n{summary}\n\n")

        return "".join(context_buffer)
    except Exception as e:
        logger.error("analysis.context_build_failed", error=str(e))
        return ""

def _find_adversarial_target(documents: List[Dict]) -> Optional[Dict]:
    """
    Scans documents to find the primary legal attack (Lawsuit/Complaint).
    """
    keywords = ["padi", "kerkese", "kërkesë", "aktakuz", "ankes", "lawsuit", "complaint"]
    
    # Sort by name length or other metric if needed, currently priority by keyword presence
    for doc in documents:
        fname = doc.get("file_name", "").lower()
        if any(k in fname for k in keywords):
            return doc
    return None

def cross_examine_case(db: Database, case_id: str) -> Dict[str, Any]:
    log = logger.bind(case_id=case_id)
    
    try:
        case_oid = ObjectId(case_id)
        documents = list(db.documents.find({"case_id": {"$in": [case_oid, case_id]}}))
        
        # 1. Attempt Auto-Targeting
        target_doc = _find_adversarial_target(documents)
        
        if target_doc:
            log.info("analysis.auto_target_found", target_id=str(target_doc["_id"]))
            
            key = target_doc.get("processed_text_storage_key")
            target_text = ""
            
            # Attempt 1: Full Processed Text
            if key:
                try:
                    raw_bytes = storage_service.download_processed_text(key)
                    if raw_bytes:
                        target_text = raw_bytes.decode('utf-8', errors='ignore')
                except Exception: pass

            # Attempt 2: Fallback to Database Raw Text or Summary
            if not target_text or len(target_text) < 100:
                target_text = target_doc.get("extracted_text", "")
                if not target_text:
                    target_text = target_doc.get("summary", "")
            
            # --- BAD DATA FILTER ---
            if not target_text or "Gabim gjatë leximit" in target_text or len(target_text) < 50:
                log.warning("analysis.target_text_corrupt", doc_name=target_doc.get("file_name"))
                target_doc = None 
            else:
                # Prepare Context with Prioritization
                other_docs = [d for d in documents if str(d["_id"]) != str(target_doc["_id"])]
                other_docs.sort(key=lambda x: _get_document_priority(x.get("file_name", "")))
                
                context_summaries = [f"[{d.get('file_name')}]: {d.get('summary', 'Ska përmbledhje')}" for d in other_docs]
                
                result = llm_service.perform_litigation_cross_examination(target_text, context_summaries)
                result["target_document_id"] = str(target_doc["_id"])
                return result

        # 2. Fallback: GENERAL SUMMARY MODE
        log.info("analysis.general_mode")
        full_case_text = _get_full_case_text(db, case_id)
        
        if not full_case_text or len(full_case_text) < 50:
            return {
                "summary_analysis": "Analiza nuk mund të kryhet sepse dokumentet nuk kanë tekst të lexueshëm. Provoni të ngarkoni dokumente më cilësore (PDF origjinale ose foto të qarta).",
                "missing_info": ["Teksti i dokumenteve është i pakuptueshëm ose bosh."]
            }
        
        return llm_service.analyze_case_contradictions(full_case_text)

    except Exception as e:
        log.error("analysis.failed", error=str(e))
        return {"error": "Analiza dështoi."}