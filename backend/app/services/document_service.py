# FILE: backend/app/services/document_service.py
# PHOENIX PROTOCOL MODIFICATION V7.0 (SERVICE COMPLETION):
# 1. CRITICAL ADDITION: Implemented the new `get_document_content_by_key` function.
# 2. This provides the necessary business logic for the new `/content` endpoint, calling
#    the storage service to download the processed text.
# 3. This change is the final step in resolving the `404 Not Found` error and makes the
#    document viewing functionality fully operational.
#
# PHOENIX PROTOCOL MODIFICATION V6.1 (SYNTAX CORRECTION)
# ...

import logging
from bson import ObjectId
from typing import List, Optional
import datetime
from datetime import timezone
from pymongo.database import Database
import redis
import httpx
import json
from fastapi import HTTPException

from ..models.document import DocumentOut, DocumentStatus
from ..models.user import UserInDB
from . import vector_store_service, storage_service

logger = logging.getLogger(__name__)

INTERNAL_API_URL = "http://backend:8000"
BROADCAST_ENDPOINT = f"{INTERNAL_API_URL}/internal/broadcast/document-update"

def trigger_websocket_broadcast(document_out: DocumentOut):
    """Triggers a websocket broadcast via an internal API endpoint."""
    try:
        payload = {
            "id": str(document_out.id),
            "case_id": str(document_out.case_id),
            "status": document_out.status,
            "file_name": document_out.file_name,
            "uploadedAt": document_out.created_at.isoformat(),
            "summary": document_out.summary
        }
        json_payload = json.dumps(payload)
        
        headers = {"Content-Type": "application/json"}
        with httpx.Client() as client:
            response = client.post(BROADCAST_ENDPOINT, content=json_payload, headers=headers)
        if response.status_code != 200:
            logger.error(f"Failed to broadcast status update via HTTP. Status: {response.status_code}, Response: {response.text}")
    except Exception as e:
        logger.error(f"Error during HTTP broadcast to main app: {e}", exc_info=True)

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
    }
    insert_result = db.documents.insert_one(document_data)
    if not insert_result.inserted_id:
        raise HTTPException(status_code=500, detail="Failed to create document record.")
    
    new_doc = db.documents.find_one({"_id": insert_result.inserted_id})
    return DocumentOut.model_validate(new_doc)

def finalize_document_processing(
    db: Database, redis_client: redis.Redis, doc_id_str: str,
    processed_text_storage_key: Optional[str] = None, summary: Optional[str] = None
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
        
    update_result = db.documents.update_one({"_id": doc_object_id}, {"$set": update_fields})
    
    if update_result.modified_count == 1:
        updated_doc_data = db.documents.find_one({"_id": doc_object_id})
        if not updated_doc_data:
            logger.error(f"Document {doc_id_str} not found after update.")
            return

        document_out = DocumentOut.model_validate(updated_doc_data)
        trigger_websocket_broadcast(document_out)
        logger.info(f"Document {doc_id_str} finalized and broadcasted as READY.")
    else:
        logger.error(f"Failed to finalize document {doc_id_str} in database.")

def get_documents_by_case_id(db: Database, case_id: str, owner: UserInDB) -> List[DocumentOut]:
    document_dicts = list(db.documents.find({"case_id": ObjectId(case_id), "owner_id": owner.id}).sort("created_at", -1))
    return [DocumentOut.model_validate(doc) for doc in document_dicts]

def get_and_verify_document(db: Database, doc_id: str, owner: UserInDB) -> DocumentOut:
    document_data = db.documents.find_one({"_id": ObjectId(doc_id), "owner_id": owner.id})
    if not document_data:
        raise HTTPException(status_code=404, detail="Document not found.")
    return DocumentOut.model_validate(document_data)

# --- PHOENIX PROTOCOL: Implement the missing service function ---
def get_document_content_by_key(storage_key: str) -> Optional[str]:
    """
    Retrieves the processed text content of a document from the storage service.
    """
    try:
        content_bytes = storage_service.download_processed_text(storage_key)
        if content_bytes:
            return content_bytes.decode('utf-8')
        return None
    except Exception as e:
        logger.error(f"Failed to retrieve content from storage for key {storage_key}: {e}", exc_info=True)
        # Depending on desired behavior, you might re-raise or return None
        return None

def delete_document_by_id(db: Database, redis_client: redis.Redis, doc_id: ObjectId, owner: UserInDB):
    document_to_delete = db.documents.find_one({"_id": doc_id, "owner_id": owner.id})
    if not document_to_delete:
        raise HTTPException(status_code=404, detail="Document not found.")
    
    doc_id_str = str(doc_id)

    db.findings.delete_many({"document_id": doc_id_str})
    vector_store_service.delete_document_embeddings(document_id=doc_id_str)
    storage_service.delete_file(storage_key=document_to_delete["storage_key"])
    if document_to_delete.get("processed_text_storage_key"):
        storage_service.delete_file(storage_key=document_to_delete.get("processed_text_storage_key"))
    
    delete_result = db.documents.delete_one({"_id": doc_id, "owner_id": owner.id})
    
    if delete_result.deleted_count == 1:
        deleted_document_out = DocumentOut.model_validate(document_to_delete)
        deleted_document_out.status = "DELETED"
        trigger_websocket_broadcast(deleted_document_out)
    else:
        raise HTTPException(status_code=500, detail="Failed to delete document from database.")