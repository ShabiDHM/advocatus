# PHOENIX PROTOCOL - CASES ROUTER V3.7 (SYNTAX & TYPE FIX)
# 1. FIXED: 'case.title' -> 'case["title"]' to handle Dict returns safely.
# 2. FIXED: Verified all parenthesis closure.

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Body
from typing import List, Annotated, Dict, Any, Union
from fastapi.responses import Response, StreamingResponse, JSONResponse, FileResponse
from pydantic import BaseModel
from pymongo.database import Database
import redis
from bson import ObjectId
from bson.errors import InvalidId
import asyncio
import logging
import io
from datetime import datetime, timezone

# --- SERVICE IMPORTS ---
from ...services import (
    case_service,
    document_service,
    findings_service,
    report_service,
    storage_service,
    analysis_service,
    visual_service,
    archive_service,
    pdf_service,
    llm_service,
    drafting_service 
)

# --- MODEL IMPORTS ---
from ...models.case import CaseCreate, CaseOut
from ...models.user import UserInDB
from ...models.findings import FindingsListOut, FindingOut
from ...models.drafting import DraftRequest 
from ...models.archive import ArchiveItemOut 
from ...models.document import DocumentOut

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
    await asyncio.to_thread(case_service.delete_case_by_id, db=db, case_id=validated_case_id, owner=current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.post("/{case_id}/drafts", status_code=status.HTTP_202_ACCEPTED, tags=["Drafting"])
async def create_draft_for_case(case_id: str, job_in: DraftRequest, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    validated_case_id = validate_object_id(case_id)
    return await asyncio.to_thread(case_service.create_draft_job_for_case, db=db, case_id=validated_case_id, job_in=job_in, owner=current_user)

@router.get("/{case_id}/findings", response_model=FindingsListOut, tags=["Findings"])
async def get_findings_for_case(case_id: str, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    validate_object_id(case_id)
    findings_data = await asyncio.to_thread(findings_service.get_findings_for_case, db=db, case_id=case_id)
    await asyncio.to_thread(case_service.sync_case_calendar_from_findings, db=db, case_id=case_id, user_id=current_user.id)
    
    findings_out_list = []
    for finding in findings_data:
        findings_out_list.append(FindingOut.model_validate({
            'id': str(finding.get('_id')),
            'case_id': str(finding.get('case_id')),
            'document_id': str(finding.get('document_id')) if finding.get('document_id') else None,
            'finding_text': finding.get('finding_text', 'N/A'),
            'source_text': finding.get('source_text', 'N/A'),
            'page_number': finding.get('page_number'),
            'document_name': finding.get('document_name'),
            'confidence_score': finding.get('confidence_score', 0.0),
            'created_at': finding.get('created_at') or datetime.now(timezone.utc)
        }))
    return FindingsListOut(findings=findings_out_list, count=len(findings_out_list))

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

@router.get("/{case_id}/documents/{doc_id}", response_model=DocumentOut, tags=["Documents"])
async def get_document_by_id(case_id: str, doc_id: str, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    doc = await asyncio.to_thread(document_service.get_and_verify_document, db, doc_id, current_user)
    if str(doc.case_id) != case_id: raise HTTPException(status_code=403)
    return doc

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
    if str(target_doc.case_id) != case_id:
        raise HTTPException(status_code=403, detail="Access Denied.")
    
    if target_doc.litigation_analysis:
        return JSONResponse(content=target_doc.litigation_analysis)

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
    """
    Auto-Generates a formal objection (.docx) from the Analysis.
    """
    validated_case_id = validate_object_id(case_id)
    validated_doc_id = validate_object_id(doc_id)

    case = await asyncio.to_thread(case_service.get_case_by_id, db=db, case_id=validated_case_id, owner=current_user)
    if not case: raise HTTPException(status_code=404, detail="Case not found.")

    doc = await asyncio.to_thread(document_service.get_and_verify_document, db, doc_id, current_user)
    if str(doc.case_id) != case_id: raise HTTPException(status_code=403, detail="Access Denied.")

    if not doc.litigation_analysis:
        raise HTTPException(status_code=404, detail="No analysis available. Please run 'Kryqëzo Provat' first.")
    
    # SAFE TITLE ACCESS: Handle if 'case' is a Dict or Object
    title = case.get("title", "Lënda") if isinstance(case, dict) else getattr(case, "title", "Lënda")

    try:
        objection_bytes = await asyncio.to_thread(
            drafting_service.generate_objection_document,
            analysis_result=doc.litigation_analysis,
            case_title=title
        )
    except Exception as e:
        logger.error(f"Document generation failed: {e}")
        raise HTTPException(status_code=500, detail="Document generation failed.")

    filename = f"Kundërshtim_{doc.file_name}.docx"
    
    return StreamingResponse(
        io.BytesIO(objection_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

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

@router.delete("/{case_id}/documents/{doc_id}", tags=["Documents"])
async def delete_document(case_id: str, doc_id: str, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db), redis_client: redis.Redis = Depends(get_sync_redis)):
    document = await asyncio.to_thread(document_service.get_and_verify_document, db, doc_id, current_user)
    if str(document.case_id) != case_id: raise HTTPException(status_code=403)
    ids = await asyncio.to_thread(document_service.delete_document_by_id, db=db, redis_client=redis_client, doc_id=ObjectId(doc_id), owner=current_user)
    return JSONResponse(status_code=200, content={"documentId": doc_id, "deletedFindingIds": ids})

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
    return JSONResponse(content=await asyncio.to_thread(analysis_service.cross_examine_case, db=db, case_id=case_id))

@router.post("/{case_id}/documents/{doc_id}/deep-scan", tags=["Documents"])
async def deep_scan_document(case_id: str, doc_id: str, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    try:
        findings = await asyncio.to_thread(visual_service.perform_deep_scan, db, doc_id)
        return {"status": "success", "findings_count": len(findings)}
    except Exception as e: raise HTTPException(500, str(e))

@router.get("/public/{case_id}/timeline", tags=["Public Portal"])
async def get_public_case_timeline(case_id: str, db: Database = Depends(get_db)):
    try:
        validate_object_id(case_id)
        return await asyncio.to_thread(case_service.get_public_case_events, db=db, case_id=case_id)
    except Exception: raise HTTPException(404, "Portal not available.")