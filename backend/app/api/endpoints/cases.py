# FILE: backend/app/api/endpoints/cases.py
# PHOENIX PROTOCOL - CASES ROUTER V30.0 (CLEAN BACKGROUND LIFECYCLE)
# 1. FIX: Only passes document_id string to BackgroundTasks to prevent closed-connection crashes.

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Body, BackgroundTasks
from typing import List, Annotated, Dict, Any
from fastapi.responses import Response, StreamingResponse, JSONResponse
from pydantic import BaseModel
from pymongo.database import Database
import redis
from bson import ObjectId
from bson.errors import InvalidId
import asyncio, logging, io
from datetime import datetime, timezone

from ...services import case_service, document_service, storage_service, analysis_service, archive_service, pdf_service, drafting_service, spreadsheet_service, llm_service
from ...services.graph_service import graph_service
from ...models.case import CaseCreate, CaseOut
from ...models.user import UserInDB, SubscriptionTier
from ...models.drafting import DraftRequest
from ...models.archive import ArchiveItemOut
from ...models.document import DocumentOut
from ...models.chat import ChatMessage
from .dependencies import get_current_user, get_db, get_sync_redis

router = APIRouter()
logger = logging.getLogger(__name__)

def validate_object_id(id_str: str) -> ObjectId:
    try: return ObjectId(id_str)
    except InvalidId: raise HTTPException(status_code=400, detail="Invalid ID format.")

@router.post("/{case_id}/documents/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_document_for_case(
    case_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Database = Depends(get_db)
):
    pdf_bytes, filename = await pdf_service.pdf_service.process_and_brand_pdf(file, case_id)
    key = await asyncio.to_thread(storage_service.upload_bytes_as_file, io.BytesIO(pdf_bytes), filename, str(current_user.id), case_id, "application/pdf")

    doc = document_service.create_document_record(db=db, owner=current_user, case_id=case_id, file_name=filename, storage_key=key, mime_type="application/pdf")

    # PHOENIX FIX: Pass ONLY the ID string. The orchestrator will create its own DB connection.
    from ...services.document_processing_service import orchestrate_document_processing_mongo
    background_tasks.add_task(orchestrate_document_processing_mongo, str(doc.id))

    return DocumentOut.model_validate(doc)

# --- Keep rest of original endpoints intact ---
@router.get("", response_model=List[CaseOut], include_in_schema=False)
async def get_user_cases(current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    return await asyncio.to_thread(case_service.get_cases_for_user, db=db, owner=current_user)

@router.get("/{case_id}", response_model=CaseOut)
async def get_single_case(case_id: str, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db)):
    case = await asyncio.to_thread(case_service.get_case_by_id, db=db, case_id=validate_object_id(case_id), owner=current_user)
    if not case: raise HTTPException(status_code=404)
    return case

@router.delete("/{case_id}/documents/{doc_id}")
async def delete_document(case_id: str, doc_id: str, current_user: Annotated[UserInDB, Depends(get_current_user)], db: Database = Depends(get_db), redis_client: redis.Redis = Depends(get_sync_redis)):
    doc = await asyncio.to_thread(document_service.get_and_verify_document, db, doc_id, current_user)
    if str(doc.case_id) != case_id: raise HTTPException(status_code=403)
    result = await asyncio.to_thread(document_service.bulk_delete_documents, db=db, redis_client=redis_client, document_ids=[doc_id], owner=current_user)
    return {"status": "deleted"}