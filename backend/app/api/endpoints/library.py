# FILE: backend/app/api/endpoints/library.py
# PHOENIX PROTOCOL - LIBRARY API (SYNTAX FIX)
# 1. FIX: Reordered arguments in 'get_templates' to satisfy Python syntax rules.
#    (Required arguments must come before Default arguments).

from fastapi import APIRouter, Depends, status
from typing import List, Optional, Annotated
from pymongo.database import Database

from ...models.user import UserInDB
from ...models.library import TemplateCreate, TemplateOut, TemplateUpdate
from ...services.library_service import LibraryService
from .dependencies import get_current_user, get_db

router = APIRouter(tags=["Library"])

@router.get("/templates", response_model=List[TemplateOut])
def get_templates(
    # PHOENIX FIX: Moved required dependency 'current_user' to the top
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db),
    category: Optional[str] = None # Default value (Optional) must be last
):
    """List all saved templates."""
    service = LibraryService(db)
    return service.get_templates(str(current_user.id), category)

@router.post("/templates", response_model=TemplateOut, status_code=status.HTTP_201_CREATED)
def create_template(
    template_in: TemplateCreate,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    """Save a new template/clause."""
    service = LibraryService(db)
    return service.create_template(str(current_user.id), template_in)

@router.put("/templates/{template_id}", response_model=TemplateOut)
def update_template(
    template_id: str,
    template_update: TemplateUpdate,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    """Update an existing template."""
    service = LibraryService(db)
    return service.update_template(str(current_user.id), template_id, template_update)

@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(
    template_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    """Delete a template."""
    service = LibraryService(db)
    service.delete_template(str(current_user.id), template_id)