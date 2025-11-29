# FILE: backend/app/api/endpoints/archive.py
# PHOENIX PROTOCOL - ARCHIVE API (FIXED)
# 1. FIX: Changed to Absolute Import 'from app.services...' to resolve symbol error.
# 2. TYPES: Kept strict typing for safety.

from fastapi import APIRouter, Depends, status, UploadFile, Form
from fastapi.responses import StreamingResponse
from typing import List, Annotated, Optional
from pymongo.database import Database
import urllib.parse

from app.models.user import UserInDB
from app.models.archive import ArchiveItemOut
# PHOENIX FIX: Absolute import is more reliable than relative '...'
from app.services.archive_service import ArchiveService 
from app.api.endpoints.dependencies import get_current_user, get_db

router = APIRouter(tags=["Archive"])

@router.get("/items", response_model=List[ArchiveItemOut])
def get_archive_items(
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db),
    category: Optional[str] = None
):
    service = ArchiveService(db)
    return service.get_archive_items(str(current_user.id), category)

@router.post("/upload", response_model=ArchiveItemOut)
async def upload_archive_item(
    file: UploadFile,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    title: str = Form(...),
    category: str = Form("UPLOAD"),
    db: Database = Depends(get_db)
):
    service = ArchiveService(db)
    return await service.add_file_to_archive(str(current_user.id), file, category, title)

@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_archive_item(
    item_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    service = ArchiveService(db)
    service.delete_archive_item(str(current_user.id), item_id)

@router.get("/items/{item_id}/download")
def download_archive_item(
    item_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    service = ArchiveService(db)
    stream, filename = service.get_file_stream(str(current_user.id), item_id)
    
    # Sanitize filename
    safe_filename = urllib.parse.quote(filename)
    
    return StreamingResponse(
        stream, 
        media_type="application/octet-stream", 
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_filename}"}
    )