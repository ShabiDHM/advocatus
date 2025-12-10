# FILE: backend/app/services/findings_service.py
# PHOENIX PROTOCOL - FINDINGS SERVICE V6.0 (SYNC TO VECTOR DB)
# 1. FIX: Now pushes extracted findings to ChromaDB immediately.
# 2. RESULT: Chat and Drafting can now "see" the findings via RAG.

import structlog
from bson import ObjectId
from typing import List, Dict, Any
from pymongo.database import Database
from pymongo.results import DeleteResult
from datetime import datetime, timezone

from app.services.llm_service import extract_findings_from_text
# PHOENIX: Import the vector store to enable sync
from app.services import vector_store_service

logger = structlog.get_logger(__name__)

def extract_and_save_findings(db: Database, document_id: str, full_text: str):
    log = logger.bind(document_id=document_id)
    
    document = db.documents.find_one({"_id": ObjectId(document_id)})
    if not document: return
    if not full_text or not full_text.strip(): return
    
    # 1. EXTRACT
    extracted_findings = extract_findings_from_text(full_text)
    
    if not extracted_findings:
        log.info("findings_service.no_findings_found_by_llm")
        return

    case_id = document.get("case_id")
    file_name = document.get("file_name", "Unknown Document")
    
    findings_to_insert = []
    for finding in extracted_findings:
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
        # 2. SAVE TO MONGODB (For UI)
        db.findings.delete_many({"document_id": ObjectId(document_id)})
        db.findings.insert_many(findings_to_insert)
        
        # 3. SAVE TO VECTOR DB (For Chat/RAG) - PHOENIX FIX
        vector_store_service.store_structured_findings(findings_to_insert)
        
        log.info("findings_service.extraction.completed", count=len(findings_to_insert))

def get_findings_for_case(db: Database, case_id: str) -> List[Dict[str, Any]]:
    try: case_object_id = ObjectId(case_id)
    except: return []
    return list(db.findings.aggregate([
        {'$match': {'case_id': case_object_id}},
        {'$sort': {'created_at': -1}}
    ]))

def delete_findings_by_document_id(db: Database, document_id: ObjectId) -> List[ObjectId]:
    findings = list(db.findings.find({"document_id": document_id}, {"_id": 1}))
    ids = [f["_id"] for f in findings]
    if ids: db.findings.delete_many({"_id": {"$in": ids}})
    return ids