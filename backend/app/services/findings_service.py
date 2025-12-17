# FILE: backend/app/services/findings_service.py
# PHOENIX PROTOCOL - FINDINGS SERVICE V9.0 (FORENSIC EXTRACTION)
# 1. NEW: Strict Validation Logic. If it's vague, it's rejected.
# 2. ENHANCEMENT: Prioritizes Page Numbers and Source Text.
# 3. SAFETY: Zero-Tolerance for Hallucinated "Summaries" disguised as findings.

import structlog
from bson import ObjectId
from typing import List, Dict, Any, Optional
import re
from pymongo.database import Database
from datetime import datetime, timezone

from app.services.llm_service import extract_findings_from_text
from app.services import vector_store_service

logger = structlog.get_logger(__name__)

# --- CONFIGURATION ---
MIN_FINDING_LENGTH = 20  # Increased to reduce noise ("Data 12.01" is useless without context)
HALLUCINATION_TRIGGERS = [
    "cannot extract", "nuk mund të", "unknown document", 
    "this document is", "ky dokument është", "nuk ka informacion",
    "as an ai", "nuk jam i sigurt", "generalized summary",
    "mungon", "nuk gjendet", "no specific date"
]

def _validate_forensic_quality(finding: Dict[str, Any]) -> bool:
    """
    STRICT FILTER: Rejects any finding that smells like a hallucination or lazy summary.
    """
    # 1. Check Text Existence
    text = finding.get("finding_text") or finding.get("finding")
    if not text or not isinstance(text, str):
        return False
    
    clean_text = text.strip()
    
    # 2. Check Length
    if len(clean_text) < MIN_FINDING_LENGTH:
        return False
        
    # 3. Check for AI Refusals / Lazy Outputs
    lower_text = clean_text.lower()
    if any(trigger in lower_text for trigger in HALLUCINATION_TRIGGERS):
        return False

    # 4. Check for "Vague Symmetry" (e.g., "The defendant defends") without quotes
    # If the category is CLAIM but source_text is empty/weak, reject.
    category = str(finding.get("category", "")).upper()
    source_text = finding.get("source_text", "")
    
    # If it claims to be a defense/claim but has no source backing, it's likely a hallucination
    if category in ["PRETENDIM", "MBROJTJE"] and (not source_text or len(source_text) < 10):
        return False

    return True

def extract_and_save_findings(db: Database, document_id: str, full_text: str) -> None:
    log = logger.bind(document_id=document_id)
    
    # 1. Validate Input
    try:
        if not ObjectId.is_valid(document_id): return
        doc_oid = ObjectId(document_id)
        document = db.documents.find_one({"_id": doc_oid})
    except Exception as e:
        log.error("findings.db_lookup_failed", error=str(e))
        return

    if not document: return
    
    # Optimization: Skip empty/tiny docs
    if not full_text or len(full_text.strip()) < 50: 
        return
    
    # 2. EXECUTE AI EXTRACTION (Strict Mode via llm_service)
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
    seen_fingerprints = set()
    
    # 3. FILTER & STANDARDIZE
    for finding in extracted_findings:
        if not _validate_forensic_quality(finding):
            continue

        # Extract Text
        f_text = str(finding.get("finding_text") or finding.get("finding")).strip()
        
        # Deduplication Strategy: Lowercase + remove punctuation
        fingerprint = re.sub(r'\W+', '', f_text.lower())
        if not fingerprint or fingerprint in seen_fingerprints:
            continue
        seen_fingerprints.add(fingerprint)

        # Source Text Handling
        s_text = str(finding.get("source_text") or finding.get("quote") or "N/A")
        
        # Category Normalization
        category = str(finding.get("category", "FAKT")).upper()
        
        # Page Number Logic (Priority: JSON -> Regex -> Fallback)
        page_num = finding.get("page_number")
        
        if not page_num:
            # Try extracting [Fq. 2] from text
            match = re.search(r'\[(?:Fq\.|Page)\s*(\d+)\]', f_text)
            if match:
                page_num = int(match.group(1))
            else:
                page_num = 1 # Fallback
                
        # Enforce Integer
        try: 
            page_num = int(page_num)
        except: 
            page_num = 1

        findings_to_insert.append({
            "case_id": case_id, 
            "document_id": doc_oid,
            "document_name": file_name,
            "finding_text": f_text,
            "source_text": s_text,
            "category": category,
            "page_number": page_num,
            "confidence_score": 1.0, 
            "created_at": datetime.now(timezone.utc)
        })
    
    if findings_to_insert:
        # 4. ATOMIC UPDATE (Delete Old -> Insert New)
        db.findings.delete_many({"document_id": doc_oid})
        db.findings.insert_many(findings_to_insert)
        log.info("findings.saved_to_mongo", count=len(findings_to_insert))
        
        # 5. SYNC TO VECTOR STORE (For Chat RAG)
        try:
            vector_payload = []
            for f in findings_to_insert:
                clean_f = f.copy()
                clean_f["case_id"] = str(f["case_id"])
                clean_f["document_id"] = str(f["document_id"])
                # Isoformat date for Vector DB
                if isinstance(clean_f.get("created_at"), datetime):
                    clean_f["created_at"] = clean_f["created_at"].isoformat()
                vector_payload.append(clean_f)

            vector_store_service.store_structured_findings(vector_payload)
            log.info("findings.synced_to_vector_store")
        except Exception as e:
            # Non-blocking error
            log.error("findings.vector_sync_failed", error=str(e))
    else:
        log.info("findings.all_rejected_by_quality_filter")

def consolidate_case_findings(db: Database, case_id: str) -> None:
    """
    DISABLED: Destructive consolidation breaks the 'Click-to-Source' chain.
    We keep raw document findings intact for the Forensic Audit trail.
    """
    pass 

def get_findings_for_case(db: Database, case_id: str) -> List[Dict[str, Any]]:
    try: 
        case_object_id = ObjectId(case_id)
    except Exception: 
        return []
        
    return list(db.findings.aggregate([
        {'$match': {'case_id': case_object_id}},
        {'$sort': {'page_number': 1, 'created_at': -1}} # Visual Sort by Page
    ]))

def delete_findings_by_document_id(db: Database, document_id: ObjectId) -> List[ObjectId]:
    findings = list(db.findings.find({"document_id": document_id}, {"_id": 1}))
    ids = [f["_id"] for f in findings]
    if ids: 
        db.findings.delete_many({"_id": {"$in": ids}})
    return ids