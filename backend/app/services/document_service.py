# FILE: backend/app/services/document_service.py
# PHOENIX PROTOCOL - DOCUMENT SERVICE CORE V6.0 (CASCADING DELETE)
# 1. FIX: Implemented aggressive 'Cascading Delete' for all related data.
# 2. LOGIC: Cleans Findings, Calendar Events, Alerts, Graph Nodes, and Vector Store.
# 3. SAFETY: Uses mixed-type queries (ObjectId/String) to ensure no orphans remain.

import logging
import datetime
import importlib
from datetime import timezone
from typing import List, Optional, Tuple, Any
from bson import ObjectId
import redis
from fastapi import HTTPException
from pymongo.database import Database

from ..models.document import DocumentOut, DocumentStatus
from ..models.user import UserInDB

from . import vector_store_service, storage_service, findings_service

logger = logging.getLogger(__name__)

def create_document_record(
    db: Database, owner: UserInDB, case_id: str, file_name: str, storage_key: str, mime_type: str
) -> DocumentOut:
    try:
        case_object_id = ObjectId(case_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Case ID format.")

    document_data = {
        "owner_id": owner.id, "case_id": case_object_id, "file_name": file_name,
        "storage_key": storage_key, "mime_type": mime_type,
        "status": DocumentStatus.PENDING,
        "created_at": datetime.datetime.now(timezone.utc),
        "preview_storage_key": None,
    }
    insert_result = db.documents.insert_one(document_data)
    if not insert_result.inserted_id:
        raise HTTPException(status_code=500, detail="Failed to create document record.")
    
    new_doc = db.documents.find_one({"_id": insert_result.inserted_id})
    return DocumentOut.model_validate(new_doc)

def finalize_document_processing(
    db: Database, redis_client: redis.Redis, doc_id_str: str,
    processed_text_storage_key: Optional[str] = None, summary: Optional[str] = None,
    preview_storage_key: Optional[str] = None
):
    try:
        doc_object_id = ObjectId(doc_id_str)
    except Exception:
        logger.error(f"Invalid Document ID received for finalization: {doc_id_str}")
        return

    update_fields = {"status": DocumentStatus.READY, "processed_timestamp": datetime.datetime.now(timezone.utc)}
    if processed_text_storage_key:
        update_fields["processed_text_storage_key"] = processed_text_storage_key
    if summary:
        update_fields["summary"] = summary
    if preview_storage_key:
        update_fields["preview_storage_key"] = preview_storage_key
        
    db.documents.update_one({"_id": doc_object_id}, {"$set": update_fields})

def get_documents_by_case_id(db: Database, case_id: str, owner: UserInDB) -> List[DocumentOut]:
    try:
        # PHOENIX FIX: Sort by creation date descending
        documents_cursor = db.documents.find({"case_id": ObjectId(case_id), "owner_id": owner.id}).sort("created_at", -1)
        documents = list(documents_cursor)
        return [DocumentOut.model_validate(doc) for doc in documents]
    except Exception as e:
        logger.error(f"Failed to fetch documents for case {case_id}: {e}")
        return []

def get_and_verify_document(db: Database, doc_id: str, owner: UserInDB) -> DocumentOut:
    try:
        doc_oid = ObjectId(doc_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid Document ID.")
        
    document_data = db.documents.find_one({"_id": doc_oid, "owner_id": owner.id})
    if not document_data:
        raise HTTPException(status_code=404, detail="Document not found.")
    return DocumentOut.model_validate(document_data)

def get_preview_document_stream(db: Database, doc_id: str, owner: UserInDB) -> Tuple[Any, DocumentOut]:
    document = get_and_verify_document(db, doc_id, owner)
    
    if document.preview_storage_key:
        try:
            file_stream = storage_service.download_preview_document_stream(document.preview_storage_key)
            if file_stream:
                return file_stream, document
        except Exception:
            logger.warning(f"Preview key exists but fetch failed for {doc_id}, falling back to original.")

    if not document.storage_key:
        raise FileNotFoundError("Document content unavailable.")
        
    try:
        file_stream = storage_service.download_original_document_stream(document.storage_key)
        return file_stream, document
    except Exception as e:
        logger.error(f"Failed to download document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not retrieve the document.")

def get_original_document_stream(db: Database, doc_id: str, owner: UserInDB) -> Tuple[Any, DocumentOut]:
    document = get_and_verify_document(db, doc_id, owner)
    if not document.storage_key:
        raise HTTPException(status_code=404, detail="Original document file not found in storage.")
    try:
        file_stream = storage_service.download_original_document_stream(document.storage_key)
        if file_stream is None: raise FileNotFoundError
        return file_stream, document
    except Exception as e:
        logger.error(f"Failed to download original document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not retrieve the document file.")

def get_document_content_by_key(storage_key: str) -> Optional[str]:
    try:
        content_bytes = storage_service.download_processed_text(storage_key)
        return content_bytes.decode('utf-8') if content_bytes else None
    except Exception as e:
        logger.error(f"Failed to retrieve content: {e}", exc_info=True)
        return None

def delete_document_by_id(db: Database, redis_client: redis.Redis, doc_id: ObjectId, owner: UserInDB) -> List[str]:
    """
    Deletes a document and CASCADES the delete to all related entities:
    - Findings
    - Calendar Events / Alerts
    - Graph Nodes
    - Vector Embeddings
    - Physical Files
    """
    document_to_delete = db.documents.find_one({"_id": doc_id, "owner_id": owner.id})
    if not document_to_delete:
        raise HTTPException(status_code=404, detail="Document not found.")
    
    doc_id_str = str(doc_id)
    storage_key = document_to_delete.get("storage_key")
    processed_key = document_to_delete.get("processed_text_storage_key")
    preview_key = document_to_delete.get("preview_storage_key")

    # PHOENIX STRATEGY: Aggressive Cleanup Query (Mixed Types)
    # We match both ObjectId and String versions of the ID to be 100% sure.
    mixed_id_query = {"$in": [doc_id, doc_id_str]}
    
    # 1. Delete Findings (Direct DB call to ensure mixed-type coverage)
    # Note: findings_service might only check ObjectId, so we do it explicitly here too.
    try:
        findings_query = {"document_id": mixed_id_query}
        deleted_findings = list(db.findings.find(findings_query, {"_id": 1}))
        db.findings.delete_many(findings_query)
        deleted_finding_ids = [str(f["_id"]) for f in deleted_findings]
    except Exception as e:
        logger.error(f"Error deleting findings for doc {doc_id}: {e}")
        deleted_finding_ids = []
    
    # 2. Cleanup Calendar Events & Alerts
    # Check for both 'document_id' (snake) and 'documentId' (camel) just in case
    link_query = {
        "$or": [
            {"document_id": mixed_id_query},
            {"documentId": mixed_id_query}
        ]
    }
    
    try:
        db.calendar_events.delete_many(link_query)
        # Also clean specific 'alerts' collection if it exists
        if "alerts" in db.list_collection_names():
            db.alerts.delete_many(link_query)
    except Exception as e:
        logger.error(f"Error deleting events/alerts for doc {doc_id}: {e}")

    # 3. Clean Graph
    # Import here to avoid circular dependency risks
    try:
        graph_service_module = importlib.import_module("app.services.graph_service")
        if hasattr(graph_service_module, "graph_service"):
            graph_service_module.graph_service.delete_document_nodes(doc_id_str)
    except Exception as e:
        logger.warning(f"Graph cleanup failed (non-critical): {e}")

    # 4. Clean Vector Store
    try:
        vector_store_service.delete_document_embeddings(document_id=doc_id_str)
    except Exception as e:
        logger.error(f"Vector store cleanup failed: {e}")
    
    # 5. Clean Physical Files
    # We wrap these individually so one failure doesn't stop the DB delete
    if storage_key: 
        try: storage_service.delete_file(storage_key=storage_key)
        except: pass
    if processed_key: 
        try: storage_service.delete_file(storage_key=processed_key)
        except: pass
    if preview_key: 
        try: storage_service.delete_file(storage_key=preview_key)
        except: pass
    
    # 6. Delete The Document Record
    db.documents.delete_one({"_id": doc_id})
    
    return deleted_finding_ids