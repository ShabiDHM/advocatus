# FILE: app/api/endpoints/cases/graph_router.py
# PHOENIX PROTOCOL - GRAPH ROUTER V6.0 (RENDER FREE TIER SAFE • SEMAPHORE 3 • ZERO-DATA-LOSS)

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated
from fastapi.responses import JSONResponse
from pymongo.database import Database
from bson import ObjectId
import asyncio
import io
import logging
from datetime import datetime, timezone

from app.services import storage_service
from app.services.ontology_service import ontology_service
from app.services.graph_service import graph_service, normalize_text_to_albanian
from app.models.user import UserInDB
from app.api.endpoints.dependencies import get_current_user, get_db
from app.api.endpoints.cases.cases_helpers import validate_object_id

logger = logging.getLogger(__name__)
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
        db.case_graphs.delete_one({"case_id": case_id})
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

    # 1. Lexo së pari nga depoja qendrore `db.case_graphs` (32 dokumentet e unifikuara)
    graph_record = db.case_graphs.find_one({"case_id": case_id})
    nodes = graph_record.get("nodes", []) if graph_record else []
    edges = graph_record.get("edges", []) if graph_record else []

    # 2. Nëse nuk ekziston në `db.case_graphs`, kontrollo te `db.cases.graph_data` ose Neo4j
    if not nodes:
        case = db.cases.find_one({"$or": [{"_id": case_oid}, {"_id": case_id}]})
        if case and case.get("graph_data"):
            raw_g = case["graph_data"]
            nodes = raw_g.get("nodes", [])
            edges = raw_g.get("edges") or raw_g.get("links") or []
        else:
            raw_g = await asyncio.to_thread(graph_service.get_case_graph, case_id)
            nodes = raw_g.get("nodes", [])
            edges = raw_g.get("edges") or raw_g.get("links") or []

    translated_nodes = []
    for n in nodes:
        translated_nodes.append({
            "id": n.get("id"),
            "label": normalize_text_to_albanian(n.get("label") or n.get("name") or "Entitet"),
            "type": n.get("type") or n.get("group") or "PERSON",
            "description": normalize_text_to_albanian(n.get("description", "")),
            "source_doc_ids": n.get("source_doc_ids", []),
            "metadata": n.get("metadata", {})
        })

    translated_edges = []
    for e in edges:
        translated_edges.append({
            "id": e.get("id") or f"{e.get('source')}_{e.get('target')}",
            "source": e.get("source"),
            "target": e.get("target"),
            "relation": normalize_text_to_albanian(e.get("relation") or e.get("label") or "LIDHJE_LIGJORE"),
            "amount_eur": e.get("amount_eur"),
            "date_iso": e.get("date_iso", ""),
            "evidence_text": normalize_text_to_albanian(e.get("evidence_text", "")),
            "source_doc_ids": e.get("source_doc_ids", [])
        })

    return {
        "case_id": case_id,
        "nodes": translated_nodes,
        "edges": translated_edges,
        "updated_at": (graph_record.get("updated_at") if graph_record else None) or datetime.now(timezone.utc).isoformat()
    }

