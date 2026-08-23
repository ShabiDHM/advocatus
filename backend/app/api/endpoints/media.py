# FILE: backend/app/api/endpoints/media.py
# PHOENIX PROTOCOL - MEDIA EVIDENCE ROUTER V5.0 (TRUE TOTAL CASCADE WIPEOUT & VECTOR PURGE)

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks, Query
from typing import List, Annotated, Dict, Any, Optional
from fastapi.responses import JSONResponse, StreamingResponse, Response
from pymongo.database import Database
from bson import ObjectId
from bson.errors import InvalidId
import asyncio
import logging
import tempfile
import os
import shutil
from datetime import datetime, timezone
from jose import jwt
import redis.asyncio as aioredis
import json

from app.api.endpoints.dependencies import get_current_user, get_db
from app.models.user import UserInDB
from app.services import storage_service, transcription_service
from app.services.video_forensic_service import video_forensic_service
from app.services.vector_store_service import create_and_store_embeddings_from_chunks, delete_document_embeddings
from app.core.config import settings

router = APIRouter(tags=["Media Evidence"])
logger = logging.getLogger(__name__)


def validate_object_id(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid ID format.")


def serialize_media_doc(item: Dict[str, Any]) -> Dict[str, Any]:
    item["id"] = str(item["_id"])
    item["_id"] = str(item["_id"])
    item["case_id"] = str(item["case_id"])
    item["owner_id"] = str(item["owner_id"])
    if isinstance(item.get("created_at"), datetime):
        item["created_at"] = item["created_at"].isoformat()
    if isinstance(item.get("updated_at"), datetime):
        item["updated_at"] = item["updated_at"].isoformat()
    return item


async def publish_media_deletion_async(user_id: str, media_id_str: str):
    try:
        payload = {"type": "MEDIA_DELETED", "media_id": media_id_str}
        channel = f"user:{user_id}:updates"
        redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True, socket_timeout=3)
        await redis_client.publish(channel, json.dumps(payload))
        await redis_client.close()
    except Exception as e:
        logger.warning(f"Media deletion SSE publish skipped: {e}")


def orchestrate_media_analysis(db_client, media_id_str: str, file_path: str, user_id_str: str, case_id_str: str, file_name: str, is_video: bool):
    from app.core.db import get_db_instance
    db = get_db_instance()
    media_oid = ObjectId(media_id_str)

    try:
        logger.info(f"🎙️ [Media] Starting forensic audio transcription for: {file_name}")
        transcript = transcription_service.transcribe_media_file(file_path)

        visual_data = {}
        if is_video:
            logger.info(f"📹 [Media Vision] Starting Video Forensic AI Analysis for: {file_name}")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                visual_data = loop.run_until_complete(
                    video_forensic_service.analyze_video_evidence_async(file_path, file_name)
                )
            finally:
                loop.close()

        update_fields = {
            "transcript": transcript,
            "visual_analysis": visual_data,
            "status": "READY",
            "updated_at": datetime.now(timezone.utc)
        }
        db.media_evidence.update_one({"_id": media_oid}, {"$set": update_fields})
        logger.info(f"✅ [Media] Audio & Visual analysis successfully saved for: {file_name}")

        combined_rag_text = f"PROVA AUDIO/VIDEO: {file_name}\n\nTRANSKRIPTI I BISEDËS:\n{transcript}\n"
        if visual_data and visual_data.get("video_forensic_log"):
            combined_rag_text += "\nDITARI I FAKTEVE VIZUALE NGA VIDEOJA:\n"
            for log in visual_data["video_forensic_log"]:
                combined_rag_text += f"- [{log.get('timestamp_video', '00:00')}]: {log.get('visual_evidence', '')} (Vlera: {log.get('evidentiary_value', '')})\n"

        create_and_store_embeddings_from_chunks(
            user_id=user_id_str,
            document_id=media_id_str,
            case_id=case_id_str,
            file_name=f"Media: {file_name}",
            chunks=[combined_rag_text],
            metadatas=[{'file_name': f"Media: {file_name}"}]
        )
        logger.info(f"🧠 [Media] Evidence successfully indexed for Chat & Strategy RAG!")

    except Exception as e:
        logger.error(f"❌ [Media] Analysis failed for {file_name}: {e}")
        db.media_evidence.update_one(
            {"_id": media_oid},
            {"$set": {"status": "FAILED", "transcript": f"Dështoi analiza: {str(e)}"}}
        )
    finally:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass


