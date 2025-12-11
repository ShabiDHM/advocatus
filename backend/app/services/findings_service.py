# FILE: backend/app/services/findings_service.py
# PHOENIX PROTOCOL - FINDINGS SERVICE V6.1 (TYPE SAFE RAG)
# 1. FIX: Sanitizes ObjectId -> String before sending to Vector Store (Prevents ChromaDB Crash).
# 2. SAFETY: Wraps Vector Sync in try/except to protect MongoDB extraction data.
# 3. LOGIC: Ensures Findings are available for both UI (Mongo) and Chat (RAG).

import structlog
from bson import ObjectId
from typing import List, Dict, Any
from pymongo.database import Database
from datetime import datetime, timezone

from app.services.llm_service import extract_findings_from_text
from app.services import vector_store_service

logger = structlog.get_logger(__name__)

def extract_and_save_findings(db: Database, document_id: str, full_text: str):
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

    if not document: return
    if not full_text or len(full_text.strip()) < 10: return
    
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
    
    # 3. PREPARE DATA
    for finding in extracted_findings:
        f_text = finding.get("finding_text") or finding.get("finding")
        s_text = finding.get("source_text") or finding.get("quote") or "N/A"
        category = finding.get("category", "GENERAL")
        
        if f_text:
            findings_to_insert.append({
                "case_id": case_id, # Keep as ObjectId for MongoDB
                "document_id": doc_oid,
                "document_name": file_name,
                "finding_text": f_text,
                "source_text": s_text,
                "category": category,
                "page_number": finding.get("page_number", 1),
                "confidence_score": 1.0, 
                "created_at": datetime.now(timezone.utc)
            })
    
    if findings_to_insert:
        # 4. SAVE TO MONGODB (UI Layer)
        # Clear old findings for this doc first to prevent duplicates
        db.findings.delete_many({"document_id": doc_oid})
        db.findings.insert_many(findings_to_insert)
        log.info("findings.saved_to_mongo", count=len(findings_to_insert))
        
        # 5. SAVE TO VECTOR DB (Chat/RAG Layer)
        # PHOENIX FIX: Sanitize types (ObjectId -> str) for ChromaDB
        try:
            vector_payload = []
            for f in findings_to_insert:
                # Create a copy to avoid modifying the MongoDB objects in memory if referenced elsewhere
                clean_f = f.copy()
                clean_f["case_id"] = str(f["case_id"])
                clean_f["document_id"] = str(f["document_id"])
                # Remove datetime objects if vector store doesn't support them, or convert to isoformat
                if isinstance(clean_f.get("created_at"), datetime):
                    clean_f["created_at"] = clean_f["created_at"].isoformat()
                vector_payload.append(clean_f)

            vector_store_service.store_structured_findings(vector_payload)
            log.info("findings.synced_to_vector_store")
        except Exception as e:
            # Critical: Don't crash the task if Vector DB is down, just log it.
            # The UI will still show the findings.
            log.error("findings.vector_sync_failed", error=str(e))

def get_findings_for_case(db: Database, case_id: str) -> List[Dict[str, Any]]:
    try: 
        case_object_id = ObjectId(case_id)
    except: 
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