# FILE: backend/app/api/endpoints/cases.py

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from typing import List, Annotated
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
from pymongo.database import Database
import redis
from bson import ObjectId
from bson.errors import InvalidId
import asyncio
import logging

from ...services import case_service, document_service, findings_service, report_service
from ...models.case import CaseCreate, CaseOut
from ...models.user import UserInDB
from ...models.document import DocumentOut
from ...models.findings import FindingsListOut, FindingOut
from .dependencies import get_current_active_user, get_db, get_sync_redis
from ...celery_app import celery_app

router = APIRouter(prefix="/cases", tags=["Cases"])
logger = logging.getLogger(__name__)

class DocumentContentOut(BaseModel):
    text: str

def validate_object_id(id_str: str) -> ObjectId:
    try: return ObjectId(id_str)
    except InvalidId: raise HTTPException(status_code=400, detail="Invalid ID format.")

@router.get("", response_model=List[CaseOut], include_in_schema=False)
@router.get("/", response_model=List[CaseOut])
async def get_user_cases(current_user: Annotated[UserInDB, Depends(get_current_active_user)], db: Database = Depends(get_db)):
    return await asyncio.to_thread(case_service.get_cases_for_user, db=db, owner=current_user)

@router.post("", response_model=CaseOut, status_code=status.HTTP_201_CREATED, include_in_schema=False)
@router.post("/", response_model=CaseOut, status_code=status.HTTP_201_CREATED)
async def create_new_case(case_in: CaseCreate, current_user: Annotated[UserInDB, Depends(get_current_active_user)], db: Database = Depends(get_db)):
    return await asyncio.to_thread(case_service.create_case, db=db, case_in=case_in, owner=current_user)

@router.get("/{case_id}", response_model=CaseOut)
async def get_single_case(case_id: str, current_user: Annotated[UserInDB, Depends(get_current_active_user)], db: Database = Depends(get_db)):
    validated_case_id = validate_object_id(case_id)
    case = await asyncio.to_thread(case_service.get_case_by_id, db=db, case_id=validated_case_id, owner=current_user)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")
    return case