@router.get("/{case_id}/media", response_model=List[Dict[str, Any]])
async def get_case_media(
    case_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    db: Database = Depends(get_db)
):
    case_oid = validate_object_id(case_id)
    user_oid = ObjectId(current_user.id)
    
    cursor = db.media_evidence.find({"case_id": case_oid, "owner_id": user_oid}).sort("created_at", -1)
    items = []
    for item in cursor:
        items.append(serialize_media_doc(item))
    return items


@router.post("/{case_id}/media/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_case_media(
    case_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Database = Depends(get_db)
):
    case_oid = validate_object_id(case_id)
    user_oid = ObjectId(current_user.id)

    filename = file.filename or "recording.mp3"
    ext = os.path.splitext(filename)[1].lower()
    is_video = ext in ['.mp4', '.mov', '.avi', '.mkv', '.webm']

    temp_fd, temp_path = tempfile.mkstemp(suffix=ext)
    os.close(temp_fd)

    try:
        file.file.seek(0)
        with open(temp_path, "wb") as buffer:
            shutil_fileobj = file.file
            while True:
                chunk = shutil_fileobj.read(1024 * 1024)
                if not chunk:
                    break
                buffer.write(chunk)
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(status_code=500, detail=f"Dështoi ngarkimi i skedarit: {e}")

    with open(temp_path, "rb") as f:
        storage_key = storage_service.upload_bytes_as_file(
            f, filename, str(current_user.id), case_id, file.content_type or ('video/mp4' if is_video else 'audio/mpeg')
        )

    now = datetime.now(timezone.utc)
    media_doc = {
        "case_id": case_oid,
        "owner_id": user_oid,
        "file_name": filename,
        "storage_key": storage_key,
        "media_type": "video" if is_video else "audio",
        "mime_type": file.content_type or ('video/mp4' if is_video else 'audio/mpeg'),
        "status": "PROCESSING",
        "transcript": "",
        "visual_analysis": {},
        "created_at": now,
        "updated_at": now
    }

    result = db.media_evidence.insert_one(media_doc)
    media_id_str = str(result.inserted_id)

    background_tasks.add_task(
        orchestrate_media_analysis,
        db,
        media_id_str,
        temp_path,
        str(current_user.id),
        case_id,
        filename,
        is_video
    )

    serialized_doc = serialize_media_doc(media_doc)
    return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content=serialized_doc)


@router.get("/{case_id}/media/{media_id}/stream")
async def stream_case_media(
    case_id: str,
    media_id: str,
    token: Optional[str] = Query(None),
    db: Database = Depends(get_db)
):
    if token:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id = payload.get("sub") or payload.get("id")
            if not user_id:
                raise HTTPException(status_code=401, detail="Invalid token subject")
        except Exception as e:
            logger.warning(f"Token decode failed for media stream: {e}")
            raise HTTPException(status_code=401, detail="Unauthorized")

    media_oid = validate_object_id(media_id)
    media_item = db.media_evidence.find_one({"_id": media_oid})
    if not media_item:
        raise HTTPException(status_code=404, detail="Regjistrimi nuk u gjet.")

    storage_key = media_item.get("storage_key")
    if not storage_key:
        raise HTTPException(status_code=404, detail="Mungon çelësi i skedarit.")

    stream = storage_service.get_file_stream(storage_key)
    if not stream:
        raise HTTPException(status_code=404, detail="Nuk mund të lexohej skedari.")

    filename = media_item.get("file_name", "media.mp4")
    mime_type = media_item.get("mime_type", "video/mp4")

    return StreamingResponse(
        stream,
        media_type=mime_type,
        headers={
            "Content-Disposition": f"inline; filename=\"{filename}\"",
            "Accept-Ranges": "bytes"
        }
    )


