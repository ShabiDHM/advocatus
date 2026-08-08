# FILE: app/api/endpoints/cases/graph_router.py
# PHOENIX PROTOCOL - GRAPH ROUTER V3.0 (AUTO-SAVE PDF REPORT TO CASE ARCHIVE ENDPOINT)

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated
from fastapi.responses import JSONResponse
from pymongo.database import Database
from bson import ObjectId
import asyncio
import io
from datetime import datetime, timezone

from app.services import analysis_service, llm_service, storage_service
from app.services.ontology_service import ontology_service
from app.services.graph_service import graph_service, normalize_text_to_albanian
from app.models.user import UserInDB
from app.api.endpoints.dependencies import get_current_user, get_db
from app.api.endpoints.cases.cases_helpers import validate_object_id

router = APIRouter()

@router.get("/{case_id}/graph")
async def get_case_graph_endpoint(
    case_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    case_oid = validate_object_id(case_id)
    
    active_docs_count = db.documents.count_documents({
        "$or": [{"case_id": case_id}, {"case_id": case_oid}],
        "status": {"$ne": "DELETED"}
    })
    
    if active_docs_count == 0:
        db.cases.update_one(
            {"$or": [{"_id": case_oid}, {"_id": case_id}]}, 
            {"$unset": {"graph_data": "", "latest_analysis": "", "latest_deep_analysis": ""}}
        )
        try:
            await asyncio.to_thread(graph_service.delete_case_nodes, case_id)
        except Exception:
            pass

        return {
            "case_id": case_id,
            "nodes": [],
            "edges": [],
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

    case = db.cases.find_one({"$or": [{"_id": case_oid}, {"_id": case_id}]})
    if not case:
        raise HTTPException(status_code=404, detail="Rasti nuk u gjet.")

    raw_graph = case.get("graph_data")
    if not raw_graph or not raw_graph.get("nodes"):
        raw_graph = await asyncio.to_thread(graph_service.get_case_graph, case_id)

    nodes = raw_graph.get("nodes", [])
    edges = raw_graph.get("edges") or raw_graph.get("links") or []

    translated_nodes = []
    for n in nodes:
        translated_nodes.append({
            "id": n.get("id"),
            "label": normalize_text_to_albanian(n.get("label") or n.get("name") or "Entitet"),
            "type": n.get("type") or n.get("group") or "PERSON",
            "description": normalize_text_to_albanian(n.get("description", ""))
        })

    translated_edges = []
    for e in edges:
        translated_edges.append({
            "id": e.get("id") or f"{e.get('source')}_{e.get('target')}",
            "source": e.get("source"),
            "target": e.get("target"),
            "relation": normalize_text_to_albanian(e.get("relation") or e.get("label") or "LIDHJE_LIGJORE"),
            "amount_eur": e.get("amount_eur"),
            "evidence_text": normalize_text_to_albanian(e.get("evidence_text", ""))
        })

    return {
        "case_id": case_id,
        "nodes": translated_nodes,
        "edges": translated_edges,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }

@router.post("/{case_id}/graph/rebuild")
@router.post("/{case_id}/rebuild-graph")
async def rebuild_case_graph_endpoint(
    case_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    case_oid = validate_object_id(case_id)
    
    docs_cursor = list(db.documents.find({
        "$or": [{"case_id": case_id}, {"case_id": case_oid}],
        "status": {"$ne": "DELETED"}
    }))
    
    if len(docs_cursor) == 0:
        db.cases.update_one(
            {"$or": [{"_id": case_oid}, {"_id": case_id}]},
            {"$unset": {"graph_data": "", "latest_analysis": "", "latest_deep_analysis": ""}}
        )
        try:
            await asyncio.to_thread(graph_service.delete_case_nodes, case_id)
        except Exception:
            pass
        return {"status": "success", "case_id": case_id, "nodes": [], "edges": []}

    doc_text_blocks = []
    for doc in docs_cursor:
        doc_name = doc.get("file_name", "Dokument")
        txt = doc.get("extracted_text") or doc.get("text_content") or doc.get("summary") or ""
        if txt.strip():
            doc_text_blocks.append(f"=== DOKUMENTI: {doc_name} ===\n{txt}")

    master_context = "\n\n".join(doc_text_blocks)
    if not master_context.strip():
        master_context = await analysis_service._fetch_rag_context_async(db, case_id, str(current_user.id), False)

    new_graph = await llm_service.extract_case_graph_ontology(master_context)
    
    if new_graph and new_graph.get("nodes"):
        await asyncio.to_thread(
            db.cases.update_one,
            {"$or": [{"_id": case_oid}, {"_id": case_id}]},
            {"$set": {"graph_data": new_graph, "updated_at": datetime.now(timezone.utc)}}
        )

    return {
        "status": "success",
        "case_id": case_id,
        "nodes": new_graph.get("nodes", []),
        "edges": new_graph.get("edges", [])
    }

# --- SAVE PDF REPORT DIRECTLY TO CASE ARCHIVE ENDPOINT ---

@router.post("/{case_id}/graph/export")
@router.get("/{case_id}/graph/export")
async def export_and_archive_courtroom_graph_report(
    case_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    c_oid = validate_object_id(case_id)
    case_obj = db.cases.find_one({"$or": [{"_id": c_oid}, {"_id": case_id}]})
    if not case_obj:
        raise HTTPException(status_code=404, detail="Rasti nuk u gjet.")

    c_title = case_obj.get("title") or case_obj.get("name") or "Rast Ligjor"

    # 1. Generate Official PDF Report Bytes
    pdf_bytes = ontology_service.generate_court_report_pdf(db=db, case_id=case_id)
    filename = f"Raporti_i_Ontologjise_Gjyqesore_{case_id[:8]}.pdf"
    
    # 2. Upload PDF Bytes to Backblaze B2 Cloud Storage
    storage_key = await asyncio.to_thread(
        storage_service.upload_bytes_as_file,
        io.BytesIO(pdf_bytes),
        filename,
        str(current_user.id),
        case_id,
        "application/pdf"
    )

    # 3. Create Archive Item Record in db.archives
    user_oid = ObjectId(current_user.id) if ObjectId.is_valid(str(current_user.id)) else str(current_user.id)
    
    archive_item = {
        "user_id": user_oid,
        "owner_id": user_oid,
        "case_id": case_id,
        "case_oid": c_oid,
        "title": f"Raporti i Ontologjisë — {c_title}",
        "category": "RAPORTE",
        "item_type": "FILE",
        "file_type": "PDF",
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