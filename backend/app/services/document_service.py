# FILE: backend/app/services/document_service.py
# PHOENIX PROTOCOL - DOCUMENT SERVICE V9.0 (GRAPH DEPENDENCY COMPLETELY REMOVED)

import logging
import datetime
import importlib
import json
import os
from datetime import timezone
from typing import List, Optional, Tuple, Any, Dict
from bson import ObjectId
import redis
from fastapi import HTTPException, status
from pymongo.database import Database

from ..models.document import DocumentOut, DocumentStatus
from ..models.user import UserInDB
from . import vector_store_service, storage_service

logger = logging.getLogger(__name__)

CACHE_DIR = os.path.join(os.getcwd(), ".file_cache")
os.makedirs(CACHE_DIR, exist_ok=True)


def create_document_record(
    db: Database, owner: UserInDB, case_id: str, file_name: str, storage_key: str, mime_type: str
) -> DocumentOut:
    try:
        case_object_id = ObjectId(case_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Format i pasaktë i ID të lëndës.")

    existing_doc = db.documents.find_one({
        "case_id": case_object_id,
        "owner_id": owner.id,
        "file_name": file_name,
        "status": {"$ne": "DELETED"}
    })
    
    if existing_doc:
        logger.warning(f"⚠️ [Duplicate Guard] Document '{file_name}' already exists in case {case_id}.")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Dokumenti '{file_name}' tashmë ekziston në këtë lëndë. Fshini versionin e vjetër nëse dëshironi ta zëvendësoni."
        )

    document_data = {
        "owner_id": owner.id, 
        "case_id": case_object_id, 
        "file_name": file_name,
        "storage_key": storage_key, 
        "mime_type": mime_type,
        "status": DocumentStatus.PENDING,
        "created_at": datetime.datetime.now(timezone.utc),
        "preview_storage_key": None,
    }
    insert_result = db.documents.insert_one(document_data)
    if not insert_result.inserted_id:
        raise HTTPException(status_code=500, detail="Dështoi krijimi i regjistrit të dokumentit.")
    
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


def get_preview_file_path_or_stream(db: Database, doc_id: str, owner: UserInDB) -> Tuple[Optional[str], Any, DocumentOut, int]:
    document = get_and_verify_document(db, doc_id, owner)
    storage_key = document.preview_storage_key or document.storage_key
    
    if not storage_key:
        raise FileNotFoundError("Përmbajtja e dokumentit nuk është e disponueshme.")

    safe_cache_name = storage_key.replace('/', '_')
    cached_path = os.path.join(CACHE_DIR, safe_cache_name)
    
    if os.path.exists(cached_path) and os.path.getsize(cached_path) > 0:
        return cached_path, None, document, os.path.getsize(cached_path)

    try:
        s3 = storage_service.get_s3_client()
        obj = s3.get_object(Bucket=storage_service.B2_BUCKET_NAME, Key=storage_key)
        file_bytes = obj['Body'].read()
        if file_bytes:
            with open(cached_path, "wb") as f:
                f.write(file_bytes)
            return cached_path, None, document, len(file_bytes)
    except Exception as e:
        logger.warning(f"Could not populate SSD cache from B2 stream: {e}")

    file_stream, length = storage_service.get_file_stream_with_meta(storage_key)
    return None, file_stream, document, length


def get_preview_document_stream(db: Database, doc_id: str, owner: UserInDB) -> Tuple[Any, DocumentOut, int]:
    document = get_and_verify_document(db, doc_id, owner)
    storage_key = document.preview_storage_key or document.storage_key
    if not storage_key:
        raise FileNotFoundError("Përmbajtja e dokumentit nuk është e disponueshme.")
    stream, length = storage_service.get_file_stream_with_meta(storage_key)
    return stream, document, length


def get_original_document_stream(db: Database, doc_id: str, owner: UserInDB) -> Tuple[Any, DocumentOut]:
    document = get_and_verify_document(db, doc_id, owner)
    if not document.storage_key:
        raise HTTPException(status_code=404, detail="Skedari origjinal nuk u gjet në hapësirën ruajtëse.")
    try:
        file_stream = storage_service.download_original_document_stream(document.storage_key)
        if file_stream is None: 
            raise FileNotFoundError
        return file_stream, document
    except Exception as e:
        logger.error(f"Failed to download original document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Nuk mund të shkarkohej skedari origjinal.")


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
        raise HTTPException(status_code=404, detail="Dokumenti nuk u gjet.")
    
    doc_id_str = str(doc_id)
    storage_key = document_to_delete.get("storage_key")
    processed_key = document_to_delete.get("processed_text_storage_key")
    preview_key = document_to_delete.get("preview_storage_key")

    for k in [storage_key, preview_key]:
        if k:
            cached_file = os.path.join(CACHE_DIR, k.replace('/', '_'))
            if os.path.exists(cached_file):
                try: 
                    os.remove(cached_file)
                except Exception: 
                    pass

    mixed_id_query = {"$in": [doc_id, doc_id_str]}
    deleted_finding_ids = []
    
    try:
        findings_query = {"document_id": mixed_id_query}
        findings_cursor = db.findings.find(findings_query, {"_id": 1})
        deleted_finding_ids = [str(f["_id"]) for f in findings_cursor]
        db.findings.delete_many(findings_query)
    except Exception as e:
        logger.error(f"Error deleting findings for doc {doc_id}: {e}")
    
    link_query = {"$or": [{"document_id": mixed_id_query}, {"documentId": mixed_id_query}]}
    try:
        db.calendar_events.delete_many(link_query)
        if "alerts" in db.list_collection_names():
            db.alerts.delete_many(link_query)
    except Exception as e:
        logger.error(f"Error deleting events/alerts for doc {doc_id}: {e}")

    try:
        vector_store_service.delete_document_embeddings(user_id=str(owner.id), document_id=doc_id_str)
    except Exception as e:
        logger.error(f"Vector store cleanup failed: {e}")
    
    try:
        if storage_key: 
            storage_service.delete_file(storage_key=storage_key)
        if processed_key: 
            storage_service.delete_file(storage_key=processed_key)
        if preview_key: 
            storage_service.delete_file(storage_key=preview_key)
    except Exception as e:
        logger.error(f"S3 cleanup failed (non-critical): {e}")
    
    db.documents.delete_one({"_id": doc_id})
    
    try:
        if redis_client:
            payload = {"type": "DOCUMENT_DELETED", "document_id": doc_id_str}
            channel = f"user:{owner.id}:updates"
            redis_client.publish(channel, json.dumps(payload))
    except Exception as sse_err:
        logger.error(f"SSE deletion broadcast warning: {sse_err}")
    
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