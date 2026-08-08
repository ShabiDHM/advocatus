# FILE: backend/app/services/archive_service.py
# PHOENIX PROTOCOL - ARCHIVE SERVICE V7.0 (GUARANTEED USER_ID & OWNER_ID BACKWARD COMPATIBILITY)

import os
import logging
import urllib.parse
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

class ArchiveService:
    def __init__(self, db: Database):
        self.db = db
        self.bucket = os.getenv("B2_BUCKET_NAME")
        if not self.bucket:
            logger.error("B2_BUCKET_NAME not found in environment variables")

    def _to_oid(self, id_str: Any) -> ObjectId:
        """Safely convert to ObjectId."""
        if isinstance(id_str, ObjectId):
            return id_str
        try:
            return ObjectId(str(id_str))
        except (InvalidId, TypeError):
            raise HTTPException(status_code=400, detail=f"Invalid ObjectId format: {id_str}")

    def create_folder(self, user_id: str, title: str, parent_id: Optional[str] = None, case_id: Optional[str] = None) -> ArchiveItemInDB:
        user_oid = self._to_oid(user_id)
        folder_data: Dict[str, Any] = {
            "user_id": user_oid, 
            "owner_id": user_oid,
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
        folder_data["id"] = result.inserted_id
        return ArchiveItemInDB.model_validate(folder_data)

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
        except Exception: 
            file_size = 0
            
        try:
            s3_client.upload_fileobj(file_obj, self.bucket, storage_key, Config=transfer_config)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Storage Upload Failed: {str(e)}")
        
        user_oid = self._to_oid(user_id)
        doc_data: Dict[str, Any] = {
            "user_id": user_oid, 
            "owner_id": user_oid,
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
        doc_data["id"] = result.inserted_id
        return ArchiveItemInDB.model_validate(doc_data)

    def archive_document(self, db: Database, case_id: str, doc_id: str, owner: Any) -> Optional[ArchiveItemInDB]:
        try:
            user_id = str(owner.id) if hasattr(owner, 'id') else str(owner)
            user_oid = self._to_oid(user_id)
            doc_oid = self._to_oid(doc_id)
            case_oid = self._to_oid(case_id)

            doc = self.db.documents.find_one({"_id": doc_oid})
            if not doc:
                return None

            storage_key = doc.get("storage_key") or doc.get("preview_storage_key")
            filename = doc.get("file_name", "dokument.pdf")

            timestamp = int(datetime.now().timestamp())
            dest_key = f"archive/{user_id}/{timestamp}_{filename}"

            if storage_key:
                try:
                    s3_client = get_s3_client()
                    copy_source = {'Bucket': self.bucket, 'Key': storage_key}
                    s3_client.copy(copy_source, self.bucket, dest_key)
                except Exception as err:
                    logger.warning(f"S3 Copy fallback: {err}")
                    dest_key = storage_key

            doc_data: Dict[str, Any] = {
                "user_id": user_oid,
                "owner_id": user_oid,
                "case_id": case_oid,
                "title": filename,
                "item_type": "FILE",
                "file_type": "PDF",
                "category": "CASE_FILE",
                "storage_key": dest_key,
                "file_size": doc.get("file_size", 0),
                "created_at": datetime.now(timezone.utc),
                "description": "Archived from Case Documents",
                "is_shared": False
            }

            res = self.db.archives.insert_one(doc_data)
            doc_data["id"] = res.inserted_id

            # Update document status in db.documents
            self.db.documents.update_one({"_id": doc_oid}, {"$set": {"status": "ARCHIVED"}})

            return ArchiveItemInDB.model_validate(doc_data)
        except Exception as e:
            logger.error(f"❌ Error in archive_document: {e}")
            return None

    def get_archive_items(self, user_id: str, category: Optional[str] = None, case_id: Optional[str] = None, parent_id: Optional[str] = None) -> List[ArchiveItemInDB]:
        """
        PHOENIX FIX: Populates missing user_id / owner_id on old records to prevent Pydantic validation crashes.
        """
        user_oid = self._to_oid(user_id)
        
        query: Dict[str, Any] = {
            "$or": [{"user_id": user_oid}, {"owner_id": user_oid}, {"user_id": user_id}]
        }
        
        if parent_id and parent_id.strip() and parent_id != "null": 
            p_oid = self._to_oid(parent_id) if ObjectId.is_valid(parent_id) else parent_id
            query["parent_id"] = {"$in": [parent_id, p_oid]}

        if category and category != "ALL": 
            query["category"] = category

        if case_id and case_id.strip() and case_id != "null": 
            c_oid = self._to_oid(case_id) if ObjectId.is_valid(case_id) else case_id
            query["$or"] = [
                {"case_id": case_id, "user_id": user_oid},
                {"case_id": c_oid, "user_id": user_oid},
                {"case_id": case_id, "owner_id": user_oid},
                {"case_id": c_oid, "owner_id": user_oid}
            ]
        
        cursor = self.db.archives.find(query).sort([("item_type", -1), ("created_at", -1)])
        items = []
        for doc in cursor:
            doc["id"] = doc["_id"]
            
            # GUARANTEE BOTH USER_ID AND OWNER_ID ARE POPULATED BEFORE PYDANTIC VALIDATION
            if not doc.get("user_id") and doc.get("owner_id"):
                doc["user_id"] = doc["owner_id"]
            if not doc.get("owner_id") and doc.get("user_id"):
                doc["owner_id"] = doc["user_id"]

            # SAFE CONVERSION TO OBJECTID
            if doc.get("case_id") and isinstance(doc["case_id"], str) and ObjectId.is_valid(doc["case_id"]):
                doc["case_id"] = ObjectId(doc["case_id"])
            if doc.get("user_id") and isinstance(doc["user_id"], str) and ObjectId.is_valid(doc["user_id"]):
                doc["user_id"] = ObjectId(doc["user_id"])
            if doc.get("owner_id") and isinstance(doc["owner_id"], str) and ObjectId.is_valid(doc["owner_id"]):
                doc["owner_id"] = ObjectId(doc["owner_id"])
            if doc.get("parent_id") and isinstance(doc["parent_id"], str) and ObjectId.is_valid(doc["parent_id"]):
                doc["parent_id"] = ObjectId(doc["parent_id"])

            items.append(ArchiveItemInDB.model_validate(doc))
        return items

    def delete_archive_item(self, user_id: str, item_id: str):
        oid_user = self._to_oid(user_id)
        oid_item = self._to_oid(item_id)
        item = self.db.archives.find_one({"_id": oid_item, "$or": [{"user_id": oid_user}, {"owner_id": oid_user}]})
        if not item: raise HTTPException(status_code=404, detail="Item not found")
        if item.get("item_type") == "FOLDER":
            children = self.db.archives.find({"parent_id": oid_item, "$or": [{"user_id": oid_user}, {"owner_id": oid_user}]})
            for child in children: self.delete_archive_item(user_id, str(child["_id"]))
        if item.get("item_type") == "FILE" and item.get("storage_key"):
            try: get_s3_client().delete_object(Bucket=self.bucket, Key=item["storage_key"])
            except Exception: pass
        self.db.archives.delete_one({"_id": oid_item})

    def rename_item(self, user_id: str, item_id: str, new_title: str) -> None:
        oid_user = self._to_oid(user_id)
        oid_item = self._to_oid(item_id)
        self.db.archives.update_one({"_id": oid_item, "$or": [{"user_id": oid_user}, {"owner_id": oid_user}]}, {"$set": {"title": new_title}})

    def share_item(self, user_id: str, item_id: str, is_shared: bool) -> ArchiveItemInDB:
        oid_user = self._to_oid(user_id)
        oid_item = self._to_oid(item_id)
        
        result = self.db.archives.find_one_and_update(
            {"_id": oid_item, "$or": [{"user_id": oid_user}, {"owner_id": oid_user}]},
            {"$set": {"is_shared": is_shared}},
            return_document=True
        )
        if not result:
             raise HTTPException(status_code=404, detail="Item not found")
        
        result["id"] = result["_id"]
        return ArchiveItemInDB.model_validate(result)

    def share_case_items(self, user_id: str, case_id: str, is_shared: bool) -> int:
        oid_user = self._to_oid(user_id)
        oid_case = self._to_oid(case_id)
        
        result = self.db.archives.update_many(
            {"$or": [{"case_id": oid_case}, {"case_id": case_id}], "$or": [{"user_id": oid_user}, {"owner_id": oid_user}]},
            {"$set": {"is_shared": is_shared}}
        )
        return result.modified_count

    async def save_generated_file(self, user_id: str, filename: str, content: bytes, category: str, title: str, case_id: Optional[str] = None) -> ArchiveItemInDB:
        s3_client = get_s3_client()
        timestamp = int(datetime.now().timestamp())
        pdf_content, final_filename = pdf_service.convert_bytes_to_pdf(content, filename)
        storage_key = f"archive/{user_id}/{timestamp}_{final_filename}"
        
        try:
            s3_client.put_object(Bucket=self.bucket, Key=storage_key, Body=pdf_content)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal Storage Save Failed: {str(e)}")
            
        file_ext = final_filename.split('.')[-1].upper() if '.' in final_filename else "PDF"
        user_oid = self._to_oid(user_id)
        doc_data: Dict[str, Any] = {
            "user_id": user_oid,
            "owner_id": user_oid,
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
        doc_data["id"] = result.inserted_id
        return ArchiveItemInDB.model_validate(doc_data)
    
    async def archive_existing_document(self, user_id: str, case_id: str, source_key: str, filename: str, category: str = "CASE_FILE", original_doc_id: Optional[str] = None) -> ArchiveItemInDB:
        s3_client = get_s3_client()
        timestamp = int(datetime.now().timestamp())
        dest_key = f"archive/{user_id}/{timestamp}_{filename}"
        
        try:
            source_meta = s3_client.head_object(Bucket=self.bucket, Key=source_key)
            file_size = source_meta.get('ContentLength', 0)
            
            copy_source = {'Bucket': self.bucket, 'Key': source_key}
            s3_client.copy(copy_source, self.bucket, dest_key)
            logger.info(f"✅ S3 Archive Copy Successful: {source_key} -> {dest_key}")
            
        except Exception as e:
            logger.error(f"S3 Archive Error (Bucket: {self.bucket}, Source: {source_key}): {e}")
            raise HTTPException(status_code=500, detail=f"Failed to archive document: {str(e)}")

        file_ext = filename.split('.')[-1].upper() if '.' in filename else "FILE"
        user_oid = self._to_oid(user_id)
        doc_data: Dict[str, Any] = {
            "user_id": user_oid,
            "owner_id": user_oid,
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

        if original_doc_id:
            doc_data["original_doc_id"] = self._to_oid(original_doc_id)

        result = self.db.archives.insert_one(doc_data)
        doc_data["id"] = result.inserted_id
        
        return ArchiveItemInDB.model_validate(doc_data)

    def get_file_stream(self, user_id: str, item_id: str) -> Tuple[Any, str, int]:
        oid_user = self._to_oid(user_id)
        oid_item = self._to_oid(item_id)

        item = self.db.archives.find_one({"_id": oid_item, "$or": [{"user_id": oid_user}, {"owner_id": oid_user}]})
        
        if not item:
            raise HTTPException(status_code=404, detail="Archive item not found or access denied")
        
        if item.get("item_type") == "FOLDER":
            raise HTTPException(status_code=400, detail="Cannot download a folder directly")
            
        storage_key = item.get("storage_key")
        if not storage_key:
             raise HTTPException(status_code=404, detail="File storage key missing")

        s3_client = get_s3_client()
        try:
            response = s3_client.get_object(Bucket=self.bucket, Key=storage_key)
            file_size = response.get('ContentLength', item.get("file_size", 0))
            return response['Body'], item.get("title", "download"), file_size
        except Exception as e:
            logger.error(f"S3 Download Error for {storage_key}: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve file content")

    def get_presigned_url(self, user_id: str, item_id: str, disposition: str = "inline") -> str:
        oid_user = self._to_oid(user_id)
        oid_item = self._to_oid(item_id)
        
        item = self.db.archives.find_one({"_id": oid_item, "$or": [{"user_id": oid_user}, {"owner_id": oid_user}]})
        if not item: raise HTTPException(status_code=404, detail="Item not found")
        
        storage_key = item.get("storage_key")
        if not storage_key: raise HTTPException(status_code=404, detail="File storage key missing")
        
        filename = item.get("title", "download")
        safe_filename = urllib.parse.quote(filename)
        
        s3_client = get_s3_client()
        
        params = {
            'Bucket': self.bucket,
            'Key': storage_key,
            'ResponseContentDisposition': f"{disposition}; filename*=UTF-8''{safe_filename}"
        }
        
        if filename.lower().endswith(".pdf"):
            params['ResponseContentType'] = "application/pdf"
            
        try:
            url = s3_client.generate_presigned_url(
                'get_object',
                Params=params,
                ExpiresIn=3600
            )
            return url
        except Exception as e:
            logger.error(f"Presigned URL generation failed: {e}")
            raise HTTPException(status_code=500, detail="Could not generate download link")