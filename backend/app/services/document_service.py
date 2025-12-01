# FILE: backend/app/services/document_service.py
# PHOENIX PROTOCOL - DOCUMENT SERVICE (DIGITAL SHREDDER ENABLED)
# 1. FIX: Added explicit deletion of Calendar Events and Alerts linked to the document.
# 2. LOGIC: Handles both String and ObjectId formats for robust cleanup.
# 3. STATUS: Complete data wiping for deleted documents.

import logging
from bson import ObjectId
from typing import List, Optional, Tuple, Any
import datetime
from datetime import timezone
from pymongo.database import Database
import redis
from fastapi import HTTPException

from ..models.document import DocumentOut, DocumentStatus
from ..models.user import UserInDB

from . import vector_store_service, storage_service, findings_service, deadline_service
from .graph_service import graph_service 

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
    document_dicts = list(db.documents.find({"case_id": ObjectId(case_id), "owner_id": owner.id}).sort("created_at", -1))
    return [DocumentOut.model_validate(doc) for doc in document_dicts]

def get_and_verify_document(db: Database, doc_id: str, owner: UserInDB) -> DocumentOut:
    document_data = db.documents.find_one({"_id": ObjectId(doc_id), "owner_id": owner.id})
    if not document_data:
        raise HTTPException(status_code=404, detail="Document not found.")
    return DocumentOut.model_validate(document_data)

def get_preview_document_stream(db: Database, doc_id: str, owner: UserInDB) -> Tuple[Any, DocumentOut]:
    document = get_and_verify_document(db, doc_id, owner)
    if not document.preview_storage_key:
        raise FileNotFoundError("Document preview is not available.")
    try:
        file_stream = storage_service.download_preview_document_stream(document.preview_storage_key)
        if file_stream is None:
            raise FileNotFoundError("Preview file stream is None.")
        return file_stream, document
    except Exception as e:
        logger.error(f"Failed to download preview document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not retrieve the document preview.")

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
    document_to_delete = db.documents.find_one({"_id": doc_id, "owner_id": owner.id})
    if not document_to_delete:
        raise HTTPException(status_code=404, detail="Document not found.")
    
    doc_id_str = str(doc_id)
    storage_key = document_to_delete.get("storage_key")
    processed_key = document_to_delete.get("processed_text_storage_key")
    preview_key = document_to_delete.get("preview_storage_key")

    # 1. Delete Findings (via service to handle finding-specific logic)
    deleted_finding_ids = findings_service.delete_findings_by_document_id(db=db, document_id=doc_id)
    
    # 2. PHOENIX FIX: Robust Link Deletion (Calendar Events & Alerts)
    # Check for both ObjectId and String versions of ID to catch all references
    any_id_query = {"document_id": {"$in": [doc_id, doc_id_str]}}
    
    # Delete Calendar Events associated with this document
    db.calendar_events.delete_many(any_id_query)
    
    # Delete Alerts associated with this document
    db.alerts.delete_many(any_id_query)
    
    # 3. Clean Graph Nodes
    try:
        graph_service.delete_document_nodes(doc_id_str)
    except Exception as e:
        logger.warning(f"Failed to clean graph nodes for doc {doc_id_str}: {e}")

    # 4. Clean Vector Embeddings
    vector_store_service.delete_document_embeddings(document_id=doc_id_str)
    
    # 5. Clean Physical Files
    if storage_key: storage_service.delete_file(storage_key=storage_key)
    if processed_key: storage_service.delete_file(storage_key=processed_key)
    if preview_key: storage_service.delete_file(storage_key=preview_key)
    
    # 6. Delete the Document Record
    delete_result = db.documents.delete_one({"_id": doc_id, "owner_id": owner.id})
    
    if delete_result.deleted_count != 1:
        raise HTTPException(status_code=500, detail="Failed to delete document from database.")
    
    return [str(fid) for fid in deleted_finding_ids]