# FILE: backend/app/services/library_service.py
# PHOENIX PROTOCOL - LIBRARY LOGIC (TYPE FIX)
# 1. FIX: Removed redundant '_id' argument to prevent TypeError.
# 2. STATUS: CRUD operations for legal templates.

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
            "user_id": ObjectId(str(user_id)),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        })
        # PyMongo modifies 'doc' in-place, adding the '_id' field automatically.
        self.db.library.insert_one(doc)
        
        # PHOENIX FIX: 'doc' now contains '_id', so we just unpack it.
        return TemplateInDB(**doc)

    def get_templates(self, user_id: str, category: Optional[str] = None) -> List[TemplateInDB]:
        query: dict[str, Any] = {"user_id": ObjectId(str(user_id))}
        
        if category and category != "ALL":
            query["category"] = category
            
        cursor = self.db.library.find(query).sort("updated_at", -1)
        
        # PHOENIX FIX: 'doc' from Mongo already has '_id'.
        return [TemplateInDB(**doc) for doc in cursor]

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
            
        # PHOENIX FIX: 'result' is the complete document including '_id'.
        return TemplateInDB(**result)

    def delete_template(self, user_id: str, template_id: str):
        result = self.db.library.delete_one({
            "_id": ObjectId(str(template_id)), 
            "user_id": ObjectId(str(user_id))
        })
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Template not found")