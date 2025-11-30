# FILE: backend/app/services/archive_service.py
# PHOENIX PROTOCOL - ARCHIVE SERVICE (COPY ENABLED)
# 1. ADDED: 'archive_existing_document' to bridge Case Docs -> Archive.
# 2. LOGIC: Copies file content directly S3-to-S3 for efficiency.

import os
import logging
from typing import List, Optional, Tuple, Any, cast, Dict
from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId
from pymongo.database import Database
from fastapi import UploadFile
from fastapi.exceptions import HTTPException

# PHOENIX FIX: Relative imports
from ..models.archive import ArchiveItemInDB
from .storage_service import get_s3_client, transfer_config

logger = logging.getLogger(__name__)

# Environment
B2_BUCKET_NAME = os.getenv("B2_BUCKET_NAME")

class ArchiveService:
    def __init__(self, db: Database):
        self.db = db

    def _to_oid(self, id_str: str) -> ObjectId:
        try:
            return ObjectId(id_str)
        except (InvalidId, TypeError):
            raise HTTPException(status_code=400, detail=f"Invalid ObjectId format: {id_str}")

    async def archive_existing_document(
        self,
        user_id: str,
        case_id: str,
        source_key: str,
        filename: str,
        category: str = "CASE_FILE"
    ) -> ArchiveItemInDB:
        """
        Copies a document from the main storage into the Archive system.
        """
        s3_client = get_s3_client()
        timestamp = int(datetime.now().timestamp())
        
        # New destination key in Archive structure
        dest_key = f"archive/{user_id}/{timestamp}_{filename}"
        
        try:
            # Efficient S3-to-S3 copy
            copy_source = {'Bucket': B2_BUCKET_NAME, 'Key': source_key}
            s3_client.copy(copy_source, B2_BUCKET_NAME, dest_key)
            
            # Get size for metadata
            meta = s3_client.head_object(Bucket=B2_BUCKET_NAME, Key=dest_key)
            file_size = meta.get('ContentLength', 0)
            
        except Exception as e:
            logger.error(f"Archive Copy Failed: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to archive document: {str(e)}")

        file_ext = filename.split('.')[-1].upper() if '.' in filename else "FILE"

        doc_data = {
            "user_id": self._to_oid(user_id),
            "case_id": self._to_oid(case_id),
            "title": filename,
            "file_type": file_ext,
            "category": category,
            "storage_key": dest_key,
            "file_size": file_size,
            "created_at": datetime.now(timezone.utc),
            "description": f"Archived from Case"
        }
        
        self.db.archives.insert_one(doc_data)
        return ArchiveItemInDB(**doc_data)

    async def add_file_to_archive(
        self, 
        user_id: str, 
        file: UploadFile, 
        category: str, 
        title: str,
        case_id: Optional[str] = None
    ) -> ArchiveItemInDB:
        s3_client = get_s3_client()
        
        filename = file.filename or "untitled"
        file_ext = filename.split('.')[-1] if '.' in filename else "BIN"
        timestamp = int(datetime.now().timestamp())
        
        storage_key = f"archive/{user_id}/{timestamp}_{filename}"
        
        try:
            file.file.seek(0, 2)
            file_size = file.file.tell()
            file.file.seek(0)
        except Exception:
            file_size = 0
            
        try:
            s3_client.upload_fileobj(
                file.file, 
                B2_BUCKET_NAME, 
                storage_key,
                Config=transfer_config
            )
        except Exception as e:
            logger.error(f"!!! UPLOAD FAILED in ArchiveService: {e}")
            raise HTTPException(status_code=500, detail=f"Storage Upload Failed: {str(e)}")
        
        doc_data = {
            "user_id": self._to_oid(user_id),
            "title": title or filename,
            "file_type": file_ext.upper(),
            "category": category,
            "storage_key": storage_key,
            "file_size": file_size,
            "created_at": datetime.now(timezone.utc),
            "description": ""
        }
        
        if case_id and case_id.strip() and case_id != "null": 
            doc_data["case_id"] = self._to_oid(case_id)
        
        self.db.archives.insert_one(doc_data)
        return ArchiveItemInDB(**doc_data)

    async def save_generated_file(
        self,
        user_id: str,
        filename: str,
        content: bytes,
        category: str,
        title: str,
        case_id: Optional[str] = None
    ) -> ArchiveItemInDB:
        s3_client = get_s3_client()
        timestamp = int(datetime.now().timestamp())
        storage_key = f"archive/{user_id}/{timestamp}_{filename}"
        
        try:
            s3_client.put_object(
                Bucket=B2_BUCKET_NAME, 
                Key=storage_key, 
                Body=content
            )
        except Exception as e:
            logger.error(f"!!! GENERATED SAVE FAILED: {e}")
            raise HTTPException(status_code=500, detail=f"Internal Storage Save Failed: {str(e)}")
            
        file_ext = filename.split('.')[-1].upper() if '.' in filename else "PDF"
        
        doc_data = {
            "user_id": self._to_oid(user_id),
            "title": title,
            "file_type": file_ext,
            "category": category,
            "storage_key": storage_key,
            "file_size": len(content),
            "created_at": datetime.now(timezone.utc),
            "description": "Generated System Document"
        }
        
        if case_id and case_id.strip() and case_id != "null":
            doc_data["case_id"] = self._to_oid(case_id)
        
        self.db.archives.insert_one(doc_data)
        return ArchiveItemInDB(**doc_data)

    def get_archive_items(
        self, 
        user_id: str, 
        category: Optional[str] = None,
        case_id: Optional[str] = None
    ) -> List[ArchiveItemInDB]:
        query: Dict[str, Any] = {"user_id": self._to_oid(user_id)}
        if category and category != "ALL": query["category"] = category
        if case_id and case_id.strip() and case_id != "null": 
            query["case_id"] = self._to_oid(case_id)
            
        cursor = self.db.archives.find(query).sort("created_at", -1)
        return [ArchiveItemInDB(**doc) for doc in cursor]

    def delete_archive_item(self, user_id: str, item_id: str):
        query: Dict[str, Any] = {"_id": self._to_oid(item_id), "user_id": self._to_oid(user_id)}
        item = self.db.archives.find_one(query)
        if not item: raise HTTPException(status_code=404, detail="Item not found")
        
        try:
            s3_client = get_s3_client()
            s3_client.delete_object(Bucket=B2_BUCKET_NAME, Key=item["storage_key"])
        except Exception: pass
        
        self.db.archives.delete_one(query)

    def get_file_stream(self, user_id: str, item_id: str) -> Tuple[Any, str]:
        query: Dict[str, Any] = {"_id": self._to_oid(item_id), "user_id": self._to_oid(user_id)}
        item = self.db.archives.find_one(query)
        if not item: raise HTTPException(status_code=404, detail="Item not found")
            
        try:
            s3_client = get_s3_client()
            response = s3_client.get_object(Bucket=B2_BUCKET_NAME, Key=item["storage_key"])
            
            title = item["title"]
            file_type = item.get("file_type", "").lower()
            
            if not title.lower().endswith(f".{file_type}") and file_type:
                filename = f"{title}.{file_type}"
            else:
                filename = title
                
            return response['Body'], filename
        except Exception as e:
            logger.error(f"!!! STREAM FAILED: {e}")
            raise HTTPException(status_code=500, detail="Could not retrieve file stream")