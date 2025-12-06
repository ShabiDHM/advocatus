# FILE: backend/app/services/document_service.py
# PHOENIX PROTOCOL - DOCUMENT SERVICE CORE
# 1. FIX: Restored missing 'get_documents_by_case_id' method.
# 2. LOGIC: Robust retrieval and deletion logic.
# 3. STATUS: Production Ready.

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

from . import vector_store_service, storage_service, findings_service
# Graph service imported conditionally or handled in upper layers if circular dependency arises
# Here we assume it's safe or we wrap it.
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

# PHOENIX FIX: Restored this critical method
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
    
    # Try fetching explicit preview first
    if document.preview_storage_key:
        try:
            file_stream = storage_service.download_preview_document_stream(document.preview_storage_key)
            if file_stream:
                return file_stream, document
        except Exception:
            logger.warning(f"Preview key exists but fetch failed for {doc_id}, falling back to original.")

    # Fallback to original (which is now likely a PDF due to Universal Converter)
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
    document_to_delete = db.documents.find_one({"_id": doc_id, "owner_id": owner.id})
    if not document_to_delete:
        raise HTTPException(status_code=404, detail="Document not found.")
    
    doc_id_str = str(doc_id)
    storage_key = document_to_delete.get("storage_key")
    processed_key = document_to_delete.get("processed_text_storage_key")
    preview_key = document_to_delete.get("preview_storage_key")

    # 1. Delete Findings
    deleted_finding_ids = findings_service.delete_findings_by_document_id(db=db, document_id=doc_id)
    
    # 2. Cleanup Links
    any_id_query = {"document_id": {"$in": [doc_id, doc_id_str]}}
    db.calendar_events.delete_many(any_id_query)
    db.alerts.delete_many(any_id_query)
    
    # 3. Clean Graph
    try:
        graph_service.delete_document_nodes(doc_id_str)
    except Exception:
        pass # Non-critical

    # 4. Clean Vector Store
    vector_store_service.delete_document_embeddings(document_id=doc_id_str)
    
    # 5. Clean Files
    if storage_key: storage_service.delete_file(storage_key=storage_key)
    if processed_key: storage_service.delete_file(storage_key=processed_key)
    if preview_key: storage_service.delete_file(storage_key=preview_key)
    
    # 6. Delete Record
    db.documents.delete_one({"_id": doc_id})
    
    return [str(fid) for fid in deleted_finding_ids]