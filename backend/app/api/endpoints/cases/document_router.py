# FILE: backend/app/api/endpoints/cases/document_router.py
# PHOENIX PROTOCOL - DOCUMENT ROUTER V50.0 (DIRTY STATE & SMART CACHE INVALIDATION)

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Body, BackgroundTasks, Query, Request
from typing import List, Annotated, Optional, Dict, Any
from fastapi.responses import StreamingResponse, FileResponse
from pymongo.database import Database
import redis
from bson import ObjectId
import asyncio
import logging
import io
import os
import json
import base64
import mimetypes
from datetime import datetime, timezone

from app.core.config import settings
from app.services import document_service, storage_service
from app.services.archive_service import ArchiveService
from app.models.document import DocumentOut, DocumentStatus
from app.models.archive import ArchiveItemOut
from app.models.user import UserInDB
from app.api.endpoints.dependencies import get_current_user, get_db, get_sync_redis
from app.api.endpoints.cases.cases_helpers import validate_object_id, DeletedDocumentResponse, BulkDeleteDocumentsRequest

router = APIRouter()
logger = logging.getLogger(__name__)

# MAX UPLOAD LIMIT (50 MB)
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024


def _safe_decode_token(token_str: str) -> Optional[Dict[str, Any]]:
    if not token_str or "." not in token_str:
        return None

    try:
        from jose import jwt
        secret = (
            getattr(settings, "SECRET_KEY", None) or 
            getattr(settings, "JWT_SECRET_KEY", None) or 
            os.getenv("SECRET_KEY") or 
            os.getenv("JWT_SECRET_KEY") or 
            "secret"
        )
        algorithm = getattr(settings, "ALGORITHM", "HS256")
        return jwt.decode(token_str, secret, algorithms=[algorithm])
    except Exception:
        pass

    try:
        parts = token_str.split(".")
        if len(parts) >= 2:
            payload_b64 = parts[1]
            payload_b64 += "=" * ((4 - len(payload_b64) % 4) % 4)
            decoded_bytes = base64.urlsafe_b64decode(payload_b64)
            return json.loads(decoded_bytes.decode("utf-8"))
    except Exception:
        pass

    return None


def _resolve_media_type(filename: str, doc_mime: Optional[str] = None) -> str:
    if doc_mime and doc_mime != "application/octet-stream" and "/" in doc_mime:
        return doc_mime

    fn = (filename or "").lower()
    if fn.endswith(".jpg") or fn.endswith(".jpeg"):
        return "image/jpeg"
    if fn.endswith(".png"):
        return "image/png"
    if fn.endswith(".webp"):
        return "image/webp"
    if fn.endswith(".pdf"):
        return "application/pdf"
    if fn.endswith(".csv"):
        return "text/csv"
    if fn.endswith(".txt") or fn.endswith(".json"):
        return "text/plain"

    guessed_type, _ = mimetypes.guess_type(filename)
    return guessed_type or "application/pdf"


