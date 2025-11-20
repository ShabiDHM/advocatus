# FILE: backend/app/services/findings_service.py
# PHOENIX PROTOCOL - ABSOLUTE IMPORT FIX
# 1. REPLACED: Relative import with absolute import 'from app.services.llm_service ...'
# 2. RESOLVES: Pylance "not a known attribute" error.
# 3. PRESERVED: Document ID deletion logic.

import structlog
from bson import ObjectId
from typing import List, Dict, Any
from pymongo.database import Database
from pymongo.results import DeleteResult

# PHOENIX FIX: Absolute import to guarantee symbol resolution
from app.services.llm_service import extract_findings_from_text

logger = structlog.get_logger(__name__)

def extract_and_save_findings(db: Database, document_id: str, full_text: str):
    log = logger.bind(document_id=document_id)
    log.info("findings_service.extraction.started", text_length=len(full_text))
    document = db.documents.find_one({"_id": ObjectId(document_id)})
    if not document:
        log.warning("findings_service.document_not_found")
        return
    if not full_text or not full_text.strip():
        log.warning("findings_service.no_text_provided")
        return
    
    # PHOENIX FIX: Call the directly imported function
    extracted_findings = extract_findings_from_text(full_text)
    
    if not extracted_findings:
        log.info("findings_service.no_findings_found")
        return
    case_id = document.get("case_id")
    file_name = document.get("file_name", "Unknown Document")
    log = log.bind(case_id=str(case_id))
    findings_to_insert = [
        {
            "case_id": case_id, "document_id": ObjectId(document_id),
            "document_name": file_name,
            "finding_text": finding.get("finding_text") or finding.get("finding") or "No finding text provided.",
            "source_text": finding.get("source_text") or "N/A",
            "page_number": finding.get("page_number", 1),
            "confidence_score": 1.0,
        }
        for finding in extracted_findings if finding.get("finding_text") or finding.get("finding")
    ]
    if findings_to_insert:
        db.findings.insert_many(findings_to_insert)
        log.info("findings_service.extraction.completed", findings_saved=len(findings_to_insert))
    else:
        log.info("findings_service.extraction.completed.no_valid_findings")

def get_findings_for_case(db: Database, case_id: str) -> List[Dict[str, Any]]:
    try:
        case_object_id = ObjectId(case_id)
    except Exception:
        return []
    pipeline = [
        {'$match': {'case_id': case_object_id}},
        {'$project': {
            '_id': 1, 
            'case_id': 1, 
            'document_id': 1, 
            'finding_text': 1, 
            'source_text': 1,
            'page_number': 1, 
            'document_name': 1, 
            'confidence_score': 1,
        }}
    ]
    findings = list(db.findings.aggregate(pipeline))
    return findings

def delete_findings_by_document_id(db: Database, document_id: ObjectId) -> List[ObjectId]:
    log = logger.bind(document_id=str(document_id))
    log.info("findings_service.deletion.started")
    if not isinstance(document_id, ObjectId):
        log.error("findings_service.deletion.invalid_id_type", type=type(document_id).__name__)
        return []
        
    findings_to_delete = list(db.findings.find({"document_id": document_id}, {"_id": 1}))
    deleted_ids = [item["_id"] for item in findings_to_delete]

    if not deleted_ids:
        log.info("findings_service.deletion.no_findings_found")
        return []

    result: DeleteResult = db.findings.delete_many({"_id": {"$in": deleted_ids}})
    deleted_count = result.deleted_count
    log.info("findings_service.deletion.completed", findings_deleted=deleted_count)
    
    return deleted_ids