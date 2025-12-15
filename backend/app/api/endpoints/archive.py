# FILE: backend/app/api/endpoints/archive.py
# PHOENIX PROTOCOL - ARCHIVE API V2.1 (RENAME ADDED)
# 1. NEW: Added 'rename_archive_item' endpoint via PUT.
# 2. SCHEMA: Added 'ArchiveRenameRequest' model.
# 3. STATUS: Fully Integrated with ArchiveService.

from fastapi import APIRouter, Depends, status, UploadFile, Form, Query, HTTPException, Body
from fastapi.responses import StreamingResponse
from typing import List, Annotated, Optional
from pymongo.database import Database
from pydantic import BaseModel
import urllib.parse
import mimetypes

# PHOENIX FIX: Relative imports
from ...models.user import UserInDB
from ...models.archive import ArchiveItemOut
from ...services.archive_service import ArchiveService 
from .dependencies import get_current_user, get_db

router = APIRouter(tags=["Archive"])

# --- REQUEST MODELS ---
class ArchiveRenameRequest(BaseModel):
    new_title: str

# --- ENDPOINTS ---

@router.get("/items", response_model=List[ArchiveItemOut])
def get_archive_items(
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db),
    category: Optional[str] = None,
    case_id: Optional[str] = None,
    parent_id: Optional[str] = None
):
    service = ArchiveService(db)
    return service.get_archive_items(str(current_user.id), category, case_id, parent_id)

@router.post("/folder", response_model=ArchiveItemOut)
def create_archive_folder(
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    title: str = Form(...),
    parent_id: Optional[str] = Form(None),
    case_id: Optional[str] = Form(None),
    db: Database = Depends(get_db)
):
    """Creates a new logical folder."""
    service = ArchiveService(db)
    return service.create_folder(str(current_user.id), title, parent_id, case_id)

@router.post("/upload", response_model=ArchiveItemOut)
async def upload_archive_item(
    file: UploadFile,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    title: str = Form(...),
    category: str = Form("UPLOAD"),
    case_id: Optional[str] = Form(None),
    parent_id: Optional[str] = Form(None),
    db: Database = Depends(get_db)
):
    service = ArchiveService(db)
    return await service.add_file_to_archive(str(current_user.id), file, category, title, case_id, parent_id)

@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_archive_item(
    item_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    service = ArchiveService(db)
    service.delete_archive_item(str(current_user.id), item_id)

# PHOENIX NEW: RENAME ENDPOINT
@router.put("/items/{item_id}/rename", status_code=status.HTTP_204_NO_CONTENT)
def rename_archive_item(
    item_id: str,
    body: ArchiveRenameRequest,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    """
    Renames a file or folder in the archive.
    """
    service = ArchiveService(db)
    service.rename_item(str(current_user.id), item_id, body.new_title)

@router.get("/items/{item_id}/download")
def download_archive_item(
    item_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db),
    preview: bool = Query(False) 
):
    service = ArchiveService(db)
    stream, filename = service.get_file_stream(str(current_user.id), item_id)
    
    # Encode filename for safety
    safe_filename = urllib.parse.quote(filename)
    
    # Determine MIME type based on extension
    content_type, _ = mimetypes.guess_type(filename)
    if not content_type:
        content_type = "application/octet-stream"
        
    # Set disposition based on preview flag
    disposition_type = "inline" if preview else "attachment"
    
    return StreamingResponse(
        stream, 
        media_type=content_type, 
        headers={"Content-Disposition": f"{disposition_type}; filename*=UTF-8''{safe_filename}"}
    )