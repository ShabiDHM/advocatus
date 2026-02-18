# FILE: backend/app/services/archive_service.py
# PHOENIX PROTOCOL - ARCHIVE V2.6 (SYNC & VALIDATION FIX)
# 1. FIXED: 'archive_existing_document' now persists 'original_doc_id' to DB.
# 2. FIXED: Injected MongoDB '_id' into return dict to prevent Pydantic ValidationError.
# 3. INTEGRITY: Maintains PDF conversion and storage logic.

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
from .pdf_service import pdf_service 

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

    def create_folder(self, user_id: str, title: str, parent_id: Optional[str] = None, case_id: Optional[str] = None) -> ArchiveItemInDB:
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
            folder_data["parent_id"] = self._to_oid(parent_id)
        if case_id and case_id.strip() and case_id != "null":
            folder_data["case_id"] = self._to_oid(case_id)
            
        result = self.db.archives.insert_one(folder_data)
        folder_data["_id"] = result.inserted_id
        return ArchiveItemInDB(**folder_data)

    async def add_file_to_archive(self, user_id: str, file: UploadFile, category: str, title: str, case_id: Optional[str] = None, parent_id: Optional[str] = None) -> ArchiveItemInDB:
        s3_client = get_s3_client()
        try:
            file_obj, final_filename = await pdf_service.convert_upload_to_pdf(file)
        except Exception as e:
            logger.error(f"PDF Conversion failed: {e}")
            file_obj = file.file
            final_filename = file.filename or "untitled"

        file_ext = final_filename.split('.')[-1].upper() if '.' in final_filename else "BIN"
        timestamp = int(datetime.now().timestamp())
        storage_key = f"archive/{user_id}/{timestamp}_{final_filename}"
        
        try:
            file_obj.seek(0, 2)
            file_size = file_obj.tell()
            file_obj.seek(0)
        except: 
            file_size = 0
            
        try:
            s3_client.upload_fileobj(file_obj, B2_BUCKET_NAME, storage_key, Config=transfer_config)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Storage Upload Failed: {str(e)}")
        
        doc_data = {
            "user_id": self._to_oid(user_id), 
            "title": title or final_filename, 
            "item_type": "FILE", 
            "file_type": file_ext,
            "category": category, 
            "storage_key": storage_key, 
            "file_size": file_size, 
            "created_at": datetime.now(timezone.utc),
            "description": "", 
            "is_shared": False
        }
        if case_id and case_id.strip() and case_id != "null": doc_data["case_id"] = self._to_oid(case_id)
        if parent_id and parent_id.strip() and parent_id != "null": doc_data["parent_id"] = self._to_oid(parent_id)
        
        result = self.db.archives.insert_one(doc_data)
        doc_data["_id"] = result.inserted_id
        return ArchiveItemInDB(**doc_data)

    def get_archive_items(self, user_id: str, category: Optional[str] = None, case_id: Optional[str] = None, parent_id: Optional[str] = None) -> List[ArchiveItemInDB]:
        query: Dict[str, Any] = {"user_id": self._to_oid(user_id)}
        if parent_id and parent_id.strip() and parent_id != "null": 
            query["parent_id"] = self._to_oid(parent_id)
        else:
            if not category or category == "ALL": query["parent_id"] = None
        if category and category != "ALL": query["category"] = category
        if case_id and case_id.strip() and case_id != "null": query["case_id"] = self._to_oid(case_id)
        cursor = self.db.archives.find(query).sort([("item_type", -1), ("created_at", -1)])
        return [ArchiveItemInDB(**doc) for doc in cursor]

    def delete_archive_item(self, user_id: str, item_id: str):
        oid_user = self._to_oid(user_id)
        oid_item = self._to_oid(item_id)
        item = self.db.archives.find_one({"_id": oid_item, "user_id": oid_user})
        if not item: raise HTTPException(status_code=404, detail="Item not found")
        if item.get("item_type") == "FOLDER":
            children = self.db.archives.find({"parent_id": oid_item, "user_id": oid_user})
            for child in children: self.delete_archive_item(user_id, str(child["_id"]))
        if item.get("item_type") == "FILE" and item.get("storage_key"):
            try: get_s3_client().delete_object(Bucket=B2_BUCKET_NAME, Key=item["storage_key"])
            except: pass
        self.db.archives.delete_one({"_id": oid_item})

    def rename_item(self, user_id: str, item_id: str, new_title: str) -> None:
        oid_user = self._to_oid(user_id)
        oid_item = self._to_oid(item_id)
        self.db.archives.update_one({"_id": oid_item, "user_id": oid_user}, {"$set": {"title": new_title}})

    def share_item(self, user_id: str, item_id: str, is_shared: bool) -> ArchiveItemInDB:
        result = self.db.archives.find_one_and_update({"_id": self._to_oid(item_id), "user_id": self._to_oid(user_id)}, {"$set": {"is_shared": is_shared}}, return_document=True)
        if not result: raise HTTPException(status_code=404, detail="Item not found")
        return ArchiveItemInDB(**result)

    def share_case_items(self, user_id: str, case_id: str, is_shared: bool) -> int:
        result = self.db.archives.update_many({"case_id": self._to_oid(case_id), "user_id": self._to_oid(user_id), "item_type": "FILE"}, {"$set": {"is_shared": is_shared}})
        return result.modified_count

    def get_file_stream(self, user_id: str, item_id: str) -> Tuple[Any, str]:
        item = self.db.archives.find_one({"_id": self._to_oid(item_id), "user_id": self._to_oid(user_id)})
        if not item: raise HTTPException(status_code=404, detail="Item not found")
        try:
            response = get_s3_client().get_object(Bucket=B2_BUCKET_NAME, Key=item["storage_key"])
            return response['Body'], item["title"]
        except: raise HTTPException(500, "Stream failed")

    async def save_generated_file(self, user_id: str, filename: str, content: bytes, category: str, title: str, case_id: Optional[str] = None) -> ArchiveItemInDB:
        s3_client = get_s3_client()
        timestamp = int(datetime.now().timestamp())
        
        pdf_content, final_filename = pdf_service.convert_bytes_to_pdf(content, filename)
        storage_key = f"archive/{user_id}/{timestamp}_{final_filename}"
        
        try:
            s3_client.put_object(Bucket=B2_BUCKET_NAME, Key=storage_key, Body=pdf_content)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal Storage Save Failed: {str(e)}")
            
        file_ext = final_filename.split('.')[-1].upper() if '.' in final_filename else "PDF"
        
        doc_data = {
            "user_id": self._to_oid(user_id),
            "title": title,
            "item_type": "FILE",
            "file_type": file_ext,
            "category": category,
            "storage_key": storage_key,
            "file_size": len(pdf_content),
            "created_at": datetime.now(timezone.utc),
            "description": "Generated System Document",
            "is_shared": False
        }
        
        if case_id and case_id.strip() and case_id != "null":
            doc_data["case_id"] = self._to_oid(case_id)
        
        result = self.db.archives.insert_one(doc_data)
        doc_data["_id"] = result.inserted_id
        return ArchiveItemInDB(**doc_data)
    
    async def archive_existing_document(self, user_id: str, case_id: str, source_key: str, filename: str, category: str = "CASE_FILE", original_doc_id: Optional[str] = None) -> ArchiveItemInDB:
        """
        PHOENIX FIX: Correctly persists original_doc_id for rename synchronization 
        and captures MongoDB _id for Pydantic validation.
        """
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

        # PHOENIX FIX: Store link to original document
        if original_doc_id:
            doc_data["original_doc_id"] = self._to_oid(original_doc_id)

        result = self.db.archives.insert_one(doc_data)
        # PHOENIX FIX: Inject generated ID for Pydantic validation
        doc_data["_id"] = result.inserted_id
        
        return ArchiveItemInDB(**doc_data)