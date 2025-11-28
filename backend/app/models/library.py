# FILE: backend/app/models/library.py
# PHOENIX PROTOCOL - LIBRARY MODELS
# 1. STRUCTURE: Defines 'LibraryTemplate' for storing reusable legal text.
# 2. METADATA: Includes tags and categories for easy searching.

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime
from .common import PyObjectId

class TemplateBase(BaseModel):
    title: str = Field(..., min_length=3)
    content: str = Field(..., min_length=10)
    category: str = "CLAUSE" # CLAUSE, CONTRACT, LETTER, MEMO
    tags: List[str] = []
    description: Optional[str] = None
    is_favorite: bool = False

class TemplateCreate(TemplateBase):
    pass

class TemplateUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    description: Optional[str] = None
    is_favorite: Optional[bool] = None

class TemplateInDB(TemplateBase):
    id: PyObjectId = Field(alias="_id", default=None)
    user_id: PyObjectId
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

class TemplateOut(TemplateInDB):
    id: PyObjectId = Field(alias="_id", serialization_alias="id", default=None)