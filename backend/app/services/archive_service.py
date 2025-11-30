# FILE: backend/app/services/archive_service.py
# PHOENIX PROTOCOL - ARCHIVE LOGIC (RELATIVE IMPORTS)
# 1. FIX: Changed absolute imports to relative to prevent ModuleNotFoundError.
# 2. FIX: Kept type ignores for ObjectId strictness.

import os
from typing import List, Optional, Tuple, Any, cast, Dict
from datetime import datetime, timezone
from bson import ObjectId
from pymongo.database import Database
from fastapi import HTTPException, UploadFile

# PHOENIX FIX: Relative imports
from ..models.archive import ArchiveItemInDB
from .storage_service import get_s3_client

# Environment
B2_BUCKET_NAME = os.getenv("B2_BUCKET_NAME")

class ArchiveService:
    def __init__(self, db: Database):
        self.db = db

    def _to_oid(self, id_str: str) -> ObjectId:
        """Helper to cast string to ObjectId and silence Pylance."""
        return ObjectId(cast(Any, id_str))

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
            file.file.seek(0)
            s3_client.upload_fileobj(file.file, B2_BUCKET_NAME, storage_key)
            file.file.seek(0, 2)
            file_size = file.file.tell()
            file.file.seek(0)
        except Exception as e:
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
        if case_id: doc_data["case_id"] = self._to_oid(case_id)
        
        result = self.db.archives.insert_one(doc_data)
        return ArchiveItemInDB(**doc_data, _id=result.inserted_id)

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
        if case_id: doc_data["case_id"] = self._to_oid(case_id)
        
        result = self.db.archives.insert_one(doc_data)
        return ArchiveItemInDB(**doc_data, _id=result.inserted_id)

    def get_archive_items(
        self, 
        user_id: str, 
        category: Optional[str] = None,
        case_id: Optional[str] = None
    ) -> List[ArchiveItemInDB]:
        query: Dict[str, Any] = {"user_id": self._to_oid(user_id)}
        if category and category != "ALL": query["category"] = category
        if case_id: query["case_id"] = self._to_oid(case_id)
            
        cursor = self.db.archives.find(query).sort("created_at", -1)
        return [ArchiveItemInDB(**doc, _id=doc["_id"]) for doc in cursor]

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
            return response['Body'], item["title"]
        except Exception as e:
            raise HTTPException(status_code=500, detail="Could not retrieve file stream")