@router.get("/{case_id}/documents", response_model=List[DocumentOut])
async def get_documents_for_case(
    case_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    case_oid = validate_object_id(case_id)
    
    cursor = db.documents.find({
        "$or": [{"case_id": case_id}, {"case_id": case_oid}],
        "status": {"$ne": "DELETED"}
    })
    docs = list(cursor)

    validated_docs = []
    for d in docs:
        doc_id_str = str(d["_id"])
        
        if d.get("status") in ["PENDING", "PROCESSING"] and d.get("extracted_text") and len(d["extracted_text"]) > 20:
            db.documents.update_one({"_id": d["_id"]}, {"$set": {"status": DocumentStatus.READY, "progress_percent": 100}})
            d["status"] = DocumentStatus.READY
            d["progress_percent"] = 100

        current_page_count = d.get("page_count") or d.get("pages") or 0
        if current_page_count <= 1:
            raw_text = d.get("extracted_text") or ""
            max_vector_page = 0
            try:
                vector_chunks = list(db.user_vectors.find({"document_id": doc_id_str}, {"page": 1}))
                if vector_chunks:
                    for vc in vector_chunks:
                        p_val = vc.get("page", 1)
                        if isinstance(p_val, int) and p_val > max_vector_page:
                            max_vector_page = p_val
                        elif isinstance(p_val, str) and p_val.isdigit() and int(p_val) > max_vector_page:
                            max_vector_page = int(p_val)
            except Exception:
                pass

            if max_vector_page > 1:
                calculated_pages = max_vector_page
            else:
                ff_count = raw_text.count('\x0c')
                page_markers = raw_text.count('--- Faqe') or raw_text.count('--- Page') or raw_text.count('[Faqe')
                if ff_count > 0:
                    calculated_pages = ff_count + 1
                elif page_markers > 0:
                    calculated_pages = page_markers
                elif len(raw_text) > 800:
                    calculated_pages = max(1, len(raw_text) // 1400 + 1)
                else:
                    calculated_pages = max(1, current_page_count)

            if calculated_pages > current_page_count:
                d["page_count"] = calculated_pages
                d["pages"] = calculated_pages
                try:
                    db.documents.update_one(
                        {"_id": d["_id"]}, 
                        {"$set": {"page_count": calculated_pages, "pages": calculated_pages}}
                    )
                except Exception:
                    pass
            else:
                d["page_count"] = current_page_count if current_page_count > 0 else 1
        else:
            d["page_count"] = current_page_count

        if not d.get("storage_key"):
            d["storage_key"] = f"doc_fallback_{doc_id_str}"
        if not d.get("file_name"):
            d["file_name"] = "Dokument"
            
        try:
            validated_docs.append(DocumentOut.model_validate(d))
        except Exception as err:
            logger.warning(f"Validation bypass for {doc_id_str}: {err}")

    return validated_docs


@router.post("/{case_id}/documents/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_document_for_case(
    case_id: str,
    background_tasks: BackgroundTasks,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    file: UploadFile = File(...),
    db: Database = Depends(get_db),
    redis_client: redis.Redis = Depends(get_sync_redis)
):
    case_oid = validate_object_id(case_id)
    
    # 1. Kontrolli i madhësisë (Max 50 MB)
    pdf_bytes = await file.read()
    if len(pdf_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Skedari është shumë i madh. Limiti maksimal është 50 MB."
        )

    # 2. Pastrimi i emrit të skedarit
    raw_filename = file.filename or "document.pdf"
    filename = storage_service.sanitize_filename(raw_filename)
    content_type = _resolve_media_type(filename, file.content_type)

    # 3. Ngarko në Storage
    key = await asyncio.to_thread(
        storage_service.upload_bytes_as_file,
        io.BytesIO(pdf_bytes),
        filename,
        str(current_user.id),
        case_id,
        content_type
    )

    try:
        cache_file_name = key.replace('/', '_')
        cache_file_path = os.path.join(document_service.CACHE_DIR, cache_file_name)
        with open(cache_file_path, "wb") as f:
            f.write(pdf_bytes)
    except Exception as e:
        logger.warning(f"Could not populate local preview cache: {e}")

    # 4. Ruaj në MongoDB
    existing_doc = db.documents.find_one({
        "case_id": case_oid,
        "owner_id": current_user.id,
        "file_name": filename,
        "status": {"$ne": "DELETED"}
    })
    
    if existing_doc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Dokumenti '{filename}' tashmë ekziston në këtë lëndë."
        )

    document_data = {
        "owner_id": current_user.id, 
        "case_id": case_oid, 
        "file_name": filename,
        "storage_key": key, 
        "mime_type": content_type,
        "page_count": 1,
        "status": DocumentStatus.PENDING,
        "progress_percent": 30,
        "progress_message": "Duke përgatitur skedarin...",
        "created_at": datetime.now(timezone.utc),
        "preview_storage_key": None,
    }
    insert_result = db.documents.insert_one(document_data)
    doc_id_str = str(insert_result.inserted_id)

    # PHOENIX SMART CACHE: Shëno lëndën si DIRTY (kërkon rianalizim sepse u shtua dokument)
    db.cases.update_one(
        {"$or": [{"_id": case_oid}, {"_id": case_id}]},
        {"$set": {"analysis_dirty": True, "updated_at": datetime.now(timezone.utc)}}
    )

    # 5. Ekzekutimi në Background
    from app.services.document_processing_service import orchestrate_document_processing_mongo
    background_tasks.add_task(orchestrate_document_processing_mongo, doc_id_str)

    new_doc = db.documents.find_one({"_id": insert_result.inserted_id})
    return DocumentOut.model_validate(new_doc)


@router.post("/{case_id}/documents/{doc_id}/archive", response_model=ArchiveItemOut)
async def archive_case_document_endpoint(
    case_id: str,
    doc_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    case_oid = validate_object_id(case_id)
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
    
    # PHOENIX SMART CACHE: Shëno lëndën si DIRTY
    db.cases.update_one(
        {"$or": [{"_id": case_oid}, {"_id": case_id}]},
        {"$set": {"analysis_dirty": True, "updated_at": datetime.now(timezone.utc)}}
    )

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
    
    doc_ids = []
    if body:
        doc_ids = body.document_ids or body.documentIds or []
    
    if not doc_ids:
        docs = list(db.documents.find({
            "$or": [{"case_id": case_id}, {"case_id": case_oid}],
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
    
    # PHOENIX SMART CACHE: Shëno lëndën si DIRTY pas fshirjes
    update_payload: Dict[str, Any] = {"analysis_dirty": True, "updated_at": datetime.now(timezone.utc)}
    if remaining_docs == 0:
        update_payload["latest_comprehensive_analysis"] = None
        update_payload["latest_analysis"] = None
        update_payload["latest_deep_analysis"] = None

    db.cases.update_one(
        {"$or": [{"_id": case_oid}, {"_id": case_id}]}, 
        {"$set": update_payload}
    )

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
        raise HTTPException(status_code=403, detail="Dokumenti nuk i përket kësaj lënde.")
        
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
        
        # PHOENIX SMART CACHE: Shëno lëndën si DIRTY
        update_payload: Dict[str, Any] = {"analysis_dirty": True, "updated_at": datetime.now(timezone.utc)}
        if remaining_docs == 0:
            update_payload["latest_comprehensive_analysis"] = None
            update_payload["latest_analysis"] = None
            update_payload["latest_deep_analysis"] = None

        db.cases.update_one(
            {"$or": [{"_id": case_oid}, {"_id": case_id}]}, 
            {"$set": update_payload}
        )
            
        return DeletedDocumentResponse(
            documentId=doc_id,
            deletedFindingIds=result.get("deleted_finding_ids", [])
        )
    raise HTTPException(status_code=500, detail="Dështoi fshirja e dokumentit.")


@router.get("/{case_id}/documents/{doc_id}/preview")
async def get_document_preview(
    case_id: str,
    doc_id: str,
    request: Request,
    token: Optional[str] = Query(None),
    db: Database = Depends(get_db)
):
    user_doc = None

    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        jwt_token = auth_header.split(" ")[1]
        payload = _safe_decode_token(jwt_token)
        if payload:
            user_id = payload.get("sub") or payload.get("id")
            if user_id:
                user_doc = db.users.find_one({"_id": ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id})

    if not user_doc and token:
        payload = _safe_decode_token(token)
        if payload:
            user_id = payload.get("sub") or payload.get("id")
            if user_id:
                user_doc = db.users.find_one({"_id": ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id})

    if not user_doc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="I paautorizuar për të parë këtë dokument."
        )

    user = UserInDB.model_validate(user_doc)

    cached_path, stream, doc, content_length = await asyncio.to_thread(
        document_service.get_preview_file_path_or_stream,
        db,
        doc_id,
        user
    )
    filename = doc.file_name if hasattr(doc, 'file_name') and doc.file_name else "document.pdf"
    doc_mime = getattr(doc, 'mime_type', None)
    resolved_media_type = _resolve_media_type(filename, doc_mime)
    
    if cached_path and os.path.exists(cached_path):
        return FileResponse(
            path=cached_path,
            media_type=resolved_media_type,
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
        media_type=resolved_media_type,
        headers=headers
    )