# FILE: backend/app/services/archive_service.py
# PHOENIX PROTOCOL - ARCHIVE LOGIC (TYPE FIX)
# 1. FIX: Explicitly typed queries as 'Dict[str, Any]' to allow mixed types (ObjectId + String).
# 2. LOGIC: Retains full functionality for Upload/List/Delete.

import os
from typing import List, Optional, Tuple, Any, Dict
from datetime import datetime, timezone
from bson import ObjectId
from pymongo.database import Database
from fastapi import HTTPException, UploadFile

from app.models.archive import ArchiveItemInDB
from app.services.storage_service import get_s3_client

# Environment
B2_BUCKET_NAME = os.getenv("B2_BUCKET_NAME")

class ArchiveService:
    def __init__(self, db: Database):
        self.db = db

    async def add_file_to_archive(self, user_id: str, file: UploadFile, category: str, title: str) -> ArchiveItemInDB:
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
            "user_id": ObjectId(str(user_id)), # type: ignore
            "title": title or filename,
            "file_type": file_ext.upper(),
            "category": category,
            "storage_key": storage_key,
            "file_size": file_size,
            "created_at": datetime.now(timezone.utc),
            "description": ""
        }
        
        result = self.db.archives.insert_one(doc_data)
        return ArchiveItemInDB(**doc_data, _id=result.inserted_id)

    def get_archive_items(self, user_id: str, category: Optional[str] = None) -> List[ArchiveItemInDB]:
        # PHOENIX FIX: Explicit annotation Dict[str, Any] allows strings to be added later
        query: Dict[str, Any] = {"user_id": ObjectId(str(user_id))} # type: ignore
        
        if category and category != "ALL":
            query["category"] = category
            
        cursor = self.db.archives.find(query).sort("created_at", -1)
        return [ArchiveItemInDB(**doc, _id=doc["_id"]) for doc in cursor]

    def delete_archive_item(self, user_id: str, item_id: str):
        # Explicit annotation here too for safety
        query: Dict[str, Any] = {
            "_id": ObjectId(str(item_id)), # type: ignore
            "user_id": ObjectId(str(user_id)) # type: ignore
        }
        item = self.db.archives.find_one(query)
        
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        
        try:
            s3_client = get_s3_client()
            s3_client.delete_object(Bucket=B2_BUCKET_NAME, Key=item["storage_key"])
        except Exception:
            pass
        
        self.db.archives.delete_one({"_id": ObjectId(str(item_id))}) # type: ignore

    def get_file_stream(self, user_id: str, item_id: str) -> Tuple[Any, str]:
        query: Dict[str, Any] = {
            "_id": ObjectId(str(item_id)), # type: ignore
            "user_id": ObjectId(str(user_id)) # type: ignore
        }
        item = self.db.archives.find_one(query)
        
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
            
        try:
            s3_client = get_s3_client()
            response = s3_client.get_object(Bucket=B2_BUCKET_NAME, Key=item["storage_key"])
            return response['Body'], item["title"]
        except Exception as e:
            raise HTTPException(status_code=500, detail="Could not retrieve file stream")