@router.post("/{case_id}/graph/rebuild")
@router.post("/{case_id}/rebuild-graph")
async def rebuild_case_graph_endpoint(
    case_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    case_oid = validate_object_id(case_id)
    
    docs = list(db.documents.find({
        "$or": [{"case_id": case_id}, {"case_id": case_oid}],
        "status": {"$ne": "DELETED"}
    }))
    
    if not docs:
        db.cases.update_one(
            {"$or": [{"_id": case_oid}, {"_id": case_id}]},
            {"$unset": {"graph_data": "", "latest_analysis": "", "latest_deep_analysis": ""}}
        )
        db.case_graphs.delete_one({"case_id": case_id})
        try:
            await asyncio.to_thread(graph_service.delete_case_nodes, case_id)
        except Exception:
            pass
        return {"status": "success", "case_id": case_id, "nodes": [], "edges": []}

    logger.info(f"⚡ Duke nisur analizën paralele të lëndës {case_id} ({len(docs)} dokumente)...")

    # Kufizuesi i Sigurt për Render Free Tier: 3 thirrje paralele (RAM < 150MB, Koha ~45s)
    sem = asyncio.Semaphore(3)

    async def process_single_doc(doc: dict):
        doc_id = str(doc.get("_id"))
        doc_name = doc.get("file_name", "Dokument")
        txt = doc.get("extracted_text") or doc.get("text_content") or doc.get("summary") or ""
        
        if not txt.strip():
            return {"nodes": [], "edges": []}

        async with sem:
            try:
                extracted = await asyncio.to_thread(
                    ontology_service.extract_ontology_from_text,
                    text=txt,
                    doc_id=doc_id,
                    doc_name=doc_name
                )
                nodes_count = len(extracted.get("nodes", []))
                edges_count = len(extracted.get("edges", []))
                logger.info(f"✅ Dokumenti '{doc_name}': U nxorën {nodes_count} nyje dhe {edges_count} lidhje.")
                return extracted
            except Exception as e:
                logger.error(f"⚠️ Dështoi nxjerrja për '{doc_name}': {e}")
                return {"nodes": [], "edges": []}

    # Ekzekutimi paralel i të gjitha dokumenteve në grupe nga 3
    extraction_results = await asyncio.gather(*(process_single_doc(doc) for doc in docs))

    accumulated_nodes = []
    accumulated_edges = []

    # Bashkimi i të gjitha të dhënave në një graf të vetëm unifikues
    for extracted in extraction_results:
        new_nodes = extracted.get("nodes", [])
        new_edges = extracted.get("edges", [])
        accumulated_nodes, accumulated_edges = ontology_service.merge_graph_data(
            accumulated_nodes, accumulated_edges, new_nodes, new_edges
        )

    now_iso = datetime.now(timezone.utc).isoformat()
    final_graph = {
        "case_id": case_id,
        "owner_id": str(current_user.id),
        "nodes": accumulated_nodes,
        "edges": accumulated_edges,
        "updated_at": now_iso
    }

    # 1. Ruaj në `db.case_graphs` (Depoja e thellë e ontologjisë)
    db.case_graphs.update_one(
        {"case_id": case_id},
        {"$set": final_graph},
        upsert=True
    )

    # 2. Sinkronizo te `db.cases.graph_data`
    db.cases.update_one(
        {"$or": [{"_id": case_oid}, {"_id": case_id}]},
        {"$set": {"graph_data": final_graph, "updated_at": datetime.now(timezone.utc)}}
    )

    # 3. Sinkronizo me Neo4j (nëse instanca Aura është e lidhur)
    try:
        await asyncio.to_thread(graph_service.delete_case_nodes, case_id)
        for edge in accumulated_edges:
            await asyncio.to_thread(
                graph_service.create_evidence_edge,
                case_id=case_id,
                source_id=edge["source"],
                target_id=edge["target"],
                relation=edge["relation"],
                properties={
                    "evidence_text": edge.get("evidence_text", ""),
                    "amount_eur": edge.get("amount_eur"),
                    "date_iso": edge.get("date_iso", "")
                }
            )
    except Exception as neo_err:
        logger.warning(f"Neo4j sync bypass: {neo_err}")

    logger.info(f"🎉 Rindërtimi përfundoi me sukses: {len(accumulated_nodes)} nyje dhe {len(accumulated_edges)} lidhje të unifikuara nga {len(docs)} dokumente.")

    return {
        "status": "success",
        "case_id": case_id,
        "nodes": accumulated_nodes,
        "edges": accumulated_edges
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

    # 1. Gjenero Raportin PDF
    pdf_bytes = ontology_service.generate_court_report_pdf(db=db, case_id=case_id)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"Raporti_i_Ontologjise_{timestamp}.pdf"
    
    # 2. Ngarko në Cloud Storage (Backblaze B2)
    storage_key = await asyncio.to_thread(
        storage_service.upload_bytes_as_file,
        io.BytesIO(pdf_bytes),
        filename,
        str(current_user.id),
        case_id,
        "application/pdf"
    )

    # 3. Regjistro në Arkivin e Lëndës
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