# FILE: backend/app/api/endpoints/archive.py
# PHOENIX PROTOCOL - ARCHIVE API (RELATIVE IMPORTS)
# 1. FIX: Changed absolute 'app.*' imports to relative '...' to prevent startup crash.
# 2. STATUS: Matches existing project structure.

from fastapi import APIRouter, Depends, status, UploadFile, Form
from fastapi.responses import StreamingResponse
from typing import List, Annotated, Optional
from pymongo.database import Database
import urllib.parse

# PHOENIX FIX: Relative imports
from ...models.user import UserInDB
from ...models.archive import ArchiveItemOut
from ...services.archive_service import ArchiveService 
from .dependencies import get_current_user, get_db

router = APIRouter(tags=["Archive"])

@router.get("/items", response_model=List[ArchiveItemOut])
def get_archive_items(
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db),
    category: Optional[str] = None,
    case_id: Optional[str] = None
):
    service = ArchiveService(db)
    return service.get_archive_items(str(current_user.id), category, case_id)

@router.post("/upload", response_model=ArchiveItemOut)
async def upload_archive_item(
    file: UploadFile,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    title: str = Form(...),
    category: str = Form("UPLOAD"),
    case_id: Optional[str] = Form(None),
    db: Database = Depends(get_db)
):
    service = ArchiveService(db)
    return await service.add_file_to_archive(str(current_user.id), file, category, title, case_id)

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
    
    safe_filename = urllib.parse.quote(filename)
    
    return StreamingResponse(
        stream, 
        media_type="application/octet-stream", 
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_filename}"}
    )