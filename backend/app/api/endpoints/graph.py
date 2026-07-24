# FILE: backend/app/api/endpoints/graph.py
# PHOENIX PROTOCOL - MINI-FOUNDRY EVIDENCE GRAPH ENDPOINTS V2.0
# Endpoints for Case Graphing, Node Merging, Manual Connections, Cross-Case Intelligence, & Court PDF Exports

import logging
from typing import List, Dict, Any, Optional, Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, status, Response
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field
from pymongo.database import Database
from bson import ObjectId
from bson.errors import InvalidId

from app.models.user import UserInDB
from app.services.ontology_service import ontology_service
from app.api.endpoints.dependencies import get_current_user, get_db

router = APIRouter()
logger = logging.getLogger(__name__)

def validate_object_id(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Mënyrë e pasaktë e ID-së së rastit (Invalid ObjectId).")

def verify_case_ownership(db: Database, case_id: str, user_id: str) -> bool:
    """
    Verifies that the requested case exists and belongs to the authenticated user/firm.
    """
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
    type: str  # PERSON, ORGANIZATION, ACCOUNT, LOCATION, EVENT, DOCUMENT
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
    Scans all documents belonging to the case and rebuilds the case ontology graph.
    """
    try:
        case_oid = ObjectId(case_id)
        docs = list(db_instance.documents.find({"case_id": case_oid}))
        logger.info(f"Starting background graph rebuild for case {case_id} across {len(docs)} documents.")

        for doc in docs:
            doc_id = str(doc["_id"])
            doc_name = doc.get("file_name") or doc.get("title") or "Dokument"
            text_content = doc.get("text_content") or doc.get("extracted_text") or doc.get("ocr_text") or ""

            if text_content and len(text_content.strip()) > 50:
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
    """
    Cross-case intelligence endpoint: Searches all cases in the firm for an entity,
    identifying if a witness, company, or account has appeared elsewhere.
    """
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
    """
    Retrieves the Palantir-style Evidence Graph (nodes & edges) for a specific case.
    """
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
    """
    Triggers an automated background rebuild/refresh of the case evidence graph across all case documents.
    """
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
    """
    Merges two entity nodes into one master node and updates all connected edges.
    """
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
    """
    Allows an attorney to manually connect two entities with a custom legal edge.
    """
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


@router.get("/{case_id}/graph/export")
async def download_courtroom_graph_report(
    case_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    """
    Exports a court-ready, stamped official evidence graph report in text/PDF format.
    """
    validate_object_id(case_id)
    if not verify_case_ownership(db, case_id, str(current_user.id)):
        raise HTTPException(status_code=403, detail="Nuk keni leje të qaseni në këtë rast.")

    report_bytes = ontology_service.generate_court_report_pdf(db=db, case_id=case_id)
    
    filename = f"Raporti_i_Ontologjise_Gjyqesore_{case_id[:8]}.txt"
    return Response(
        content=report_bytes,
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )