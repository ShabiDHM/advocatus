# FILE: backend/app/api/endpoints/forensic/document_router.py
# PHOENIX PROTOCOL - FORENSIC DOCUMENT ROUTER V1.7 (ADDED EXTRACTED TEXT ENDPOINT)
# 100% COMPLETE CODE • ZERO PY WARNINGS • RBAC PROTECTED

import os
import io
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import StreamingResponse, PlainTextResponse
from pymongo.database import Database
from bson import ObjectId
from pydantic import BaseModel, Field

from app.core.db import get_db
from app.api.endpoints.dependencies import get_current_forensic_user
from app.models.user import UserInDB
from app.services import storage_service
from app.services.text_extraction_service import text_extraction_service
from app.services.forensic.forensic_chain_of_custody import generate_evidence_hash, create_custody_stamp
from app.services.forensic.forensic_audit_service import log_forensic_action
from app.services.forensic.forensic_llm_service import call_forensic_llm
from app.services.pdf_service import pdf_service

router = APIRouter(prefix="/documents", tags=["Forensic Documents"])
logger = logging.getLogger(__name__)

FORENSIC_DOCS_COLLECTION = "forensic_documents"

class GeneratePillarRequest(BaseModel):
    pillar: str = Field(..., description="PILLAR_1, PILLAR_2, ose PILLAR_3")
    prompt: str = Field(..., min_length=10)

class RenameDocRequest(BaseModel):
    new_name: str = Field(..., min_length=1)

def _serialize_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    doc["id"] = str(doc["_id"])
    doc["_id"] = str(doc["_id"])
    doc["case_id"] = str(doc.get("case_id", ""))
    doc["owner_id"] = str(doc.get("owner_id", ""))
    if isinstance(doc.get("created_at"), datetime):
        doc["created_at"] = doc["created_at"].isoformat()
    return doc

# ==========================================================
# 1. NGARKIMI I SHKRESËS ME VULË TË MENJËHERSHME DHE OCR
# ==========================================================
@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_forensic_document(
    case_id: str = Form(...),
    file: UploadFile = File(...),
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db)
):
    user_id = str(current_user.id)
    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Skedari i shkresës është i zbrazët.")

    filename = storage_service.sanitize_filename(file.filename or "dokument.pdf")
    content_type = file.content_type or "application/pdf"

    evidence_sha256 = generate_evidence_hash(raw_bytes)

    storage_key = await asyncio.to_thread(
        storage_service.upload_bytes_as_file,
        io.BytesIO(raw_bytes),
        filename,
        user_id,
        case_id,
        content_type
    )

    custody_stamp = create_custody_stamp(
        user_id=user_id,
        case_id=case_id,
        action="FORENSIC_DOCUMENT_SECURED",
        evidence_ids=[evidence_sha256],
        metadata={"filename": filename, "file_size_bytes": len(raw_bytes)}
    )

    extracted_text = ""
    try:
        extracted_text = await asyncio.to_thread(
            text_extraction_service.extract_text,
            raw_bytes,
            filename
        )
    except Exception as ocr_err:
        logger.warning(f"OCR warning: {ocr_err}")

    now = datetime.now(timezone.utc)
    doc = {
        "case_id": case_id,
        "owner_id": user_id,
        "file_name": filename,
        "storage_key": storage_key,
        "mime_type": content_type,
        "status": "READY",
        "evidence_sha256": evidence_sha256,
        "custody_stamp": custody_stamp,
        "extracted_text": extracted_text or "",
        "forensic_pillars": {},
        "created_at": now,
        "updated_at": now
    }

    result = db[FORENSIC_DOCS_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id

    log_forensic_action(
        db=db,
        user_id=user_id,
        case_id=case_id,
        action="DOCUMENT_EVIDENCE_ACQUIRED",
        details={
            "filename": filename,
            "sha256": evidence_sha256,
            "custody_hash": custody_stamp["custody_hash"]
        }
    )

    return _serialize_doc(doc)

# ==========================================================
# 2. LISTIMI I SHKRESAVE (PËRFSHIN EDHE TË ARKIVUARA)
# ==========================================================
@router.get("/{case_id}/list")
def list_forensic_documents(
    case_id: str,
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db)
):
    cursor = db[FORENSIC_DOCS_COLLECTION].find({
        "case_id": str(case_id),
        "status": {"$ne": "DELETED"}
    }).sort("created_at", -1)
    items = [_serialize_doc(d) for d in cursor]

    try:
        case_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
        legacy_cursor = db.documents.find({
            "$or": [{"case_id": case_oid}, {"case_id": str(case_id)}],
            "status": {"$ne": "DELETED"}
        }).sort("created_at", -1)
        for leg in legacy_cursor:
            items.append(_serialize_doc(leg))
    except Exception:
        pass

    return items

