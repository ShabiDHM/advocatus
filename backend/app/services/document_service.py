# FILE: backend/app/services/document_service.py
# PHOENIX PROTOCOL - DOCUMENT SERVICE V6.6 (AGGRESSIVE CASCADE CLEANUP)
# 1. FIXED: Implements ruthless deletion logic for Calendar Events using Mixed-Type queries.
# 2. ADDED: Granular logging to confirm exactly how many events are wiped on delete.
# 3. ROBUSTNESS: Isolated try/except blocks ensure Calendar cleanup runs even if S3/Vector fails.

import logging
import datetime
import importlib
from datetime import timezone
from typing import List, Optional, Tuple, Any, Dict
from bson import ObjectId
import redis
from fastapi import HTTPException
from pymongo.database import Database

from ..models.document import DocumentOut, DocumentStatus
from ..models.user import UserInDB

# Only essential services
from . import vector_store_service, storage_service

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
    MASTER DELETE FUNCTION
    Removes: DB Record, S3 Files, Findings, Vector Embeddings, Calendar Events, Graph Nodes.
    Robust against failures in individual subsystems.
    """
    # Verify ownership before deletion attempts
    document_to_delete = db.documents.find_one({"_id": doc_id, "owner_id": owner.id})
    if not document_to_delete:
        raise HTTPException(status_code=404, detail="Document not found.")
    
    doc_id_str = str(doc_id)
    storage_key = document_to_delete.get("storage_key")
    processed_key = document_to_delete.get("processed_text_storage_key")
    preview_key = document_to_delete.get("preview_storage_key")

    # Mixed Query handles both ObjectId and String formats in related collections
    mixed_id_query = {"$in": [doc_id, doc_id_str]}
    
    deleted_finding_ids = []
    
    # 1. DELETE FINDINGS
    try:
        findings_query = {"document_id": mixed_id_query}
        findings_cursor = db.findings.find(findings_query, {"_id": 1})
        deleted_finding_ids = [str(f["_id"]) for f in findings_cursor]
        
        delete_result = db.findings.delete_many(findings_query)
        logger.info(f"Cascading delete: Removed {delete_result.deleted_count} findings for doc {doc_id}")
    except Exception as e:
        logger.error(f"Error deleting findings for doc {doc_id}: {e}")
    
    # 2. DELETE CALENDAR EVENTS & ALERTS (PHOENIX FOCUS)
    # This matches document_id (string) AND document_id (ObjectId) AND camelCase documentId
    link_query = {
        "$or": [
            {"document_id": mixed_id_query},
            {"documentId": mixed_id_query}
        ]
    }
    
    try:
        events_result = db.calendar_events.delete_many(link_query)
        logger.info(f"Cascading delete: Removed {events_result.deleted_count} calendar events for doc {doc_id}")
        
        if "alerts" in db.list_collection_names():
            alerts_result = db.alerts.delete_many(link_query)
            logger.info(f"Cascading delete: Removed {alerts_result.deleted_count} alerts for doc {doc_id}")
    except Exception as e:
        logger.error(f"Error deleting events/alerts for doc {doc_id}: {e}")

    # 3. DELETE GRAPH NODES
    try:
        graph_service_module = importlib.import_module("app.services.graph_service")
        if hasattr(graph_service_module, "graph_service"):
            graph_service_module.graph_service.delete_document_nodes(doc_id_str)
    except Exception as e:
        logger.warning(f"Graph cleanup failed (non-critical): {e}")

    # 4. DELETE VECTOR EMBEDDINGS (AI Memory)
    try:
        vector_store_service.delete_document_embeddings(
            user_id=str(owner.id),
            document_id=doc_id_str
        )
    except Exception as e:
        logger.error(f"Vector store cleanup failed: {e}")
    
    # 5. DELETE S3 FILES
    try:
        if storage_key: storage_service.delete_file(storage_key=storage_key)
        if processed_key: storage_service.delete_file(storage_key=processed_key)
        if preview_key: storage_service.delete_file(storage_key=preview_key)
    except Exception as e:
        logger.error(f"S3 cleanup failed (non-critical): {e}")
    
    # 6. DELETE DOCUMENT RECORD (Final Step)
    db.documents.delete_one({"_id": doc_id})
    logger.info(f"Document record {doc_id} deleted successfully.")
    
    return deleted_finding_ids

def bulk_delete_documents(db: Database, redis_client: redis.Redis, document_ids: List[str], owner: UserInDB) -> Dict[str, Any]:
    deleted_count = 0
    failed_count = 0
    all_deleted_finding_ids = []

    for doc_id_str in document_ids:
        try:
            if not ObjectId.is_valid(doc_id_str):
                continue
            
            doc_oid = ObjectId(doc_id_str)
            # Re-use the safe delete logic
            finding_ids = delete_document_by_id(db, redis_client, doc_oid, owner)
            all_deleted_finding_ids.extend(finding_ids)
            deleted_count += 1
        except Exception as e:
            logger.error(f"Bulk delete failed for {doc_id_str}: {e}")
            failed_count += 1
            
    return {
        "success": True,
        "deleted_count": deleted_count,
        "failed_count": failed_count,
        "deleted_finding_ids": all_deleted_finding_ids
    }