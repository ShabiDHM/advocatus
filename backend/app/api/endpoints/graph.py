# FILE: backend/app/api/endpoints/graph.py
# PHOENIX PROTOCOL - MINI-FOUNDRY EVIDENCE GRAPH ENDPOINTS V4.0 (AUTO-SAVE PDF REPORT TO CASE ARCHIVE)

import logging
from typing import List, Dict, Any, Optional, Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, status, Response
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel, Field
from pymongo.database import Database
from bson import ObjectId
from bson.errors import InvalidId
import pypdf
import io
import asyncio
from datetime import datetime, timezone

from app.models.user import UserInDB
from app.services.ontology_service import ontology_service
from app.services import storage_service
from app.api.endpoints.dependencies import get_current_user, get_db

router = APIRouter()
logger = logging.getLogger(__name__)

def validate_object_id(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Mënyrë e pasaktë e ID-së së rastit (Invalid ObjectId).")

def verify_case_ownership(db: Database, case_id: str, user_id: str) -> bool:
    try:
        c_oid = validate_object_id(case_id)
        case = db.cases.find_one({"_id": c_oid})
        if not case:
            return False
        owner_id = str(case.get("owner_id") or case.get("user_id") or case.get("owner") or "")
        return owner_id == str(user_id)
    except Exception as e:
        logger.error(f"Error checking case access: {e}")
        return False


# --- PYDANTIC REQUEST & RESPONSE MODELS ---

class OntologyNodeOut(BaseModel):
    id: str
    label: str
    type: str
    description: Optional[str] = ""
    source_doc_ids: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class OntologyEdgeOut(BaseModel):
    id: str
    source: str
    target: str
    relation: str
    amount_eur: Optional[float] = None
    date_iso: Optional[str] = ""
    evidence_text: Optional[str] = ""
    source_doc_ids: List[str] = Field(default_factory=list)

class CaseGraphResponse(BaseModel):
    case_id: str
    nodes: List[OntologyNodeOut]
    edges: List[OntologyEdgeOut]
    updated_at: Optional[str] = None

class CrossCaseMatchOut(BaseModel):
    case_id: str
    case_title: str
    matched_entity: OntologyNodeOut
    connected_edges: List[OntologyEdgeOut]

class RebuildGraphResponse(BaseModel):
    status: str
    message: str
    total_documents: int

class MergeNodesRequest(BaseModel):
    primary_id: str
    secondary_id: str

class CustomEdgeRequest(BaseModel):
    source: str
    target: str
    relation: str
    evidence_text: Optional[str] = ""
    amount_eur: Optional[float] = None


# --- BACKGROUND WORKER HELPER ---

def _rebuild_case_graph_background(case_id: str, owner_id: str, db_instance: Database):
    """
    Scans case documents. Fetches full text from MongoDB 'user_vectors' collection
    where OCR chunks are stored.
    """
    try:
        case_oid = ObjectId(case_id)
        docs = list(db_instance.documents.find({"case_id": case_oid}))
        logger.info(f"Starting background graph rebuild for case {case_id} across {len(docs)} documents.")

        for doc in docs:
            doc_id = str(doc["_id"])
            doc_name = doc.get("file_name") or doc.get("title") or "Dokument"
            doc_oid = ObjectId(doc_id)
            
            chunks = list(db_instance.user_vectors.find({
                "$or": [
                    {"document_id": doc_id},
                    {"document_id": doc_oid},
                    {"case_id": case_id}
                ]
            }))

            text_content = ""
            if chunks:
                chunk_texts = [
                    str(c.get("text") or c.get("content") or "")
                    for c in chunks if (c.get("text") or c.get("content"))
                ]
                text_content = "\n\n".join(chunk_texts).strip()
                logger.info(f"✅ [user_vectors Chunks Found] Retrieved {len(chunks)} chunks ({len(text_content)} chars) for doc {doc_id}")

            if not text_content or len(text_content.strip()) < 100:
                text_content = doc.get("extracted_text") or doc.get("ocr_text") or doc.get("text_content") or ""

            if not text_content or len(text_content.strip()) < 100:
                storage_key = doc.get("storage_key") or doc.get("preview_storage_key")
                if storage_key:
                    try:
                        stream = storage_service.get_file_stream(storage_key)
                        if stream:
                            pdf_bytes = stream.read()
                            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
                            extracted_parts = [p.extract_text() or "" for p in reader.pages if p.extract_text()]
                            text_content = "\n\n".join(extracted_parts).strip()
                    except Exception as err:
                        logger.error(f"❌ Storage fetch failed for doc {doc_id}: {err}")

            if text_content and len(text_content.strip()) > 30:
                db_instance.documents.update_one(
                    {"_id": doc_oid},
                    {"$set": {"text_content": text_content, "extracted_text": text_content}}
                )

                logger.info(f"🚀 Sending {len(text_content)} chars of OCR/text to DeepSeek ontology builder for doc {doc_id}...")
                ontology_service.process_and_save_document_ontology(
                    db=db_instance,
                    case_id=case_id,
                    owner_id=owner_id,
                    doc_id=doc_id,
                    doc_name=doc_name,
                    text=text_content
                )
        logger.info(f"✅ Background graph rebuild completed for case {case_id}")
    except Exception as e:
        logger.error(f"❌ Background graph rebuild failed for case {case_id}: {e}")


# --- API ENDPOINTS ---

@router.get("/firm/graph/search", response_model=List[CrossCaseMatchOut])
async def search_firm_cross_case_graph(
    query: Annotated[str, Query(..., min_length=2, description="Emri i entitetit, personit, apo nr. i llogarisë për kërkim në të gjitha lëndët")],
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    matches = ontology_service.search_cross_case_entities(
        db=db,
        owner_id=str(current_user.id),
        query=query
    )
    return matches


@router.get("/{case_id}/graph", response_model=CaseGraphResponse)
async def get_case_evidence_graph(
    case_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    validate_object_id(case_id)
    
    if not verify_case_ownership(db, case_id, str(current_user.id)):
        raise HTTPException(status_code=403, detail="Nuk keni leje të qaseni në këtë rast.")

    graph_data = ontology_service.get_case_graph(db, case_id)
    return CaseGraphResponse(
        case_id=case_id,
        nodes=graph_data.get("nodes", []),
        edges=graph_data.get("edges", []),
        updated_at=graph_data.get("updated_at")
    )


@router.post("/{case_id}/graph/rebuild", response_model=RebuildGraphResponse, status_code=status.HTTP_202_ACCEPTED)
async def rebuild_case_evidence_graph(
    case_id: str,
    background_tasks: BackgroundTasks,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    c_oid = validate_object_id(case_id)
    if not verify_case_ownership(db, case_id, str(current_user.id)):
        raise HTTPException(status_code=403, detail="Nuk keni leje të qaseni në këtë rast.")

    total_docs = db.documents.count_documents({"case_id": c_oid})
    if total_docs == 0:
        return RebuildGraphResponse(
            status="warning",
            message="Rasti nuk ka asnjë dokument të ngarkuar për të ndërtuar grafikun.",
            total_documents=0
        )

    background_tasks.add_task(
        _rebuild_case_graph_background,
        case_id=case_id,
        owner_id=str(current_user.id),
        db_instance=db
    )

    return RebuildGraphResponse(
        status="processing",
        message=f"Procesimi i grafikut të provave filloi në prapavijë për {total_docs} dokumente.",
        total_documents=total_docs
    )


@router.post("/{case_id}/graph/nodes/merge")
async def merge_entity_nodes(
    case_id: str,
    body: MergeNodesRequest,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    validate_object_id(case_id)
    if not verify_case_ownership(db, case_id, str(current_user.id)):
        raise HTTPException(status_code=403, detail="Nuk keni leje të qaseni në këtë rast.")

    result = ontology_service.merge_case_nodes(
        db=db,
        case_id=case_id,
        primary_id=body.primary_id,
        secondary_id=body.secondary_id
    )

    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))

    return result


@router.post("/{case_id}/graph/edges")
async def create_custom_edge(
    case_id: str,
    body: CustomEdgeRequest,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    validate_object_id(case_id)
    if not verify_case_ownership(db, case_id, str(current_user.id)):
        raise HTTPException(status_code=403, detail="Nuk keni leje të qaseni në këtë rast.")

    result = ontology_service.add_custom_edge(
        db=db,
        case_id=case_id,
        source_id=body.source,
        target_id=body.target,
        relation=body.relation,
        evidence_text=body.evidence_text or "",
        amount_eur=body.amount_eur
    )

    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))

    return result


# --- SAVE PDF REPORT TO CASE ARCHIVE ENDPOINT ---

@router.post("/{case_id}/graph/export")
@router.get("/{case_id}/graph/export")
async def archive_courtroom_graph_report(
    case_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    c_oid = validate_object_id(case_id)
    if not verify_case_ownership(db, case_id, str(current_user.id)):
        raise HTTPException(status_code=403, detail="Nuk keni leje të qaseni në këtë rast.")

    case_obj = db.cases.find_one({"_id": c_oid})
    c_title = case_obj.get("title") or case_obj.get("name") or "Rast Ligjor" if case_obj else "Rast Ligjor"

    # 1. Generate Official PDF Report Bytes
    pdf_bytes = ontology_service.generate_court_report_pdf(db=db, case_id=case_id)
    filename = f"Raporti_i_Ontologjise_Gjyqesore_{case_id[:8]}.pdf"
    
    # 2. Upload PDF to Backblaze B2 Storage
    storage_key = await asyncio.to_thread(
        storage_service.upload_bytes_as_file,
        io.BytesIO(pdf_bytes),
        filename,
        str(current_user.id),
        case_id,
        "application/pdf"
    )

    # 3. Create Archive Record in db.archives
    archive_item = {
        "owner_id": ObjectId(current_user.id),
        "case_id": c_oid,
        "title": f"Raporti i Ontologjisë — {c_title}",
        "category": "RAPORTE",
        "storage_key": storage_key,
        "file_name": filename,
        "mime_type": "application/pdf",
        "is_shared": False,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    
    res = await asyncio.to_thread(db.archives.insert_one, archive_item)
    archive_id_str = str(res.inserted_id)

    return JSONResponse(
        content={
            "status": "success",
            "message": "Raporti PDF i Ontologjisë u ruajt me sukses në Arkivin e Lëndës.",
            "archive_id": archive_id_str,
            "file_name": filename,
            "title": f"Raporti i Ontologjisë — {c_title}"
        },
        status_code=status.HTTP_201_CREATED
    )