# ==========================================================
# 3. SHTJELLAT FORENZIKE (CLAUDE SONNET 4.6)
# ==========================================================
@router.get("/{case_id}/{doc_id}/pillars")
def get_forensic_doc_pillars(
    case_id: str,
    doc_id: str,
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db)
):
    doc = None
    if ObjectId.is_valid(doc_id):
        doc = db[FORENSIC_DOCS_COLLECTION].find_one({"_id": ObjectId(doc_id)})
        if not doc:
            doc = db.documents.find_one({"_id": ObjectId(doc_id)})

    if not doc:
        raise HTTPException(status_code=404, detail="Dokumenti nuk u gjet.")

    return doc.get("forensic_pillars", {}) or {}

@router.post("/{case_id}/{doc_id}/pillars")
def generate_and_save_doc_pillar(
    case_id: str,
    doc_id: str,
    payload: GeneratePillarRequest,
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db)
):
    user_id = str(current_user.id)
    doc = None
    target_coll = FORENSIC_DOCS_COLLECTION
    if ObjectId.is_valid(doc_id):
        doc = db[FORENSIC_DOCS_COLLECTION].find_one({"_id": ObjectId(doc_id)})
        if not doc:
            doc = db.documents.find_one({"_id": ObjectId(doc_id)})
            target_coll = "documents"

    if not doc:
        raise HTTPException(status_code=404, detail="Dokumenti nuk u gjet.")

    pillar_key = payload.pillar.strip().upper()
    doc_text = (doc.get("extracted_text") or doc.get("content") or "")[:25000]

    system_prompt = f"""EKSPERTIZA DOKTRINARE E SHKRESËS ({pillar_key}) - CLAUDE SONNET 4.6:
Ju jeni Konsulenca Supreme Ligjore e autorizuar për Republikën e Kosovës.
Analizoni tekstin e shkresës me saktësi kirurgjikale dhe nene të sakta të ligjit pozitiv."""

    user_content = f"""DOKUMENTI: {doc.get('file_name', 'Dokument')}

DIREKTIVA E KËRKUAR:
{payload.prompt}

TEKSTI I SHKRESËS:
{doc_text}"""

    content = call_forensic_llm(
        system_prompt=system_prompt,
        user_content=user_content,
        temperature=0.0
    )

    now = datetime.now(timezone.utc)
    db[target_coll].update_one(
        {"_id": doc["_id"]},
        {"$set": {
            f"forensic_pillars.{pillar_key}": content,
            "updated_at": now
        }}
    )

    log_forensic_action(
        db=db,
        user_id=user_id,
        case_id=case_id,
        action="DOCUMENT_PILLAR_ANALYZED",
        details={"doc_name": doc.get("file_name"), "pillar": pillar_key}
    )

    return {"status": "success", "pillar": pillar_key, "content": content}

@router.delete("/{case_id}/{doc_id}/pillars/{pillar}", status_code=status.HTTP_200_OK)
def delete_forensic_doc_pillar(
    case_id: str,
    doc_id: str,
    pillar: str,
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db)
):
    pillar_key = pillar.strip().upper()
    if ObjectId.is_valid(doc_id):
        db[FORENSIC_DOCS_COLLECTION].update_one(
            {"_id": ObjectId(doc_id)},
            {"$unset": {f"forensic_pillars.{pillar_key}": ""}}
        )
        db.documents.update_one(
            {"_id": ObjectId(doc_id)},
            {"$unset": {f"forensic_pillars.{pillar_key}": ""}}
        )

    return {"status": "success", "message": f"Shtjella {pillar_key} u asgjësua nga MongoDB."}

# ==========================================================
# 4. FSHIRJA, RIEMËRTIMI DHE ARKIVIMI
# ==========================================================
@router.delete("/{case_id}/{doc_id}", status_code=status.HTTP_200_OK)
def delete_forensic_document(
    case_id: str,
    doc_id: str,
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db)
):
    user_id = str(current_user.id)
    doc = None
    if ObjectId.is_valid(doc_id):
        doc = db[FORENSIC_DOCS_COLLECTION].find_one({"_id": ObjectId(doc_id)})
        if doc:
            db[FORENSIC_DOCS_COLLECTION].delete_one({"_id": ObjectId(doc_id)})
        else:
            doc = db.documents.find_one({"_id": ObjectId(doc_id)})
            if doc:
                db.documents.delete_one({"_id": ObjectId(doc_id)})

    if not doc:
        raise HTTPException(status_code=404, detail="Dokumenti nuk u gjet.")

    storage_key = doc.get("storage_key")
    if storage_key:
        try:
            storage_service.delete_file(storage_key)
        except Exception:
            pass

    log_forensic_action(
        db=db,
        user_id=user_id,
        case_id=case_id,
        action="DOCUMENT_EVIDENCE_PURGED",
        details={"file_name": doc.get("file_name", "")}
    )

    return {"status": "success", "message": "Dokumenti u asgjësua nga dosja forenzike."}

@router.put("/{case_id}/{doc_id}/rename", status_code=status.HTTP_200_OK)
def rename_forensic_document(
    case_id: str,
    doc_id: str,
    payload: RenameDocRequest,
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db)
):
    new_name = payload.new_name.strip()
    if ObjectId.is_valid(doc_id):
        db[FORENSIC_DOCS_COLLECTION].update_one(
            {"_id": ObjectId(doc_id)},
            {"$set": {"file_name": new_name, "updated_at": datetime.now(timezone.utc)}}
        )
        db.documents.update_one(
            {"_id": ObjectId(doc_id)},
            {"$set": {"file_name": new_name, "updated_at": datetime.now(timezone.utc)}}
        )

    return {"status": "success", "new_name": new_name}

@router.post("/{case_id}/{doc_id}/archive", status_code=status.HTTP_200_OK)
def archive_forensic_document(
    case_id: str,
    doc_id: str,
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db)
):
    if not ObjectId.is_valid(doc_id):
        raise HTTPException(status_code=400, detail="ID e dokumentit e pavlefshme.")

    doc = db[FORENSIC_DOCS_COLLECTION].find_one({"_id": ObjectId(doc_id)})
    if not doc:
        doc = db.documents.find_one({"_id": ObjectId(doc_id)})

    if not doc:
        raise HTTPException(status_code=404, detail="Dokumenti nuk u gjet.")

    now = datetime.now(timezone.utc)
    db[FORENSIC_DOCS_COLLECTION].update_one(
        {"_id": ObjectId(doc_id)},
        {"$set": {"status": "ARCHIVED", "archived_at": now, "updated_at": now}}
    )
    db.documents.update_one(
        {"_id": ObjectId(doc_id)},
        {"$set": {"status": "ARCHIVED", "archived_at": now, "updated_at": now}}
    )

    log_forensic_action(
        db=db,
        user_id=str(current_user.id),
        case_id=case_id,
        action="DOCUMENT_ARCHIVED",
        details={"doc_id": doc_id, "file_name": doc.get("file_name", "")}
    )

    return {"status": "success", "message": "Dokumenti u arkivua (mbetet në listë)."}

