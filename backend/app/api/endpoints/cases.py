# FILE: backend/app/api/endpoints/cases.py
# PHOENIX PROTOCOL - CASES ROUTER V7.0 (INTELLIGENCE ENGINE CONNECTED)
# 1. ADDED: get_node_analysis_endpoint for Real-Time Graph Intelligence.
# 2. MAINTAINED: All existing Archive, Portal, and Document logic.

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Body, Query
from typing import List, Annotated, Dict, Optional
from fastapi.responses import Response, StreamingResponse, JSONResponse, FileResponse
from pydantic import BaseModel
from pymongo.database import Database
import redis
from bson import ObjectId
from bson.errors import InvalidId
import asyncio
import logging
import io
import urllib.parse
import mimetypes
from datetime import datetime, timezone

# --- SERVICE IMPORTS ---
from ...services import (
    case_service,
    document_service,
    report_service,
    storage_service,
    analysis_service,
    archive_service,
    pdf_service,
    llm_service,
    drafting_service,
    spreadsheet_service
)
from ...services.graph_service import graph_service 

# --- MODEL IMPORTS ---
from ...models.case import CaseCreate, CaseOut
from ...models.user import UserInDB
from ...models.drafting import DraftRequest 
from ...models.archive import ArchiveItemOut 
from ...models.document import DocumentOut
from ...models.finance import InvoiceInDB

from .dependencies import get_current_user, get_db, get_sync_redis
from ...celery_app import celery_app

router = APIRouter(tags=["Cases"])
logger = logging.getLogger(__name__)

# --- LOCAL SCHEMAS ---
class DocumentContentOut(BaseModel):
    text: str

class DeletedDocumentResponse(BaseModel):
    documentId: str
    deletedFindingIds: List[str]

class RenameDocumentRequest(BaseModel):
    new_name: str

class ShareDocumentRequest(BaseModel):
    is_shared: bool 

class BulkDeleteRequest(BaseModel):
    document_ids: List[str]

class ArchiveImportRequest(BaseModel):
    archive_item_ids: List[str]

def validate_object_id(id_str: str) -> ObjectId:
    try: return ObjectId(id_str)
    except InvalidId: raise HTTPException(status_code=400, detail="Invalid ID format.")

# --- ENDPOINTS ---

