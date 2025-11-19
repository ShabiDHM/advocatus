# FILE: backend/app/services/document_service.py
# PHOENIX PROTOCOL - CLEANED VERSION
# 1. Removed legacy HTTP Broadcast (trigger_websocket_broadcast) to fix 404 errors.
# 2. State updates are now handled exclusively via Redis/SSE in the Task layer.

import logging
from bson import ObjectId
from typing import List, Optional, Tuple, Any
import datetime
from datetime import timezone
from pymongo.database import Database
import redis
# REMOVED: import httpx (No longer needed)
import json
from fastapi import HTTPException

from ..models.document import DocumentOut, DocumentStatus
from ..models.user import UserInDB
from . import vector_store_service, storage_service, findings_service

logger = logging.getLogger(__name__)

# REMOVED: INTERNAL_API_URL & BROADCAST_ENDPOINT (Legacy WebSocket Architecture)

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
    """
    Updates the document record in MongoDB.
    Note: The actual SSE notification is now handled by the Celery Task (document_processing.py),
    so we don't need to broadcast here anymore.
    """
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
        
    result = db.documents.update_one({"_id": doc_object_id}, {"$set": update_fields})
    
    if result.modified_count > 0:
        logger.info(f"Document {doc_id_str} finalized in DB as READY.")
    else:
        logger.warning(f"Document {doc_id_str} update attempted but no changes made (or doc not found).")

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
        logger.error(f"Failed to download preview document from storage for key {document.preview_storage_key}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not retrieve the document preview from storage.")

def get_original_document_stream(db: Database, doc_id: str, owner: UserInDB) -> Tuple[Any, DocumentOut]:
    document = get_and_verify_document(db, doc_id, owner)
    if not document.storage_key:
        raise HTTPException(status_code=404, detail="Original document file not found in storage.")
    try:
        file_stream = storage_service.download_original_document_stream(document.storage_key)
        if file_stream is None: raise FileNotFoundError
        return file_stream, document
    except Exception as e:
        logger.error(f"Failed to download original document from storage for key {document.storage_key}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not retrieve the document file from storage.")

def get_document_content_by_key(storage_key: str) -> Optional[str]:
    try:
        content_bytes = storage_service.download_processed_text(storage_key)
        return content_bytes.decode('utf-8') if content_bytes else None
    except Exception as e:
        logger.error(f"Failed to retrieve content from storage for key {storage_key}: {e}", exc_info=True)
        return None

def delete_document_by_id(db: Database, redis_client: redis.Redis, doc_id: ObjectId, owner: UserInDB) -> List[str]:
    document_to_delete = db.documents.find_one({"_id": doc_id, "owner_id": owner.id})
    if not document_to_delete:
        raise HTTPException(status_code=404, detail="Document not found.")
    
    doc_id_str = str(doc_id)
    storage_key = document_to_delete.get("storage_key")
    processed_key = document_to_delete.get("processed_text_storage_key")
    preview_key = document_to_delete.get("preview_storage_key")

    deleted_finding_ids = findings_service.delete_findings_by_document_id(db=db, document_id=doc_id)
    
    vector_store_service.delete_document_embeddings(document_id=doc_id_str)
    if storage_key: storage_service.delete_file(storage_key=storage_key)
    if processed_key: storage_service.delete_file(storage_key=processed_key)
    if preview_key: storage_service.delete_file(storage_key=preview_key)
    
    delete_result = db.documents.delete_one({"_id": doc_id, "owner_id": owner.id})
    
    if delete_result.deleted_count != 1:
        raise HTTPException(status_code=500, detail="Failed to delete document from database.")

    # REMOVED: Legacy Broadcast. The Frontend now handles deletion via the API response
    # (DeletedDocumentResponse) which contains the deleted IDs. 
    
    return [str(fid) for fid in deleted_finding_ids]