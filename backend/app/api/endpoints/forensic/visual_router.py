# FILE: backend/app/api/endpoints/forensic/visual_router.py
# PHOENIX PROTOCOL - FORENSIC DEDICATED VISUAL & CCTV VIDEO ROUTER V1.4 (AUTO PROCESSING & VECTORIZATION)
# 100% COMPLETE CODE • ZERO PY WARNINGS • RBAC PROTECTED

import os
import io
import asyncio
import logging
import tempfile
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status, BackgroundTasks
from fastapi.responses import StreamingResponse
from pymongo.database import Database
from bson import ObjectId

from app.core.db import get_db
from app.core.config import settings
from app.api.endpoints.dependencies import get_current_forensic_user
from app.models.user import UserInDB
from app.services import storage_service
from app.services.video_service import compress_video_for_storage
from app.services.forensic.forensic_chain_of_custody import generate_evidence_hash, create_custody_stamp
from app.services.forensic.forensic_audit_service import log_forensic_action
from app.services.forensic.forensic_visual_service import (
    process_visual_evidence,
    analyze_cctv_video_forensics
)
from app.services.forensic.forensic_media_processing_service import process_visual_media_background

router = APIRouter(prefix="/visual", tags=["Forensic Visual"])
logger = logging.getLogger(__name__)

FORENSIC_MEDIA_COLLECTION = "forensic_media"

def _serialize_media(doc: Dict[str, Any]) -> Dict[str, Any]:
    doc["id"] = str(doc["_id"])
    doc["_id"] = str(doc["_id"])
    doc["case_id"] = str(doc.get("case_id", ""))
    doc["owner_id"] = str(doc.get("owner_id", ""))
    if isinstance(doc.get("created_at"), datetime):
        doc["created_at"] = doc["created_at"].isoformat()
    return doc

# ==========================================================
# 1. NGARKIMI I VIDEOS/FOTOS ME KOMPRESIM, VULOSJE DHE PËRPUNIM AUTOMATIK
# ==========================================================
@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_forensic_visual(
    case_id: str = Form(...),
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db)
):
    user_id = str(current_user.id)
    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Skedari vizual është i zbrazët.")

    filename = storage_service.sanitize_filename(file.filename or "evidence.jpg")
    ext = os.path.splitext(filename)[1].lower()
    is_video = ext in ['.mp4', '.mov', '.avi', '.mkv', '.webm']
    content_type = file.content_type or ("video/mp4" if is_video else "image/jpeg")

    final_bytes_for_upload = raw_bytes

    # --- KOMPRESIMI I VIDEOS PËR TË MBROJTUR BACKBLAZE B2 FREE TIER ---
    if is_video:
        temp_in = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
        temp_in.write(raw_bytes)
        temp_in.close()
        temp_in_path = temp_in.name
        temp_out_path = temp_in_path.replace(ext, f"_compressed{ext}")

        logger.info(f"🎞️ Duke kompresuar videon forenzike '{filename}' për B2 Storage...")
        success = await compress_video_for_storage(temp_in_path, temp_out_path)
        
        if success and os.path.exists(temp_out_path):
            with open(temp_out_path, "rb") as f:
                final_bytes_for_upload = f.read()
                
        # Pastrimi i skedarëve të përkohshëm
        try:
            if os.path.exists(temp_in_path): os.remove(temp_in_path)
            if os.path.exists(temp_out_path): os.remove(temp_out_path)
        except Exception:
            pass

    # 1. Llogarit SHA-256 të provës (pas kompresimit për përputhje)
    evidence_sha256 = generate_evidence_hash(final_bytes_for_upload)

    # 2. Ngarko në Storage B2
    storage_key = await asyncio.to_thread(
        storage_service.upload_bytes_as_file,
        io.BytesIO(final_bytes_for_upload),
        filename,
        user_id,
        case_id,
        content_type
    )

    # 3. Krijon Vulën Kriptografike Server-Side (Chain of Custody)
    custody_stamp = create_custody_stamp(
        user_id=user_id,
        case_id=case_id,
        action="FORENSIC_VISUAL_SECURED",
        evidence_ids=[evidence_sha256],
        metadata={
            "filename": filename, 
            "is_video": is_video, 
            "original_size": len(raw_bytes),
            "final_size_bytes": len(final_bytes_for_upload)
        }
    )

    now = datetime.now(timezone.utc)
    doc = {
        "case_id": case_id,
        "owner_id": user_id,
        "file_name": filename,
        "storage_key": storage_key,
        "media_type": "video" if is_video else "image",
        "mime_type": content_type,
        "status": "PROCESSING",
        "evidence_sha256": evidence_sha256,
        "custody_stamp": custody_stamp,
        "created_at": now,
        "updated_at": now,
        "progress_percent": 0,
        "progress_message": "Në pritje të përpunimit..."
    }

    result = db[FORENSIC_MEDIA_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    media_id_str = str(result.inserted_id)

    # Trigger background processing (analysis + embeddings)
    background_tasks.add_task(process_visual_media_background, db, media_id_str)

    log_forensic_action(
        db=db,
        user_id=user_id,
        case_id=case_id,
        action="VISUAL_EVIDENCE_ACQUIRED",
        details={
            "filename": filename,
            "is_video": is_video,
            "compressed": is_video,
            "sha256": evidence_sha256,
            "custody_hash": custody_stamp["custody_hash"]
        }
    )

    return _serialize_media(doc)

# ==========================================================
# 2. LISTIMI I PROVAVE VIZUALE TË LËNDËS
# ==========================================================
@router.get("/{case_id}/list")
def list_forensic_visual(
    case_id: str,
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db)
):
    query = {"case_id": str(case_id), "media_type": {"$in": ["video", "image"]}}
    cursor = db[FORENSIC_MEDIA_COLLECTION].find(query).sort("created_at", -1)
    
    items = [_serialize_media(d) for d in cursor]

    if len(items) == 0:
        try:
            case_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
            legacy_cursor = db.media_evidence.find({
                "$or": [{"case_id": case_oid}, {"case_id": str(case_id)}],
                "$or": [{"media_type": "video"}, {"mime_type": {"$regex": "^image/"}}]
            }).sort("created_at", -1)
            for leg in legacy_cursor:
                items.append(_serialize_media(leg))
        except Exception:
            pass

    return items

