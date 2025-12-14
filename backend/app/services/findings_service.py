# FILE: backend/app/services/findings_service.py
# PHOENIX PROTOCOL - FINDINGS SERVICE V8.0 (JANITOR & SYNTHESIS)
# 1. NEW: 'consolidate_case_findings' triggers the LLM Synthesizer.
# 2. LOGIC: Replaces messy findings with clean, synthesized ones.
# 3. STATUS: Full deduplication enabled.

import structlog
from bson import ObjectId
from typing import List, Dict, Any, Optional
from pymongo.database import Database
from datetime import datetime, timezone

from app.services.llm_service import extract_findings_from_text, synthesize_and_deduplicate_findings
from app.services import vector_store_service

logger = structlog.get_logger(__name__)

def _is_high_quality_finding(finding: Dict[str, Any]) -> bool:
    """
    Quality Gate: Filters out noise, hallucinations, or empty data.
    """
    text = finding.get("finding_text") or finding.get("finding")
    if not text or not isinstance(text, str):
        return False
    
    clean_text = text.strip()
    
    # Rule 1: Too short (likely noise)
    if len(clean_text) < 15:
        return False
        
    # Rule 2: Generic LLM refusals or descriptions
    noise_triggers = [
        "cannot extract", "nuk mund të", "unknown document", 
        "this document is", "ky dokument është", "nuk ka informacion"
    ]
    if any(trigger in clean_text.lower() for trigger in noise_triggers):
        return False

    return True

def extract_and_save_findings(db: Database, document_id: str, full_text: str) -> None:
    log = logger.bind(document_id=document_id)
    
    # 1. Fetch Document Info
    try:
        if not ObjectId.is_valid(document_id):
            return
        doc_oid = ObjectId(document_id)
        document = db.documents.find_one({"_id": doc_oid})
    except Exception as e:
        log.error("findings.db_lookup_failed", error=str(e))
        return

    if not document:
        return
    
    # Optimization: Don't process tiny snippets
    if not full_text or len(full_text.strip()) < 50: 
        return
    
    # 2. EXTRACT FINDINGS (AI)
    try:
        extracted_findings = extract_findings_from_text(full_text)
    except Exception as e:
        log.error("findings.llm_extraction_failed", error=str(e))
        return
    
    if not extracted_findings:
        log.info("findings.no_findings_found")
        return

    case_id = document.get("case_id")
    file_name = document.get("file_name", "Unknown Document")
    
    findings_to_insert = []
    
    # PHOENIX FIX: DEDUPLICATION SET
    seen_fingerprints = set()
    
    # 3. PREPARE DATA (With Quality Control & Deduplication)
    for finding in extracted_findings:
        if not _is_high_quality_finding(finding):
            continue

        # STRICT TYPE CASTING
        val = finding.get("finding_text") or finding.get("finding")
        if val is None:
            continue
            
        f_text = str(val)
        if not f_text:
            continue

        # Create a normalized fingerprint (lowercase, no extra spaces)
        fingerprint = f_text.strip().lower()
        
        # DEDUPLICATION CHECK
        if not fingerprint or fingerprint in seen_fingerprints:
            continue
        
        # Add to set so we don't add it again
        seen_fingerprints.add(fingerprint)

        s_text_val = finding.get("source_text") or finding.get("quote")
        s_text = str(s_text_val) if s_text_val is not None else "N/A"
        
        category_val = finding.get("category", "FAKT")
        category = str(category_val).upper() if category_val else "FAKT"
        
        findings_to_insert.append({
            "case_id": case_id, 
            "document_id": doc_oid,
            "document_name": file_name,
            "finding_text": f_text, # Keep original casing for display
            "source_text": s_text,
            "category": category,
            "page_number": finding.get("page_number", 1),
            "confidence_score": 1.0, 
            "created_at": datetime.now(timezone.utc)
        })
    
    if findings_to_insert:
        # 4. SAVE TO MONGODB (UI Layer)
        # Clear old findings for this doc first to prevent duplicates/ghosts
        db.findings.delete_many({"document_id": doc_oid})
        db.findings.insert_many(findings_to_insert)
        log.info("findings.saved_to_mongo", count=len(findings_to_insert))
        
        # 5. SAVE TO VECTOR DB (Chat/RAG Layer)
        try:
            vector_payload = []
            for f in findings_to_insert:
                clean_f = f.copy()
                clean_f["case_id"] = str(f["case_id"])
                clean_f["document_id"] = str(f["document_id"])
                
                # Sanitize Datetime for JSON/Vector serialization
                if isinstance(clean_f.get("created_at"), datetime):
                    clean_f["created_at"] = clean_f["created_at"].isoformat()
                
                vector_payload.append(clean_f)

            vector_store_service.store_structured_findings(vector_payload)
            log.info("findings.synced_to_vector_store")
        except Exception as e:
            # Critical: Don't crash the task if Vector DB is down, just log it.
            log.error("findings.vector_sync_failed", error=str(e))
    else:
        log.info("findings.quality_filter_rejected_all")