@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case(case_id: str, current_user: Annotated[UserInDB, Depends(get_current_active_user)], db: Database = Depends(get_db)):
    validated_case_id = validate_object_id(case_id)
    await asyncio.to_thread(case_service.delete_case_by_id, db=db, case_id=validated_case_id, owner=current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.get("/{case_id}/findings", response_model=FindingsListOut, tags=["Findings"])
async def get_findings_for_case(case_id: str, current_user: Annotated[UserInDB, Depends(get_current_active_user)], db: Database = Depends(get_db)):
    validate_object_id(case_id)
    findings_data = await asyncio.to_thread(findings_service.get_findings_for_case, db=db, case_id=case_id)
    findings_out_list = [
        FindingOut.model_validate({
            'id': str(finding.get('_id')), 'case_id': str(finding.get('case_id')),
            'finding_text': finding.get('finding_text', 'N/A'), 'source_text': finding.get('source_text', 'N/A'),
            'page_number': finding.get('page_number'), 'document_name': finding.get('document_name'),
            'confidence_score': finding.get('confidence_score', 0.0),
        }) for finding in findings_data
    ]
    return FindingsListOut(findings=findings_out_list, count=len(findings_out_list))

@router.get("/{case_id}/documents", response_model=List[DocumentOut], tags=["Documents"])
async def get_documents_for_case(case_id: str, current_user: Annotated[UserInDB, Depends(get_current_active_user)], db: Database = Depends(get_db)):
    return await asyncio.to_thread(document_service.get_documents_by_case_id, db, case_id, current_user)

@router.post("/{case_id}/documents/upload", status_code=status.HTTP_202_ACCEPTED, tags=["Documents"])
async def upload_document_for_case(case_id: str, current_user: Annotated[UserInDB, Depends(get_current_active_user)], file: UploadFile = File(...), db: Database = Depends(get_db)):
    file_name = file.filename or "untitled_upload"
    mime_type = file.content_type or "application/octet-stream"
    try:
        storage_key = await asyncio.to_thread(document_service.storage_service.upload_original_document, file=file, user_id=str(current_user.id), case_id=case_id)
        new_document = document_service.create_document_record(db=db, owner=current_user, case_id=case_id, file_name=file_name, storage_key=storage_key, mime_type=mime_type)
        celery_app.send_task("process_document_task", args=[str(new_document.id)])
        return DocumentOut.model_validate(new_document)
    except Exception as e:
        logger.error(f"CRITICAL UPLOAD FAILURE for case {case_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Document upload failed.")

@router.get("/{case_id}/documents/{doc_id}", response_model=DocumentOut, tags=["Documents"])
async def get_document_by_id(case_id: str, doc_id: str, current_user: Annotated[UserInDB, Depends(get_current_active_user)], db: Database = Depends(get_db)):
    document = await asyncio.to_thread(document_service.get_and_verify_document, db, doc_id, current_user)
    if str(document.case_id) != case_id: raise HTTPException(status_code=403, detail="Document does not belong to the specified case.")
    return document

@router.get("/{case_id}/documents/{doc_id}/original", tags=["Documents"], response_class=StreamingResponse)
async def get_original_document(
    case_id: str, 
    doc_id: str, 
    current_user: Annotated[UserInDB, Depends(get_current_active_user)], 
    db: Database = Depends(get_db)
):
    try:
        file_stream, document = await asyncio.to_thread(
            document_service.get_original_document_stream, db, doc_id, current_user
        )
        if str(document.case_id) != case_id:
            raise HTTPException(status_code=403, detail="Document does not belong to the specified case.")
        headers = {'Content-Disposition': f'inline; filename="{document.file_name}"'}
        return StreamingResponse(file_stream, media_type=document.mime_type, headers=headers)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Failed to stream original document {doc_id} for case {case_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not retrieve the document file.")

@router.get("/{case_id}/documents/{doc_id}/content", response_model=DocumentContentOut, tags=["Documents"])
async def get_document_content(case_id: str, doc_id: str, current_user: Annotated[UserInDB, Depends(get_current_active_user)], db: Database = Depends(get_db)):
    document = await asyncio.to_thread(document_service.get_and_verify_document, db, doc_id, current_user)
    if str(document.case_id) != case_id: raise HTTPException(status_code=403, detail="Document does not belong to the specified case.")
    if not document.processed_text_storage_key: raise HTTPException(status_code=404, detail="Document content not available.")
    content = await asyncio.to_thread(document_service.get_document_content_by_key, storage_key=document.processed_text_storage_key)
    if content is None: raise HTTPException(status_code=404, detail="Document content not found in storage.")
    return DocumentContentOut(text=content)

@router.get("/{case_id}/documents/{doc_id}/report", tags=["Documents"])
async def get_document_report_pdf(case_id: str, doc_id: str, current_user: Annotated[UserInDB, Depends(get_current_active_user)], db: Database = Depends(get_db)):
    document = await asyncio.to_thread(document_service.get_and_verify_document, db, doc_id, current_user)
    if str(document.case_id) != case_id: raise HTTPException(status_code=403, detail="Document does not belong to the specified case.")
    if not document.processed_text_storage_key: raise HTTPException(status_code=404, detail="Document content not available for report.")
    content = await asyncio.to_thread(document_service.get_document_content_by_key, storage_key=document.processed_text_storage_key)
    if content is None: raise HTTPException(status_code=404, detail="Document content not found in storage.")
    pdf_buffer = await asyncio.to_thread(report_service.create_pdf_from_text, text=content, document_title=document.file_name)
    headers = {'Content-Disposition': f'inline; filename="{document.file_name}.pdf"'}
    return StreamingResponse(pdf_buffer, media_type="application/pdf", headers=headers)

@router.delete("/{case_id}/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Documents"])
async def delete_document(case_id: str, doc_id: str, current_user: Annotated[UserInDB, Depends(get_current_active_user)], db: Database = Depends(get_db), redis_client: redis.Redis = Depends(get_sync_redis)):
    validated_doc_id = validate_object_id(doc_id)
    await asyncio.to_thread(document_service.delete_document_by_id, db=db, redis_client=redis_client, doc_id=validated_doc_id, owner=current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)