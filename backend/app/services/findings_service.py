# FILE: backend/app/services/findings_service.py
# PHOENIX PROTOCOL - FINDINGS SERVICE V5 (UNIFIED PIPELINE)
# 1. ARCHITECTURE: Removed duplicate DeepSeek logic. Now delegates to 'llm_service'.
# 2. LOGIC: Centralized "Kosovo Forensic Audit" logic in one place.
# 3. FIX: Ensures extraction actually returns data to the DB.

import structlog
from bson import ObjectId
from typing import List, Dict, Any
from pymongo.database import Database
from pymongo.results import DeleteResult
from datetime import datetime, timezone

# PHOENIX: Import the centralized brain
from app.services.llm_service import extract_findings_from_text

logger = structlog.get_logger(__name__)

def extract_and_save_findings(db: Database, document_id: str, full_text: str):
    """
    Orchestrates the extraction of findings using the central LLM service
    and saves them to the MongoDB 'findings' collection.
    """
    log = logger.bind(document_id=document_id)
    log.info("findings_service.extraction.started", text_length=len(full_text))
    
    document = db.documents.find_one({"_id": ObjectId(document_id)})
    if not document:
        log.warning("findings_service.document_not_found")
        return
    
    if not full_text or not full_text.strip():
        log.warning("findings_service.no_text_provided")
        return
    
    # 1. DELEGATE TO LLM SERVICE (The "Brain")
    # This uses the robust, Kosovo-aware prompt we defined in llm_service.py
    extracted_findings = extract_findings_from_text(full_text)
    
    if not extracted_findings:
        log.info("findings_service.no_findings_found_by_llm")
        return

    case_id = document.get("case_id")
    file_name = document.get("file_name", "Unknown Document")
    
    findings_to_insert = []
    for finding in extracted_findings:
        # Normalize keys (just in case LLM varies slightly, though schema is strict)
        f_text = finding.get("finding_text") or finding.get("finding")
        s_text = finding.get("source_text") or finding.get("quote") or "N/A"
        category = finding.get("category", "GENERAL")
        
        if f_text:
            findings_to_insert.append({
                "case_id": case_id, 
                "document_id": ObjectId(document_id),
                "document_name": file_name,
                "finding_text": f_text,
                "source_text": s_text,
                "category": category,
                "page_number": finding.get("page_number", 1),
                "confidence_score": 1.0, 
                "created_at": datetime.now(timezone.utc)
            })
    
    if findings_to_insert:
        # Delete old findings for this document to avoid duplicates on re-scan
        db.findings.delete_many({"document_id": ObjectId(document_id)})
        
        db.findings.insert_many(findings_to_insert)
        log.info("findings_service.extraction.completed", findings_saved=len(findings_to_insert))
    else:
        log.info("findings_service.extraction.completed.no_valid_data")

def get_findings_for_case(db: Database, case_id: str) -> List[Dict[str, Any]]:
    try:
        case_object_id = ObjectId(case_id)
    except Exception:
        return []
        
    pipeline = [
        {'$match': {'case_id': case_object_id}},
        {'$sort': {'created_at': -1}}, 
        {'$project': {
            '_id': 1, 
            'case_id': 1, 
            'document_id': 1, 
            'finding_text': 1, 
            'source_text': 1,
            'category': 1,
            'page_number': 1, 
            'document_name': 1, 
            'confidence_score': 1,
            'created_at': 1 
        }}
    ]
    return list(db.findings.aggregate(pipeline))

def delete_findings_by_document_id(db: Database, document_id: ObjectId) -> List[ObjectId]:
    log = logger.bind(document_id=str(document_id))
    
    if not isinstance(document_id, ObjectId):
        log.error("findings_service.deletion.invalid_id_type")
        return []
        
    findings_to_delete = list(db.findings.find({"document_id": document_id}, {"_id": 1}))
    deleted_ids = [item["_id"] for item in findings_to_delete]

    if not deleted_ids:
        log.info("findings_service.deletion.no_findings_found")
        return []

    result: DeleteResult = db.findings.delete_many({"_id": {"$in": deleted_ids}})
    log.info("findings_service.deletion.completed", findings_deleted=result.deleted_count)
    
    return deleted_ids