# --- NEW: THE SYNTHESIZER ---
def consolidate_case_findings(db: Database, case_id: str) -> None:
    """
    The Janitor Function.
    1. Grabs ALL findings for a case.
    2. Sends them to LLM for merging/deduplication.
    3. Replaces the DB records with the clean list.
    """
    try:
        case_oid = ObjectId(case_id)
        raw_findings = list(db.findings.find({"case_id": case_oid}))
        
        # Only run if we have enough data to be messy (e.g., > 5 findings)
        if len(raw_findings) < 5:
            return

        # Prepare text for LLM
        findings_text_list = []
        for f in raw_findings:
            doc_name = f.get("document_name", "Unknown")
            text = f.get("finding_text", "")
            findings_text_list.append(f"Fakti: {text} (Burimi: {doc_name})")

        # Run Synthesis
        clean_data = synthesize_and_deduplicate_findings(findings_text_list)
        
        if not clean_data:
            return

        # Convert to DB objects
        new_findings = []
        for item in clean_data:
            sources = ", ".join(item.get("source_documents", []))
            # Type safety for values
            finding_text = item.get("finding_text") or "N/A"
            category = item.get("category", "SINTEZË")
            
            new_findings.append({
                "case_id": case_oid,
                "document_id": None, # Consolidated -> No single doc ID
                "document_name": sources, # Multiple sources
                "finding_text": finding_text,
                "source_text": "Sintezë nga Inteligjenca Artificiale",
                "category": category,
                "page_number": 1,
                "confidence_score": 1.0,
                "created_at": datetime.now(timezone.utc)
            })

        # ATOMIC SWAP: Delete old -> Insert New
        # Warning: This removes per-document granularity in the "All Findings" view,
        # but provides the clean "Case View" the user demands.
        db.findings.delete_many({"case_id": case_oid})
        db.findings.insert_many(new_findings)
        logger.info("findings.consolidated", case_id=case_id, old_count=len(raw_findings), new_count=len(new_findings))

    except Exception as e:
        logger.error("findings.consolidation_failed", error=str(e))

def get_findings_for_case(db: Database, case_id: str) -> List[Dict[str, Any]]:
    try: 
        case_object_id = ObjectId(case_id)
    except Exception: 
        return []
        
    return list(db.findings.aggregate([
        {'$match': {'case_id': case_object_id}},
        {'$sort': {'created_at': -1}}
    ]))

def delete_findings_by_document_id(db: Database, document_id: ObjectId) -> List[ObjectId]:
    findings = list(db.findings.find({"document_id": document_id}, {"_id": 1}))
    ids = [f["_id"] for f in findings]
    if ids: 
        db.findings.delete_many({"_id": {"$in": ids}})
    return ids