# FILE: backend/app/services/analysis_service.py
# PHOENIX PROTOCOL - ANALYSIS SERVICE V10.5 (FORENSIC WIRING)
# 1. FIX: Connected to 'analyze_case_integrity' (The Auditor).
# 2. CITATION OPTIMIZATION: Context headers rewritten to force [Burimi: ...] compliance.
# 3. SAFETY: Preserves priority sorting to ensure "Judgments" are read first.

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
    Formats headers strictly for LLM Citation generation: [BURIMI: Filename]
    """
    try:
        case_oid = ObjectId(case_id)
        documents = list(db.documents.find({"case_id": {"$in": [case_oid, case_id]}}))
        
        # PHOENIX PRIORITY: Sort documents so AI sees the most important text first
        documents.sort(key=lambda x: _get_document_priority(x.get("file_name", "")))
        
        context_buffer = []
        for doc in documents:
            name = doc.get("file_name", "Dokument_Panjohur")
            doc_id = str(doc["_id"])
            
            # Retrieve available text layers
            summary = doc.get("summary", "")
            raw_text = doc.get("extracted_text", "")
            
            # --- CONTEXT BUILDER ---
            # We strictly format the header so the LLM can generate [Burimi: X] citations.
            
            findings = list(db.findings.find({"document_id": doc_id}))
            
            if findings:
                # Findings are high-density facts
                findings_text = "\n".join([f"- {f.get('finding_text', '')}" for f in findings])
                context_buffer.append(f"\n=== [BURIMI: {name} (Fakte të nxjerra)] ===\n{findings_text}\n")
            
            if raw_text and len(raw_text) > 50:
                # Raw text allows for Deep Reading and Page Citations
                # We limit to 5000 chars per doc to manage context window, but prioritize the start (header/dates)
                context_buffer.append(f"\n=== [BURIMI: {name} (Tekst Origjinal)] ===\n{raw_text[:5000]}\n")
            
            elif summary and len(summary) > 20:
                context_buffer.append(f"\n=== [BURIMI: {name} (Përmbledhje)] ===\n{summary}\n")

        return "\n".join(context_buffer)
    except Exception as e:
        logger.error("analysis.context_build_failed", error=str(e))
        return ""

def _find_adversarial_target(documents: List[Dict]) -> Optional[Dict]:
    """
    Scans documents to find the primary legal attack (Lawsuit/Complaint) for Cross-Examination.
    """
    keywords = ["padi", "kerkese", "kërkesë", "aktakuz", "ankes", "lawsuit", "complaint"]
    
    for doc in documents:
        fname = doc.get("file_name", "").lower()
        if any(k in fname for k in keywords):
            return doc
    return None

def cross_examine_case(db: Database, case_id: str) -> Dict[str, Any]:
    """
    The Central Intelligence Logic.
    Mode 1: Targeted Cross-Examination (if a specific Target Document exists).
    Mode 2: General Case Integrity Audit (Full Case Scan).
    """
    log = logger.bind(case_id=case_id)
    
    try:
        case_oid = ObjectId(case_id)
        documents = list(db.documents.find({"case_id": {"$in": [case_oid, case_id]}}))
        
        # 1. ATTEMPT AUTO-TARGETING (Cross-Examination Mode)
        # Useful if we want to cross-examine the main lawsuit against other evidence.
        target_doc = _find_adversarial_target(documents)
        
        if target_doc:
            log.info("analysis.auto_target_found", target_id=str(target_doc["_id"]))
            
            # Fetch highest fidelity text available
            key = target_doc.get("processed_text_storage_key")
            target_text = ""
            
            if key:
                try:
                    raw_bytes = storage_service.download_processed_text(key)
                    if raw_bytes:
                        target_text = raw_bytes.decode('utf-8', errors='ignore')
                except Exception: pass

            if not target_text or len(target_text) < 100:
                target_text = target_doc.get("extracted_text", "")
                if not target_text:
                    target_text = target_doc.get("summary", "")
            
            # Bad Data Check
            if not target_text or "Gabim gjatë leximit" in target_text or len(target_text) < 50:
                log.warning("analysis.target_text_corrupt", doc_name=target_doc.get("file_name"))
                target_doc = None 
            else:
                # Prepare Context for Comparison
                other_docs = [d for d in documents if str(d["_id"]) != str(target_doc["_id"])]
                other_docs.sort(key=lambda x: _get_document_priority(x.get("file_name", "")))
                
                context_summaries = [f"[{d.get('file_name')}]: {d.get('summary', 'Ska përmbledhje')}" for d in other_docs]
                
                # EXECUTE CROSS-EXAMINATION
                result = llm_service.perform_litigation_cross_examination(target_text, context_summaries)
                result["target_document_id"] = str(target_doc["_id"])
                
                # Ensure the 'mode' is clear for the frontend
                result["analysis_mode"] = "CROSS_EXAMINATION"
                return result

        # 2. FALLBACK: GENERAL CASE INTEGRITY AUDIT (The "Auditor")
        log.info("analysis.general_mode_integrity_check")
        full_case_text = _get_full_case_text(db, case_id)
        
        if not full_case_text or len(full_case_text) < 50:
            return {
                "summary_analysis": "Analiza nuk mund të kryhet sepse dokumentet nuk kanë tekst të lexueshëm. Ju lutem kontrolloni cilësinë e skanimeve.",
                "missing_info": ["Teksti i dokumenteve është i pakuptueshëm ose bosh."]
            }
        
        # PHOENIX CALL: Use the new Integrity Checker
        result = llm_service.analyze_case_integrity(full_case_text)
        result["analysis_mode"] = "FULL_CASE_AUDIT"
        return result

    except Exception as e:
        log.error("analysis.failed", error=str(e))
        return {"error": "Analiza dështoi për shkak të një problemi teknik."}