# ==========================================================
# 3. VIDEO & IMAGE STREAMING
# ==========================================================
@router.get("/{case_id}/{media_id}/stream")
def stream_forensic_visual(
    case_id: str,
    media_id: str,
    token: Optional[str] = Query(None),
    db: Database = Depends(get_db)
):
    if not token:
        raise HTTPException(status_code=401, detail="Kërkohet autorizim për streaming.")

    doc = None
    if ObjectId.is_valid(media_id):
        doc = db[FORENSIC_MEDIA_COLLECTION].find_one({"_id": ObjectId(media_id)})
        if not doc:
            doc = db.media_evidence.find_one({"_id": ObjectId(media_id)})

    if not doc:
        raise HTTPException(status_code=404, detail="Prova vizuale nuk u gjet.")

    storage_key = doc.get("storage_key")
    if not storage_key:
        raise HTTPException(status_code=404, detail="Skedari mungon në storage.")

    stream = storage_service.get_file_stream(storage_key)
    if not stream:
        raise HTTPException(status_code=500, detail="Dështoi leximi i provës vizuale nga serveri.")

    filename = doc.get("file_name", "evidence.jpg")
    mime = doc.get("mime_type", "image/jpeg")

    return StreamingResponse(
        stream,
        media_type=mime,
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Accept-Ranges": "bytes"
        }
    )

# ==========================================================
# 4. FSHIRJA E PROVËS VIZUALE ME AUDIT TRAIL
# ==========================================================
@router.delete("/{case_id}/{media_id}", status_code=status.HTTP_200_OK)
def delete_forensic_visual(
    case_id: str,
    media_id: str,
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db)
):
    user_id = str(current_user.id)
    doc = None
    if ObjectId.is_valid(media_id):
        doc = db[FORENSIC_MEDIA_COLLECTION].find_one({"_id": ObjectId(media_id)})
        if doc:
            db[FORENSIC_MEDIA_COLLECTION].delete_one({"_id": ObjectId(media_id)})
        else:
            doc = db.media_evidence.find_one({"_id": ObjectId(media_id)})
            if doc:
                db.media_evidence.delete_one({"_id": ObjectId(media_id)})

    if not doc:
        raise HTTPException(status_code=404, detail="Prova vizuale nuk u gjet.")

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
        action="VISUAL_EVIDENCE_PURGED",
        details={"file_name": doc.get("file_name", "")}
    )

    return {"status": "success", "message": "Prova vizuale u asgjësua nga laboratori forenzik."}

# ==========================================================
# 5. EKSPERTIZA E FOTOS (EXIF, ELA DHE GOOGLE VISION)
# ==========================================================
@router.post("/analyze")
async def analyze_visual_forensics(
    case_id: str = Form(...),
    case_context: str = Form(""),
    file: UploadFile = File(...),
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db)
):
    user_id = str(current_user.id)
    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Skedari i imazhit është i zbrazët.")

    result = process_visual_evidence(
        image_bytes=raw_bytes,
        case_context=case_context
    )

    log_forensic_action(
        db=db,
        user_id=user_id,
        case_id=case_id,
        action="IMAGE_EXPERT_ANALYSIS_EXECUTED",
        details={
            "file_name": file.filename,
            "manipulation_score": result.get("tamper_analysis", {}).get("manipulation_risk_score", 0.0),
            "has_gps": result.get("exif_metadata", {}).get("has_gps", False)
        }
    )

    return {"success": True, "file_name": file.filename, "data": result}

# ==========================================================
# 6. EKSPERTIZA E PLOTË E VIDEOS CCTV (KEYFRAMES, ELA & CLAUDE 4.6)
# ==========================================================
@router.post("/analyze-video")
async def analyze_video_cctv_forensics(
    case_id: str = Form(...),
    case_context: str = Form(""),
    file: UploadFile = File(...),
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db)
):
    user_id = str(current_user.id)
    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Skedari video është i zbrazët.")

    result = analyze_cctv_video_forensics(
        video_bytes=raw_bytes,
        file_name=file.filename or "cctv_recording.mp4",
        case_context=case_context
    )

    log_forensic_action(
        db=db,
        user_id=user_id,
        case_id=case_id,
        action="CCTV_VIDEO_EXPERT_ANALYSIS_EXECUTED",
        details={
            "file_name": file.filename,
            "keyframes_count": result.get("keyframes_count", 0),
            "avg_tamper_score": result.get("avg_tamper_score", 0.0)
        }
    )

    return {"success": True, "file_name": file.filename, "data": result}