@router.get("", response_model=List[CaseOut], include_in_schema=False)
@router.get("/", response_model=List[CaseOut])
async def get_user_cases(current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    return await asyncio.to_thread(case_service.get_cases_for_user, db=db, owner=current_user)

@router.post("", response_model=CaseOut, status_code=status.HTTP_201_CREATED, include_in_schema=False)
@router.post("/", response_model=CaseOut, status_code=status.HTTP_201_CREATED)
async def create_new_case(case_in: CaseCreate, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    return await asyncio.to_thread(case_service.create_case, db=db, case_in=case_in, owner=current_user)

@router.get("/{case_id}", response_model=CaseOut)
async def get_single_case(case_id: str, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    validated_case_id = validate_object_id(case_id)
    case = await asyncio.to_thread(case_service.get_case_by_id, db=db, case_id=validated_case_id, owner=current_user)
    if not case: raise HTTPException(status_code=404, detail="Case not found.")
    return case

@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case(case_id: str, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    validated_case_id = validate_object_id(case_id)
    
    # 1. Delete from MongoDB
    await asyncio.to_thread(case_service.delete_case_by_id, db=db, case_id=validated_case_id, owner=current_user)
    
    # 2. SYNC: Delete from Graph (Fire and Forget)
    try:
        await asyncio.to_thread(graph_service.delete_node, node_id=case_id)
    except Exception as e:
        logger.warning(f"Failed to sync delete to graph for case {case_id}: {e}")

    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.post("/{case_id}/drafts", status_code=status.HTTP_202_ACCEPTED, tags=["Drafting"])
async def create_draft_for_case(case_id: str, job_in: DraftRequest, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    validated_case_id = validate_object_id(case_id)
    return await asyncio.to_thread(case_service.create_draft_job_for_case, db=db, case_id=validated_case_id, job_in=job_in, owner=current_user)

@router.get("/{case_id}/documents", response_model=List[DocumentOut], tags=["Documents"])
async def get_documents_for_case(case_id: str, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    return await asyncio.to_thread(document_service.get_documents_by_case_id, db, case_id, current_user)

@router.post("/{case_id}/documents/upload", status_code=status.HTTP_202_ACCEPTED, tags=["Documents"])
async def upload_document_for_case(case_id: str, current_user: Annotated[UserInDB, Depends(get_current_user)], file: UploadFile = File(...), db: Database = Depends(get_db)):
    try:
        pdf_bytes, final_filename = await pdf_service.pdf_service.process_and_brand_pdf(file, case_id)
        pdf_file_obj = io.BytesIO(pdf_bytes)
        pdf_file_obj.name = final_filename 
        storage_key = await asyncio.to_thread(storage_service.upload_bytes_as_file, file_obj=pdf_file_obj, filename=final_filename, user_id=str(current_user.id), case_id=case_id, content_type="application/pdf")
        new_document = document_service.create_document_record(db=db, owner=current_user, case_id=case_id, file_name=final_filename, storage_key=storage_key, mime_type="application/pdf")
        celery_app.send_task("process_document_task", args=[str(new_document.id)])
        return DocumentOut.model_validate(new_document)
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail="Document upload failed.")

@router.post("/{case_id}/documents/import-archive", status_code=status.HTTP_201_CREATED, tags=["Documents"])
async def import_archive_documents(
    case_id: str,
    body: ArchiveImportRequest,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    validate_object_id(case_id)
    case = await asyncio.to_thread(case_service.get_case_by_id, db=db, case_id=ObjectId(case_id), owner=current_user)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")

    imported_docs = []
    for item_id in body.archive_item_ids:
        try:
            archive_item = await asyncio.to_thread(
                db.archives.find_one,
                {"_id": ObjectId(item_id), "user_id": current_user.id, "item_type": "FILE"}
            )
            if not archive_item or not archive_item.get("storage_key"): continue
            original_key = archive_item["storage_key"]
            filename = archive_item["title"]
            new_key = await asyncio.to_thread(storage_service.copy_s3_object, source_key=original_key, dest_folder=f"{current_user.id}/{case_id}")
            new_doc = document_service.create_document_record(db=db, owner=current_user, case_id=case_id, file_name=filename, storage_key=new_key, mime_type="application/pdf")
            celery_app.send_task("process_document_task", args=[str(new_doc.id)])
            imported_docs.append(DocumentOut.model_validate(new_doc))
        except Exception as e:
            logger.error(f"Failed to import archive item {item_id}: {e}")
            continue
    return imported_docs

@router.get("/{case_id}/documents/{doc_id}", response_model=DocumentOut, tags=["Documents"])
async def get_document_by_id(case_id: str, doc_id: str, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    doc = await asyncio.to_thread(document_service.get_and_verify_document, db, doc_id, current_user)
    if str(doc.case_id) != case_id: raise HTTPException(status_code=403)
    return doc

@router.delete("/{case_id}/documents/{doc_id}", response_model=DeletedDocumentResponse, tags=["Documents"])
async def delete_document(
    case_id: str, 
    doc_id: str, 
    current_user: Annotated[UserInDB, Depends(get_current_user)], 
    db: Database = Depends(get_db),
    redis_client: redis.Redis = Depends(get_sync_redis)
):
    validate_object_id(case_id)
    doc_oid = validate_object_id(doc_id)
    
    doc = await asyncio.to_thread(document_service.get_and_verify_document, db, doc_id, current_user)
    if str(doc.case_id) != case_id: raise HTTPException(status_code=403, detail="Document does not belong to this case.")

    # 1. Delete from MongoDB/Redis
    result = await asyncio.to_thread(
        document_service.bulk_delete_documents, 
        db=db, 
        redis_client=redis_client, 
        document_ids=[doc_id], 
        owner=current_user
    )
    
    # 2. SYNC: Delete from Graph
    if result.get("deleted_count", 0) > 0:
        try:
            await asyncio.to_thread(graph_service.delete_node, node_id=doc_id)
        except Exception as e:
            logger.warning(f"Failed to sync delete to graph for document {doc_id}: {e}")

        return DeletedDocumentResponse(
            documentId=doc_id, 
            deletedFindingIds=result.get("deleted_finding_ids", [])
        )
    raise HTTPException(status_code=500, detail="Failed to delete document.")

@router.put("/{case_id}/documents/{doc_id}/share", response_model=DocumentOut, tags=["Documents"])
async def share_document_toggle(
    case_id: str,
    doc_id: str,
    body: ShareDocumentRequest,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    validate_object_id(case_id)
    doc_oid = validate_object_id(doc_id)
    doc = await asyncio.to_thread(document_service.get_and_verify_document, db, doc_id, current_user)
    if str(doc.case_id) != case_id: 
        raise HTTPException(status_code=403, detail="Document does not belong to this case.")

    await asyncio.to_thread(
        db.documents.update_one,
        {"_id": doc_oid},
        {"$set": {"is_shared": body.is_shared, "updated_at": datetime.now(timezone.utc)}}
    )
    
    updated_doc = await asyncio.to_thread(db.documents.find_one, {"_id": doc_oid})
    return DocumentOut.model_validate(updated_doc)

@router.post("/{case_id}/documents/{doc_id}/cross-examine", tags=["Analysis"])
async def cross_examine_document(
    case_id: str,
    doc_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    validated_case_id = validate_object_id(case_id)
    validated_doc_id = validate_object_id(doc_id)
    target_doc = await asyncio.to_thread(document_service.get_and_verify_document, db, doc_id, current_user)
    if str(target_doc.case_id) != case_id: raise HTTPException(status_code=403, detail="Access Denied.")
    
    other_docs_cursor = db.documents.find(
        {"case_id": validated_case_id, "_id": {"$ne": validated_doc_id}, "summary": {"$exists": True, "$ne": None}},
        {"summary": 1, "file_name": 1}
    )
    other_docs = await asyncio.to_thread(list, other_docs_cursor)
    context_summaries = [f"[{d['file_name']}]: {d['summary']}" for d in other_docs]
    
    key = target_doc.processed_text_storage_key
    if not key: raise HTTPException(status_code=400, detail="Document text not processed yet.")
    target_text = await asyncio.to_thread(document_service.get_document_content_by_key, storage_key=key)
    if not target_text: raise HTTPException(status_code=400, detail="Document content empty.")

    analysis_result = await asyncio.to_thread(llm_service.perform_litigation_cross_examination, target_text=target_text, context_summaries=context_summaries)
    await asyncio.to_thread(db.documents.update_one, {"_id": validated_doc_id}, {"$set": {"litigation_analysis": analysis_result}})
    return JSONResponse(content=analysis_result)

@router.get("/{case_id}/documents/{doc_id}/generate-objection", response_class=FileResponse, tags=["Drafting"])
async def generate_objection(
    case_id: str,
    doc_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    validated_case_id = validate_object_id(case_id)
    validated_doc_id = validate_object_id(doc_id)
    case = await asyncio.to_thread(case_service.get_case_by_id, db=db, case_id=validated_case_id, owner=current_user)
    if not case: raise HTTPException(status_code=404, detail="Case not found.")
    doc = await asyncio.to_thread(document_service.get_and_verify_document, db, doc_id, current_user)
    if str(doc.case_id) != case_id: raise HTTPException(status_code=403, detail="Access Denied.")
    if not doc.litigation_analysis: raise HTTPException(status_code=404, detail="No analysis available.")
    
    title = case.get("title", "Lënda") if isinstance(case, dict) else getattr(case, "title", "Lënda")
    try:
        objection_bytes = await asyncio.to_thread(drafting_service.generate_objection_document, analysis_result=doc.litigation_analysis, case_title=title)
    except Exception as e:
        logger.error(f"Document generation failed: {e}")
        raise HTTPException(status_code=500, detail="Document generation failed.")
    filename = f"Kundërshtim_{doc.file_name}.docx"
    return StreamingResponse(io.BytesIO(objection_bytes), media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", headers={"Content-Disposition": f"attachment; filename={filename}"})

@router.get("/{case_id}/documents/{doc_id}/preview", tags=["Documents"], response_class=StreamingResponse)
async def get_document_preview(case_id: str, doc_id: str, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    try:
        file_stream, doc = await asyncio.to_thread(document_service.get_preview_document_stream, db, doc_id, current_user)
        if str(doc.case_id) != case_id: raise HTTPException(status_code=403)
        return StreamingResponse(file_stream, media_type="application/pdf", headers={'Content-Disposition': f'inline; filename="{doc.file_name}"'})
    except FileNotFoundError: return await get_original_document(case_id, doc_id, current_user, db)

@router.get("/{case_id}/documents/{doc_id}/original", tags=["Documents"], response_class=StreamingResponse)
async def get_original_document(case_id: str, doc_id: str, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    file_stream, doc = await asyncio.to_thread(document_service.get_original_document_stream, db, doc_id, current_user)
    if str(doc.case_id) != case_id: raise HTTPException(status_code=403)
    return StreamingResponse(file_stream, media_type=doc.mime_type, headers={'Content-Disposition': f'inline; filename="{doc.file_name}"'})

@router.get("/{case_id}/documents/{doc_id}/content", response_model=DocumentContentOut, tags=["Documents"])
async def get_document_content(case_id: str, doc_id: str, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    doc = await asyncio.to_thread(document_service.get_and_verify_document, db, doc_id, current_user)
    if str(doc.case_id) != case_id: raise HTTPException(status_code=403)
    key = doc.processed_text_storage_key
    if not key: raise HTTPException(404, "No content")
    content = await asyncio.to_thread(document_service.get_document_content_by_key, storage_key=key)
    return DocumentContentOut(text=content or "")

@router.get("/{case_id}/documents/{doc_id}/report", tags=["Documents"])
async def get_document_report_pdf(case_id: str, doc_id: str, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    doc = await asyncio.to_thread(document_service.get_and_verify_document, db, doc_id, current_user)
    if str(doc.case_id) != case_id: raise HTTPException(status_code=403)
    key = doc.processed_text_storage_key
    if not key: raise HTTPException(status_code=404, detail="Document content not available for report.")
    content = await asyncio.to_thread(document_service.get_document_content_by_key, storage_key=key)
    pdf_buffer = await asyncio.to_thread(report_service.create_pdf_from_text, text=content or "", document_title=doc.file_name)
    return StreamingResponse(pdf_buffer, media_type="application/pdf", headers={'Content-Disposition': f'inline; filename="{doc.file_name}.pdf"'})

@router.post("/{case_id}/documents/bulk-delete", tags=["Documents"])
async def bulk_delete_documents(
    case_id: str,
    body: BulkDeleteRequest,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db),
    redis_client: redis.Redis = Depends(get_sync_redis)
):
    validate_object_id(case_id)
    case = await asyncio.to_thread(case_service.get_case_by_id, db=db, case_id=ObjectId(case_id), owner=current_user)
    if not case: raise HTTPException(status_code=404, detail="Case not found.")
    
    # 1. Delete from MongoDB/Redis
    result = await asyncio.to_thread(document_service.bulk_delete_documents, db=db, redis_client=redis_client, document_ids=body.document_ids, owner=current_user)
    
    # 2. SYNC: Bulk Delete from Graph
    if result.get("deleted_count", 0) > 0:
        for doc_id in body.document_ids:
            try:
                await asyncio.to_thread(graph_service.delete_node, node_id=doc_id)
            except Exception as e:
                logger.warning(f"Failed to sync delete to graph for document {doc_id}: {e}")

    return JSONResponse(status_code=200, content=result)

@router.post("/{case_id}/documents/{doc_id}/archive", response_model=ArchiveItemOut, tags=["Documents"])
async def archive_case_document(case_id: str, doc_id: str, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    doc = await asyncio.to_thread(document_service.get_and_verify_document, db, doc_id, current_user)
    if str(doc.case_id) != case_id: raise HTTPException(status_code=403)
    archiver = archive_service.ArchiveService(db)
    return await archiver.archive_existing_document(user_id=str(current_user.id), case_id=case_id, source_key=doc.storage_key, filename=doc.file_name)

@router.put("/{case_id}/documents/{doc_id}/rename", tags=["Documents"])
async def rename_document_endpoint(case_id: str, doc_id: str, body: RenameDocumentRequest, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    return await asyncio.to_thread(case_service.rename_document, db=db, case_id=ObjectId(case_id), doc_id=ObjectId(doc_id), new_name=body.new_name, owner=current_user)

@router.post("/{case_id}/analyze", tags=["Analysis"])
async def analyze_case_risks(case_id: str, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    validate_object_id(case_id)
    return JSONResponse(content=await asyncio.to_thread(
        analysis_service.cross_examine_case, 
        db=db, 
        case_id=case_id,
        user_id=str(current_user.id)
    ))

@router.post("/{case_id}/analyze/spreadsheet", tags=["Analysis"])
async def analyze_spreadsheet_endpoint(
    case_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    file: UploadFile = File(...),
    db: Database = Depends(get_db)
):
    validate_object_id(case_id)
    case = await asyncio.to_thread(case_service.get_case_by_id, db=db, case_id=ObjectId(case_id), owner=current_user)
    if not case: raise HTTPException(status_code=404, detail="Case not found.")

    try:
        content = await file.read()
        filename = file.filename or "unknown.xlsx"
        result = await spreadsheet_service.analyze_spreadsheet_file(content, filename)
        return JSONResponse(content=result)
        
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Spreadsheet Analysis Error: {e}")
        raise HTTPException(status_code=500, detail="Analysis failed.")

@router.get("/public/{case_id}/timeline", tags=["Public Portal"])
async def get_public_case_timeline(case_id: str, db: Database = Depends(get_db)):
    try:
        validate_object_id(case_id)
        return await asyncio.to_thread(case_service.get_public_case_events, db=db, case_id=case_id)
    except Exception: raise HTTPException(404, "Portal not available.")

@router.get("/public/{case_id}/documents/{doc_id}/download", tags=["Public Portal"])
async def download_public_document(
    case_id: str,
    doc_id: str,
    source: str = Query("ACTIVE", enum=["ACTIVE", "ARCHIVE"]),
    db: Database = Depends(get_db)
):
    try:
        case_oid = validate_object_id(case_id)
        doc_oid = validate_object_id(doc_id)
        
        doc_data = None
        if source == "ACTIVE":
            doc_data = await asyncio.to_thread(db.documents.find_one, {
                "_id": doc_oid,
                "$or": [{"case_id": case_id}, {"case_id": case_oid}]
            })
        else:
            doc_data = await asyncio.to_thread(db.archives.find_one, {
                "_id": doc_oid,
                "$or": [{"case_id": case_id}, {"case_id": case_oid}],
                "item_type": "FILE"
            })

        if not doc_data:
            raise HTTPException(status_code=404, detail="Document not found.")

        if not doc_data.get("is_shared"):
            raise HTTPException(status_code=403, detail="Access Denied: This document is not shared.")

        storage_key = doc_data.get("storage_key")
        if not storage_key:
            raise HTTPException(status_code=404, detail="File content missing.")
        
        file_stream = await asyncio.to_thread(storage_service.download_original_document_stream, storage_key)
        if not file_stream:
             raise HTTPException(status_code=500, detail="Storage Error.")

        filename = doc_data.get("file_name") or doc_data.get("title") or "document.pdf"
        safe_filename = urllib.parse.quote(filename)
        
        content_type, _ = mimetypes.guess_type(filename)
        if not content_type: content_type = "application/octet-stream"

        return StreamingResponse(
            file_stream, 
            media_type=content_type, 
            headers={"Content-Disposition": f"inline; filename*=UTF-8''{safe_filename}"}
        )

    except HTTPException as e: raise e
    except Exception as e:
        logger.error(f"Public Download Error: {e}")
        raise HTTPException(status_code=500, detail="Download failed.")

@router.get("/public/{case_id}/invoices/{invoice_id}/download", tags=["Public Portal"])
async def download_public_invoice(
    case_id: str,
    invoice_id: str,
    db: Database = Depends(get_db)
):
    try:
        validate_object_id(case_id)
        invoice_oid = validate_object_id(invoice_id)
        
        invoice_doc = await asyncio.to_thread(db.invoices.find_one, {
            "_id": invoice_oid,
            "related_case_id": case_id,
            "status": {"$ne": "DRAFT"}
        })
        
        if not invoice_doc:
            raise HTTPException(status_code=404, detail="Invoice not found or not available.")

        invoice = InvoiceInDB(**invoice_doc)
        user_id = str(invoice_doc.get("owner_id"))
        
        pdf_buffer = await asyncio.to_thread(
            report_service.generate_invoice_pdf, 
            invoice=invoice, 
            db=db, 
            user_id=user_id
        )
        
        filename = f"Fatura_{invoice.invoice_number}.pdf"
        safe_filename = urllib.parse.quote(filename)
        
        return StreamingResponse(
            pdf_buffer, 
            media_type="application/pdf", 
            headers={"Content-Disposition": f"inline; filename*=UTF-8''{safe_filename}"}
        )

    except HTTPException as e: raise e
    except Exception as e:
        logger.error(f"Public Invoice Download Error: {e}")
        raise HTTPException(status_code=500, detail="Generation failed.")

@router.get("/public/{case_id}/logo", tags=["Public Portal"])
async def get_public_case_logo(
    case_id: str,
    db: Database = Depends(get_db)
):
    try:
        case_oid = validate_object_id(case_id)
        case = await asyncio.to_thread(db.cases.find_one, {"_id": case_oid})
        if not case: raise HTTPException(status_code=404, detail="Case not found")
        
        owner_id = case.get("owner_id") or case.get("user_id")
        if not owner_id: raise HTTPException(status_code=404, detail="Owner not found")
        
        query_id = owner_id
        if isinstance(query_id, str):
            try: query_id = ObjectId(query_id)
            except: pass
        
        profile = await asyncio.to_thread(db.business_profiles.find_one, {"user_id": query_id})
        if not profile and isinstance(owner_id, ObjectId):
             profile = await asyncio.to_thread(db.business_profiles.find_one, {"user_id": str(owner_id)})
             
        if not profile or "logo_storage_key" not in profile:
            raise HTTPException(status_code=404, detail="Logo not found")
        
        key = profile["logo_storage_key"]
        
        stream = await asyncio.to_thread(storage_service.get_file_stream, key)
        mime_type, _ = mimetypes.guess_type(key)
        
        return StreamingResponse(stream, media_type=mime_type or "image/png")

    except HTTPException as e: raise e
    except Exception as e:
        logger.error(f"Public Logo Error: {e}")
        raise HTTPException(status_code=404, detail="Logo not available")

@router.get("/{case_id}/graph/nodes/{node_id}/analysis", tags=["Analysis"])
async def get_node_analysis_endpoint(
    case_id: str,
    node_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    """
    REAL-TIME FORENSIC NODE ANALYSIS.
    Called when a user clicks a node in the graph.
    """
    validate_object_id(case_id)
    
    # 1. Run Analysis
    result = await asyncio.to_thread(
        analysis_service.analyze_node_context,
        db=db,
        case_id=case_id,
        node_id=node_id,
        user_id=str(current_user.id)
    )
    
    return JSONResponse(content=result)