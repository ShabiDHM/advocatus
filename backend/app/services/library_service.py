# FILE: backend/app/services/library_service.py
# PHOENIX PROTOCOL - LIBRARY LOGIC (TYPE FIX)
# 1. FIX: Explicit string conversion for ObjectId to satisfy strict linters.
# 2. CRUD: Manage personal legal templates.

from typing import List, Optional, Any
from datetime import datetime, timezone
from bson import ObjectId
from pymongo.database import Database
from fastapi import HTTPException

from ..models.library import TemplateCreate, TemplateUpdate, TemplateInDB

class LibraryService:
    def __init__(self, db: Database):
        self.db = db

    def create_template(self, user_id: str, data: TemplateCreate) -> TemplateInDB:
        doc = data.model_dump()
        doc.update({
            "user_id": ObjectId(str(user_id)), # PHOENIX FIX: Explicit str()
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        })
        result = self.db.library.insert_one(doc)
        return TemplateInDB(**doc, _id=result.inserted_id)

    def get_templates(self, user_id: str, category: Optional[str] = None) -> List[TemplateInDB]:
        # PHOENIX FIX: Explicit str() to satisfy Pylance
        query: dict[str, Any] = {"user_id": ObjectId(str(user_id))}
        
        if category and category != "ALL":
            query["category"] = category
            
        cursor = self.db.library.find(query).sort("updated_at", -1)
        return [TemplateInDB(**doc, _id=doc["_id"]) for doc in cursor]

    def update_template(self, user_id: str, template_id: str, data: TemplateUpdate) -> TemplateInDB:
        update_data = {k: v for k, v in data.model_dump().items() if v is not None}
        if not update_data:
            raise HTTPException(status_code=400, detail="No data to update")
            
        update_data["updated_at"] = datetime.now(timezone.utc)
        
        result = self.db.library.find_one_and_update(
            {"_id": ObjectId(str(template_id)), "user_id": ObjectId(str(user_id))},
            {"$set": update_data},
            return_document=True
        )
        if not result:
            raise HTTPException(status_code=404, detail="Template not found")
        return TemplateInDB(**result, _id=result["_id"])

    def delete_template(self, user_id: str, template_id: str):
        result = self.db.library.delete_one({
            "_id": ObjectId(str(template_id)), 
            "user_id": ObjectId(str(user_id))
        })
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Template not found")