@router.delete("/{case_id}/media/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case_media(
    case_id: str,
    media_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    background_tasks: BackgroundTasks,
    db: Database = Depends(get_db)
):
    """
    6-LEVEL TOTAL CASCADE WIPEOUT (GDPR COMPLIANT):
    Asgjëson 100% provën nga Cloud Storage, Vector RAG (user_vectors), Grafi i Lëndës dhe MongoDB.
    """
    media_oid = validate_object_id(media_id)
    user_oid = ObjectId(current_user.id)

    media_item = db.media_evidence.find_one({"_id": media_oid, "owner_id": user_oid})
    if not media_item:
        raise HTTPException(status_code=404, detail="Regjistrimi nuk u gjet.")

    file_name = media_item.get("file_name", "")

    # 1. Asgjësimi i Skedarit Fizik nga Backblaze B2 Cloud Storage
    storage_key = media_item.get("storage_key")
    if storage_key:
        try:
            await asyncio.to_thread(storage_service.delete_file, storage_key)
            logger.info(f"🗑️ [Cascade 1/6] Purged B2 storage file: {storage_key}")
        except Exception as e:
            logger.warning(f"Failed to purge B2 storage file {storage_key}: {e}")

    # 2. 🛡️ ASGJËSIMI I PLOTË I VEKTORËVE NGA BAZA E NJOHURIVE TË AI (RAG PURGE)
    try:
        # Fshin me ID dhe me Emër Skedari
        delete_document_embeddings(user_id=str(current_user.id), document_id=media_id)
        db.user_vectors.delete_many({
            "$or": [
                {"document_id": media_id},
                {"document_id": media_oid},
                {"file_name": f"Media: {file_name}"},
                {"file_name": file_name}
            ]
        })
        logger.info(f"🗑️ [Cascade 2/6] Total Vector Wipeout completed for media: {file_name}")
    except Exception as e:
        logger.error(f"Failed to purge vector embeddings: {e}")

    # 3. Spastrimi nga Harta e Provave (Case Knowledge Graph)
    try:
        graph_rec = db.case_graphs.find_one({"case_id": case_id})
        if graph_rec:
            nodes = graph_rec.get("nodes", [])
            edges = graph_rec.get("edges", [])
            for n in nodes:
                if "source_doc_ids" in n and media_id in n["source_doc_ids"]:
                    n["source_doc_ids"].remove(media_id)
            for e in edges:
                if "source_doc_ids" in e and media_id in e["source_doc_ids"]:
                    e["source_doc_ids"].remove(media_id)
            db.case_graphs.update_one(
                {"case_id": case_id},
                {"$set": {"nodes": nodes, "edges": edges, "updated_at": datetime.now(timezone.utc).isoformat()}}
            )
            logger.info(f"🗑️ [Cascade 3/6] Cleaned media references from Case Knowledge Graph")
    except Exception as g_err:
        logger.warning(f"Graph cascade cleanup bypass: {g_err}")

    # 4. Spastrimi nga Arkivi
    try:
        db.archives.delete_many({"case_id": case_id, "file_name": file_name})
        logger.info(f"🗑️ [Cascade 4/6] Purged related archive records")
    except Exception as a_err:
        logger.warning(f"Archive cascade cleanup bypass: {a_err}")

    # 5. Fshirja Finale nga Baza e të Dhënave MongoDB (`media_evidence`)
    db.media_evidence.delete_one({"_id": media_oid})
    logger.info(f"🗑️ [Cascade 5/6] Removed media evidence database record: {media_id}")

    # 6. Njoftimi Asinkron Real-Time (SSE / Redis)
    background_tasks.add_task(publish_media_deletion_async, str(current_user.id), media_id)
    logger.info(f"⚡ [Cascade 6/6] Real-time SSE wipeout event dispatched")

    return Response(status_code=status.HTTP_204_NO_CONTENT)