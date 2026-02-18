# FILE: backend/app/api/endpoints/archive.py
# PHOENIX PROTOCOL - ARCHIVE API V2.5 (TURBO STREAM RESTORATION)
# 1. FIXED: Reverted Redirect (307) to StreamingResponse (200) to fix Frontend Viewer compatibility.
# 2. PERF: Implemented 64KB chunking (iter_chunks) for faster download speeds.
# 3. FIXED: Preserved 'Content-Length' to allow browser progress bars.

from fastapi import APIRouter, Depends, status, UploadFile, Form, Query, HTTPException, Body
from fastapi.responses import StreamingResponse
from typing import List, Annotated, Optional, Dict, Any
from pymongo.database import Database
from pydantic import BaseModel
import urllib.parse
import mimetypes

from ...models.user import UserInDB
from ...models.archive import ArchiveItemOut
from ...services.archive_service import ArchiveService 
from .dependencies import get_current_user, get_db

router = APIRouter(tags=["Archive"])

# --- REQUEST MODELS ---
class ArchiveRenameRequest(BaseModel):
    new_title: str

class ArchiveShareRequest(BaseModel):
    is_shared: bool

class ArchiveCaseShareRequest(BaseModel):
    case_id: str
    is_shared: bool

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

@router.put("/items/{item_id}/rename", status_code=status.HTTP_204_NO_CONTENT)
def rename_archive_item(
    item_id: str,
    body: ArchiveRenameRequest,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    service = ArchiveService(db)
    service.rename_item(str(current_user.id), item_id, body.new_title)

# PHOENIX NEW: SHARE SINGLE ITEM
@router.put("/items/{item_id}/share", response_model=ArchiveItemOut)
def share_archive_item(
    item_id: str,
    body: ArchiveShareRequest,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    """
    Toggles visibility of an archive item in the Client Portal.
    """
    service = ArchiveService(db)
    return service.share_item(str(current_user.id), item_id, body.is_shared)

# PHOENIX NEW: SHARE ALL ITEMS FOR CASE
@router.put("/case/share", status_code=status.HTTP_200_OK)
def share_archive_case(
    body: ArchiveCaseShareRequest,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    """
    Bulk toggles visibility for ALL archive files belonging to a case.
    """
    service = ArchiveService(db)
    count = service.share_case_items(str(current_user.id), body.case_id, body.is_shared)
    return {"message": "Success", "updated_count": count}

@router.get("/items/{item_id}/download")
def download_archive_item(
    item_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db),
    preview: bool = Query(False) 
):
    service = ArchiveService(db)
    
    # Unpack tuple from service (stream body, filename, file_size)
    stream_body, filename, file_size = service.get_file_stream(str(current_user.id), item_id)
    
    safe_filename = urllib.parse.quote(filename)
    content_type, _ = mimetypes.guess_type(filename)
    if not content_type: content_type = "application/octet-stream"
        
    disposition_type = "inline" if preview else "attachment"
    
    headers = {
        "Content-Disposition": f"{disposition_type}; filename*=UTF-8''{safe_filename}",
        "Content-Length": str(file_size)
    }
    
    # TURBO MODE: Iterate in 64KB chunks (65536 bytes) instead of default small chunks.
    # This reduces overhead and speeds up the transfer significantly.
    return StreamingResponse(
        stream_body.iter_chunks(chunk_size=65536), 
        media_type=content_type, 
        headers=headers
    )