# ==========================================================
# 5. SHKARKIMI I SKEDARIT ORIGJINAL (DOWNLOAD)
# ==========================================================
@router.get("/{case_id}/{doc_id}/download")
async def download_forensic_document(
    case_id: str,
    doc_id: str,
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db)
):
    """Kthen skedarin origjinal (pa konvertim)."""
    doc = None
    if ObjectId.is_valid(doc_id):
        doc = db[FORENSIC_DOCS_COLLECTION].find_one({"_id": ObjectId(doc_id)})
        if not doc:
            doc = db.documents.find_one({"_id": ObjectId(doc_id)})

    if not doc:
        raise HTTPException(status_code=404, detail="Dokumenti nuk u gjet.")

    storage_key = doc.get("storage_key")
    if not storage_key:
        raise HTTPException(status_code=404, detail="Skedari nuk gjendet në ruajtje.")

    try:
        file_bytes = await asyncio.to_thread(storage_service.download_file_as_bytes, storage_key)
        filename = doc.get("file_name", "dokument.pdf")
        mime_type = doc.get("mime_type", "application/pdf")
        return StreamingResponse(
            io.BytesIO(file_bytes),
            media_type=mime_type,
            headers={"Content-Disposition": f"inline; filename={filename}"}
        )
    except Exception as e:
        logger.error(f"File download error: {e}")
        raise HTTPException(status_code=500, detail="Dështoi shkarkimi i skedarit.")

# ==========================================================
# 6. PREVIEW - KONVERTIM NË PDF (SI CASE VIEW)
# ==========================================================
@router.get("/{case_id}/{doc_id}/preview")
async def preview_forensic_document(
    case_id: str,
    doc_id: str,
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db)
):
    """
    Preview dokumenti: nëse nuk është PDF, konvertohet në PDF duke përdorur
    të njëjtën logjikë si Case View (pdf_service).
    """
    doc = None
    if ObjectId.is_valid(doc_id):
        doc = db[FORENSIC_DOCS_COLLECTION].find_one({"_id": ObjectId(doc_id)})
        if not doc:
            doc = db.documents.find_one({"_id": ObjectId(doc_id)})

    if not doc:
        raise HTTPException(status_code=404, detail="Dokumenti nuk u gjet.")

    storage_key = doc.get("storage_key")
    if not storage_key:
        raise HTTPException(status_code=404, detail="Skedari nuk gjendet në ruajtje.")

    # Shkarko bytes nga storage
    try:
        file_bytes = await asyncio.to_thread(storage_service.download_file_as_bytes, storage_key)
    except Exception as e:
        logger.error(f"Preview download error: {e}")
        raise HTTPException(status_code=500, detail="Dështoi shkarkimi i skedarit.")

    filename = doc.get("file_name", "dokument.pdf")
    mime_type = doc.get("mime_type", "application/pdf")

    # Nëse tashmë është PDF, ktheje direkt
    if filename.lower().endswith('.pdf') or mime_type == 'application/pdf':
        return StreamingResponse(
            io.BytesIO(file_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"inline; filename={filename}"}
        )

    # Konverto në PDF duke përdorur pdf_service
    try:
        pdf_bytes, new_filename = await asyncio.to_thread(
            pdf_service.convert_bytes_to_pdf,
            file_bytes,
            filename
        )
        if pdf_bytes == file_bytes:
            return StreamingResponse(
                io.BytesIO(file_bytes),
                media_type=mime_type or 'application/octet-stream',
                headers={"Content-Disposition": f"inline; filename={filename}"}
            )
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"inline; filename={new_filename}"}
        )
    except Exception as e:
        logger.error(f"Preview conversion error: {e}")
        raise HTTPException(status_code=500, detail="Dështoi konvertimi i dokumentit në PDF.")

# ==========================================================
# 7. NEW: GET EXTRACTED TEXT
# ==========================================================
@router.get("/{case_id}/{doc_id}/extracted-text", response_class=PlainTextResponse)
async def get_extracted_text(
    case_id: str,
    doc_id: str,
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db)
):
    """
    Kthen tekstin e ekstraktuar/procesuar për dokumentin e dhënë,
    i cili përdoret për embeddings dhe analiza.
    """
    doc = None
    if ObjectId.is_valid(doc_id):
        doc = db[FORENSIC_DOCS_COLLECTION].find_one({"_id": ObjectId(doc_id)})
        if not doc:
            doc = db.documents.find_one({"_id": ObjectId(doc_id)})

    if not doc:
        raise HTTPException(status_code=404, detail="Dokumenti nuk u gjet.")

    extracted_text = doc.get("extracted_text") or ""
    if not extracted_text:
        raise HTTPException(status_code=404, detail="Teksti i ekstraktuar nuk është i disponueshëm për këtë dokument.")

    return extracted_text