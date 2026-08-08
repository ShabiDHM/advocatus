# FILE: backend/app/api/endpoints/cases/document_router.py
# PHOENIX PROTOCOL - DOCUMENT ROUTER V9.0 (PRISTINE UN-WATERMARKED INSTANT UPLOAD)

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Body, BackgroundTasks
from typing import List, Annotated, Optional
from fastapi.responses import StreamingResponse, FileResponse
from pymongo.database import Database
import redis
from bson import ObjectId
import asyncio
import logging
import io
import os

from app.services import document_service, storage_service
from app.services.archive_service import ArchiveService
from app.services.graph_service import graph_service
from app.models.document import DocumentOut
from app.models.archive import ArchiveItemOut
from app.models.user import UserInDB
from app.api.endpoints.dependencies import get_current_user, get_db, get_sync_redis
from app.api.endpoints.cases.cases_helpers import validate_object_id, DeletedDocumentResponse, BulkDeleteDocumentsRequest

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/{case_id}/documents", response_model=List[DocumentOut])
async def get_documents_for_case(
    case_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    case_oid = validate_object_id(case_id)
    user_oid = ObjectId(current_user.id)
    
    cursor = db.documents.find({
        "$or": [{"case_id": case_id}, {"case_id": case_oid}],
        "owner_id": user_oid,
        "status": {"$ne": "DELETED"}
    })
    docs = list(cursor)
    return [DocumentOut.model_validate(d) for d in docs]

@router.post("/{case_id}/documents/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_document_for_case(
    case_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Database = Depends(get_db),
    redis_client: redis.Redis = Depends(get_sync_redis)
):
    # ⚡ 1. Read raw pristine PDF bytes directly (0ms - No watermarks, no modifications)
    pdf_bytes = await file.read()
    filename = file.filename or "document.pdf"
    content_type = file.content_type or "application/pdf"

    # 2. Upload pristine bytes to storage
    key = await asyncio.to_thread(
        storage_service.upload_bytes_as_file,
        io.BytesIO(pdf_bytes),
        filename,
        str(current_user.id),
        case_id,
        content_type
    )

    # 3. Immediately populate local SSD disk cache for instant 0ms previews
    try:
        cache_file_name = key.replace('/', '_')
        cache_file_path = os.path.join(document_service.CACHE_DIR, cache_file_name)
        with open(cache_file_path, "wb") as f:
            f.write(pdf_bytes)
    except Exception as e:
        logger.warning(f"Could not populate local SSD preview cache: {e}")

    doc = document_service.create_document_record(
        db=db,
        owner=current_user,
        case_id=case_id,
        file_name=filename,
        storage_key=key,
        mime_type=content_type
    )

    from app.services.document_processing_service import orchestrate_document_processing_mongo
    background_tasks.add_task(
        orchestrate_document_processing_mongo,
        str(doc.id)
    )

    return DocumentOut.model_validate(doc)

@router.post("/{case_id}/documents/{doc_id}/archive", response_model=ArchiveItemOut)
async def archive_case_document_endpoint(
    case_id: str,
    doc_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    validate_object_id(case_id)
    validate_object_id(doc_id)
    
    service = ArchiveService(db)
    archive_item = await asyncio.to_thread(
        service.archive_document,
        db=db,
        case_id=case_id,
        doc_id=doc_id,
        owner=current_user
    )
    if not archive_item:
        raise HTTPException(status_code=404, detail="Dokumenti nuk u gjet ose dështoi arkivimi.")
    return archive_item

@router.post("/{case_id}/documents/bulk-delete")
@router.delete("/{case_id}/documents/bulk-delete")
async def bulk_delete_documents_endpoint(
    case_id: str,
    body: Optional[BulkDeleteDocumentsRequest] = Body(None),
    current_user: Annotated[UserInDB, Depends(get_current_user)] = None,
    db: Database = Depends(get_db),
    redis_client: redis.Redis = Depends(get_sync_redis)
):
    case_oid = validate_object_id(case_id)
    user_oid = ObjectId(current_user.id)
    
    doc_ids = []
    if body:
        doc_ids = body.document_ids or body.documentIds or []
    
    if not doc_ids:
        docs = list(db.documents.find({
            "$or": [{"case_id": case_id}, {"case_id": case_oid}],
            "owner_id": user_oid, 
            "status": {"$nin": ["DELETED", "ARCHIVED"]}
        }))
        doc_ids = [str(d["_id"]) for d in docs]

    if not doc_ids:
        return {"status": "success", "deleted_count": 0, "deleted_finding_ids": []}

    result = await asyncio.to_thread(
        document_service.bulk_delete_documents,
        db=db,
        redis_client=redis_client,
        document_ids=doc_ids,
        owner=current_user
    )
    
    remaining_docs = db.documents.count_documents({
        "$or": [{"case_id": case_id}, {"case_id": case_oid}], 
        "status": {"$ne": "DELETED"}
    })
    
    if remaining_docs == 0:
        db.cases.update_one(
            {"$or": [{"_id": case_oid}, {"_id": case_id}]}, 
            {"$unset": {"graph_data": "", "latest_analysis": "", "latest_deep_analysis": ""}}
        )
        try:
            await asyncio.to_thread(graph_service.delete_case_nodes, case_id)
        except Exception as e:
            logger.warning(f"Failed to clear case graph nodes: {e}")

    return {
        "status": "success",
        "deleted_count": result.get("deleted_count", len(doc_ids)),
        "deleted_finding_ids": result.get("deleted_finding_ids", []),
        "deleted_document_ids": doc_ids,
        "remaining_documents": remaining_docs
    }

@router.delete("/{case_id}/documents/{doc_id}", response_model=DeletedDocumentResponse)
async def delete_document(
    case_id: str,
    doc_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db),
    redis_client: redis.Redis = Depends(get_sync_redis)
):
    doc = await asyncio.to_thread(
        document_service.get_and_verify_document,
        db,
        doc_id,
        current_user
    )
    if str(doc.case_id) != case_id:
        raise HTTPException(status_code=403, detail="Document does not belong to this case.")
        
    case_oid = validate_object_id(case_id)
    result = await asyncio.to_thread(
        document_service.bulk_delete_documents,
        db=db,
        redis_client=redis_client,
        document_ids=[doc_id],
        owner=current_user
    )
    if result.get("deleted_count", 0) > 0:
        remaining_docs = db.documents.count_documents({
            "$or": [{"case_id": case_id}, {"case_id": case_oid}], 
            "status": {"$ne": "DELETED"}
        })
        if remaining_docs == 0:
            db.cases.update_one(
                {"$or": [{"_id": case_oid}, {"_id": case_id}]}, 
                {"$unset": {"graph_data": "", "latest_analysis": "", "latest_deep_analysis": ""}}
            )
            try:
                await asyncio.to_thread(graph_service.delete_case_nodes, case_id)
            except Exception as e:
                logger.warning(f"Failed to clear case graph nodes: {e}")
            
        return DeletedDocumentResponse(
            documentId=doc_id,
            deletedFindingIds=result.get("deleted_finding_ids", [])
        )
    raise HTTPException(status_code=500, detail="Failed to delete document.")

@router.get("/{case_id}/documents/{doc_id}/preview")
async def get_document_preview(
    case_id: str,
    doc_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    """
    PHOENIX FAST PREVIEW: Serves from local SSD cache in 0.001s.
    """
    cached_path, stream, doc, content_length = await asyncio.to_thread(
        document_service.get_preview_file_path_or_stream,
        db,
        doc_id,
        current_user
    )
    filename = doc.file_name if hasattr(doc, 'file_name') else "document.pdf"
    
    if cached_path and os.path.exists(cached_path):
        return FileResponse(
            path=cached_path,
            media_type="application/pdf",
            filename=filename,
            headers={
                "Content-Disposition": f'inline; filename="{filename}"',
                "Cache-Control": "public, max-age=86400",
                "Accept-Ranges": "bytes"
            }
        )
    
    headers = {
        "Content-Disposition": f'inline; filename="{filename}"',
        "Cache-Control": "public, max-age=3600",
        "Accept-Ranges": "bytes"
    }
    if content_length > 0:
        headers["Content-Length"] = str(content_length)

    return StreamingResponse(
        stream, 
        media_type="application/pdf",
        headers=headers
    )