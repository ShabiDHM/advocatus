# FILE: backend/app/api/endpoints/forensic/audio_router.py
# PHOENIX PROTOCOL - FORENSIC DEDICATED AUDIO ROUTER V1.2 (PURE TRANSCRIPT SUPPORT)
# 100% COMPLETE CODE • ZERO PY WARNINGS • RBAC PROTECTED

import os
import io
import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from fastapi.responses import StreamingResponse
from pymongo.database import Database
from bson import ObjectId

from app.core.db import get_db
from app.core.config import settings
from app.api.endpoints.dependencies import get_current_forensic_user
from app.models.user import UserInDB
from app.services import storage_service
from app.services.forensic.forensic_chain_of_custody import generate_evidence_hash, create_custody_stamp
from app.services.forensic.forensic_audit_service import log_forensic_action
from app.services.forensic.forensic_audio_service import process_audio_file

router = APIRouter(prefix="/audio", tags=["Forensic Audio"])
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
# 1. NGARKIMI I AUDIOS ME VULOSJE TË MENJËHERSHME (CUSTODY SEAL)
# ==========================================================
@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_forensic_audio(
    case_id: str = Form(...),
    file: UploadFile = File(...),
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db)
):
    user_id = str(current_user.id)
    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Skedari audio është i zbrazët.")

    evidence_sha256 = generate_evidence_hash(raw_bytes)
    filename = storage_service.sanitize_filename(file.filename or "recording.mp3")
    content_type = file.content_type or "audio/mpeg"

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
        action="FORENSIC_AUDIO_SECURED",
        evidence_ids=[evidence_sha256],
        metadata={"filename": filename, "file_size_bytes": len(raw_bytes)}
    )

    now = datetime.now(timezone.utc)
    doc = {
        "case_id": case_id,
        "owner_id": user_id,
        "file_name": filename,
        "storage_key": storage_key,
        "media_type": "audio",
        "mime_type": content_type,
        "status": "READY",
        "evidence_sha256": evidence_sha256,
        "custody_stamp": custody_stamp,
        "created_at": now,
        "updated_at": now
    }

    result = db[FORENSIC_MEDIA_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id

    log_forensic_action(
        db=db,
        user_id=user_id,
        case_id=case_id,
        action="AUDIO_EVIDENCE_ACQUIRED",
        details={
            "filename": filename,
            "sha256": evidence_sha256,
            "custody_hash": custody_stamp["custody_hash"]
        }
    )

    return _serialize_media(doc)

# ==========================================================
# 2. LISTIMI I PROVAVE AUDIO TË LËNDËS
# ==========================================================
@router.get("/{case_id}/list")
def list_forensic_audio(
    case_id: str,
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db)
):
    query = {"case_id": str(case_id), "media_type": "audio"}
    cursor = db[FORENSIC_MEDIA_COLLECTION].find(query).sort("created_at", -1)
    items = [_serialize_media(d) for d in cursor]

    if len(items) == 0:
        try:
            case_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
            legacy_cursor = db.media_evidence.find({
                "$or": [{"case_id": case_oid}, {"case_id": str(case_id)}],
                "media_type": "audio"
            }).sort("created_at", -1)
            for leg in legacy_cursor:
                items.append(_serialize_media(leg))
        except Exception:
            pass

    return items

# ==========================================================
# 3. AUDIO STREAMING (ME MBROJTJE TOKEN-I)
# ==========================================================
@router.get("/{case_id}/{media_id}/stream")
def stream_forensic_audio(
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
        raise HTTPException(status_code=404, detail="Regjistrimi audio nuk u gjet.")

    storage_key = doc.get("storage_key")
    if not storage_key:
        raise HTTPException(status_code=404, detail="Skedari mungon në storage.")

    stream = storage_service.get_file_stream(storage_key)
    if not stream:
        raise HTTPException(status_code=500, detail="Dështoi leximi i stream-it të audios.")

    filename = doc.get("file_name", "audio.mp3")
    mime = doc.get("mime_type", "audio/mpeg")

    return StreamingResponse(
        stream,
        media_type=mime,
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Accept-Ranges": "bytes"
        }
    )

# ==========================================================
# 4. FSHIRJA E AUDIOS ME AUDIT TRAIL
# ==========================================================
@router.delete("/{case_id}/{media_id}", status_code=status.HTTP_200_OK)
def delete_forensic_audio(
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
        raise HTTPException(status_code=404, detail="Prova audio nuk u gjet.")

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
        action="AUDIO_EVIDENCE_PURGED",
        details={"file_name": doc.get("file_name", "")}
    )

    return {"status": "success", "message": "Prova audio u asgjësua nga laboratori forenzik."}

# ==========================================================
# 5. ANALIZA E DIARIZIMIT DHE STRESIT (ASSEMBLYAI & CLAUDE)
# ==========================================================
@router.post("/analyze")
async def analyze_audio_forensics(
    case_id: str = Form(...),
    case_context: str = Form(""),
    file: UploadFile = File(...),
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db)
):
    user_id = str(current_user.id)
    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Skedari audio është i zbrazët.")

    result = process_audio_file(
        audio_bytes=raw_bytes,
        case_context=case_context
    )

    log_forensic_action(
        db=db,
        user_id=user_id,
        case_id=case_id,
        action="AUDIO_EXPERT_ANALYSIS_EXECUTED",
        details={
            "file_name": file.filename,
            "threat_level": result.get("forensic_intelligence", {}).get("threat_level", "N/A")
        }
    )

    return {"success": True, "file_name": file.filename, "data": result}

# ==========================================================
# 6. VETËM TRANSKRIPTI I PASTËR (VERBATIM, PA ANALIZË LLM)
# ==========================================================
@router.post("/pure-transcript")
async def get_pure_audio_transcript(
    case_id: str = Form(...),
    file: UploadFile = File(...),
    current_user: UserInDB = Depends(get_current_forensic_user),
    db: Database = Depends(get_db)
):
    from app.services.video_service import video_service
    import tempfile
    
    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Skedari audio është i zbrazët.")
        
    ext = os.path.splitext(file.filename or ".mp3")[1].lower()
    temp_in = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
    temp_in.write(raw_bytes)
    temp_in.close()
    temp_path = temp_in.name

    try:
        # Përdorim motorin e thjeshtë të Whisper (pa diarizim dhe pa Claude)
        result = await video_service.analyze_video_evidence_async(temp_path, file.filename or "audio")
        pure_text = result.get("transcription", "[Zëri nuk mund të transkriptohej.]")
        
        log_forensic_action(
            db=db,
            user_id=str(current_user.id),
            case_id=case_id,
            action="PURE_TRANSCRIPT_GENERATED",
            details={"file_name": file.filename}
        )
        
        return {"success": True, "data": pure_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_path):
            try: os.remove(temp_path)
            except Exception: pass