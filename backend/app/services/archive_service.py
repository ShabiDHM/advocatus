# FILE: backend/app/services/archive_service.py
# PHOENIX PROTOCOL - ARCHIVE V2.3 (SHARING SUPPORT)
# 1. NEW: 'share_item' toggles 'is_shared' for a single file.
# 2. NEW: 'share_case_items' bulk toggles 'is_shared' for all files in a case.
# 3. STATUS: Backend logic complete for Client Portal Library.

import os
import logging
from typing import List, Optional, Tuple, Any, Dict
from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId
from pymongo.database import Database
from fastapi import UploadFile
from fastapi.exceptions import HTTPException

from ..models.archive import ArchiveItemInDB
from .storage_service import get_s3_client, transfer_config

logger = logging.getLogger(__name__)

B2_BUCKET_NAME = os.getenv("B2_BUCKET_NAME")

class ArchiveService:
    def __init__(self, db: Database):
        self.db = db

    def _to_oid(self, id_str: str) -> ObjectId:
        try:
            return ObjectId(id_str)
        except (InvalidId, TypeError):
            raise HTTPException(status_code=400, detail=f"Invalid ObjectId format: {id_str}")

    # --- FOLDER MANAGEMENT ---
    def create_folder(
        self,
        user_id: str,
        title: str,
        parent_id: Optional[str] = None,
        case_id: Optional[str] = None
    ) -> ArchiveItemInDB:
        folder_data = {
            "user_id": self._to_oid(user_id),
            "title": title,
            "item_type": "FOLDER",
            "file_type": "FOLDER",
            "category": "FOLDER",
            "created_at": datetime.now(timezone.utc),
            "storage_key": None,
            "file_size": 0,
            "description": "",
            "is_shared": False 
        }
        
        if parent_id and parent_id.strip() and parent_id != "null":
            parent = self.db.archives.find_one({"_id": self._to_oid(parent_id)})
            if not parent or parent.get("item_type") != "FOLDER":
                raise HTTPException(status_code=400, detail="Invalid parent folder")
            folder_data["parent_id"] = self._to_oid(parent_id)
            
        if case_id and case_id.strip() and case_id != "null":
            folder_data["case_id"] = self._to_oid(case_id)
            
        result = self.db.archives.insert_one(folder_data)
        folder_data["_id"] = result.inserted_id
        return ArchiveItemInDB(**folder_data)

    # --- FILE OPERATIONS ---
    async def add_file_to_archive(
        self, 
        user_id: str, 
        file: UploadFile, 
        category: str, 
        title: str,
        case_id: Optional[str] = None,
        parent_id: Optional[str] = None 
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
            s3_client.upload_fileobj(file.file, B2_BUCKET_NAME, storage_key, Config=transfer_config)
        except Exception as e:
            logger.error(f"!!! UPLOAD FAILED in ArchiveService: {e}")
            raise HTTPException(status_code=500, detail=f"Storage Upload Failed: {str(e)}")
        
        doc_data = {
            "user_id": self._to_oid(user_id),
            "title": title or filename,
            "item_type": "FILE",
            "file_type": file_ext.upper(),
            "category": category,
            "storage_key": storage_key,
            "file_size": file_size,
            "created_at": datetime.now(timezone.utc),
            "description": "",
            "is_shared": False
        }
        
        if case_id and case_id.strip() and case_id != "null": 
            doc_data["case_id"] = self._to_oid(case_id)
        if parent_id and parent_id.strip() and parent_id != "null":
            doc_data["parent_id"] = self._to_oid(parent_id)
        
        self.db.archives.insert_one(doc_data)
        return ArchiveItemInDB(**doc_data)

    # --- RETRIEVAL ---
    def get_archive_items(
        self, 
        user_id: str, 
        category: Optional[str] = None,
        case_id: Optional[str] = None,
        parent_id: Optional[str] = None
    ) -> List[ArchiveItemInDB]:
        query: Dict[str, Any] = {"user_id": self._to_oid(user_id)}
        
        if parent_id and parent_id.strip() and parent_id != "null":
            query["parent_id"] = self._to_oid(parent_id)
        else:
            if not category or category == "ALL":
                query["parent_id"] = None

        if category and category != "ALL": query["category"] = category
        if case_id and case_id.strip() and case_id != "null": query["case_id"] = self._to_oid(case_id)
            
        cursor = self.db.archives.find(query).sort([("item_type", -1), ("created_at", -1)])
        return [ArchiveItemInDB(**doc) for doc in cursor]

    # --- CASCADE DELETION ---
    def delete_archive_item(self, user_id: str, item_id: str):
        oid_user = self._to_oid(user_id)
        oid_item = self._to_oid(item_id)
        
        item = self.db.archives.find_one({"_id": oid_item, "user_id": oid_user})
        if not item: raise HTTPException(status_code=404, detail="Item not found")
        
        if item.get("item_type") == "FOLDER":
            children = self.db.archives.find({"parent_id": oid_item, "user_id": oid_user})
            for child in children:
                self.delete_archive_item(user_id, str(child["_id"]))
        
        if item.get("item_type") == "FILE" and item.get("storage_key"):
            try:
                s3_client = get_s3_client()
                s3_client.delete_object(Bucket=B2_BUCKET_NAME, Key=item["storage_key"])
            except Exception as e:
                logger.error(f"Failed to delete S3 file {item['storage_key']}: {e}")
        
        self.db.archives.delete_one({"_id": oid_item})

    # --- RENAME ---
    def rename_item(self, user_id: str, item_id: str, new_title: str) -> None:
        oid_user = self._to_oid(user_id)
        oid_item = self._to_oid(item_id)
        result = self.db.archives.update_one(
            {"_id": oid_item, "user_id": oid_user},
            {"$set": {"title": new_title}}
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Item not found or access denied.")

    # --- PHOENIX NEW: SHARING LOGIC ---
    def share_item(self, user_id: str, item_id: str, is_shared: bool) -> ArchiveItemInDB:
        """
        Toggles the 'is_shared' flag for a single archive item.
        """
        oid_user = self._to_oid(user_id)
        oid_item = self._to_oid(item_id)

        result = self.db.archives.find_one_and_update(
            {"_id": oid_item, "user_id": oid_user},
            {"$set": {"is_shared": is_shared}},
            return_document=True
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="Item not found or access denied.")
            
        return ArchiveItemInDB(**result)

    def share_case_items(self, user_id: str, case_id: str, is_shared: bool) -> int:
        """
        Bulk toggles 'is_shared' for all files belonging to a specific case.
        """
        oid_user = self._to_oid(user_id)
        oid_case = self._to_oid(case_id)

        result = self.db.archives.update_many(
            {"case_id": oid_case, "user_id": oid_user, "item_type": "FILE"},
            {"$set": {"is_shared": is_shared}}
        )
        
        return result.modified_count

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
    
    async def save_generated_file(self, user_id: str, filename: str, content: bytes, category: str, title: str, case_id: Optional[str] = None) -> ArchiveItemInDB:
        s3_client = get_s3_client()
        timestamp = int(datetime.now().timestamp())
        storage_key = f"archive/{user_id}/{timestamp}_{filename}"
        
        try:
            s3_client.put_object(Bucket=B2_BUCKET_NAME, Key=storage_key, Body=content)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal Storage Save Failed: {str(e)}")
            
        file_ext = filename.split('.')[-1].upper() if '.' in filename else "PDF"
        
        doc_data = {
            "user_id": self._to_oid(user_id),
            "title": title,
            "item_type": "FILE",
            "file_type": file_ext,
            "category": category,
            "storage_key": storage_key,
            "file_size": len(content),
            "created_at": datetime.now(timezone.utc),
            "description": "Generated System Document",
            "is_shared": False
        }
        
        if case_id and case_id.strip() and case_id != "null":
            doc_data["case_id"] = self._to_oid(case_id)
        
        self.db.archives.insert_one(doc_data)
        return ArchiveItemInDB(**doc_data)
    
    async def archive_existing_document(self, user_id: str, case_id: str, source_key: str, filename: str, category: str = "CASE_FILE", original_doc_id: Optional[str] = None) -> ArchiveItemInDB:
        s3_client = get_s3_client()
        timestamp = int(datetime.now().timestamp())
        dest_key = f"archive/{user_id}/{timestamp}_{filename}"
        try:
            copy_source = {'Bucket': B2_BUCKET_NAME, 'Key': source_key}
            s3_client.copy(copy_source, B2_BUCKET_NAME, dest_key)
            meta = s3_client.head_object(Bucket=B2_BUCKET_NAME, Key=dest_key)
            file_size = meta.get('ContentLength', 0)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to archive document: {str(e)}")

        file_ext = filename.split('.')[-1].upper() if '.' in filename else "FILE"
        doc_data = {
            "user_id": self._to_oid(user_id),
            "case_id": self._to_oid(case_id),
            "title": filename,
            "item_type": "FILE",
            "file_type": file_ext,
            "category": category,
            "storage_key": dest_key,
            "file_size": file_size,
            "created_at": datetime.now(timezone.utc),
            "description": "Archived from Case",
            "is_shared": False
        }
        self.db.archives.insert_one(doc_data)
        return ArchiveItemInDB(**doc_data)