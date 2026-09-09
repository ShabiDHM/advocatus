# FILE: backend/app/services/forensic/forensic_media_processing_service.py
# PHOENIX PROTOCOL - MEDIA PROCESSING SERVICE V1.0 (AUDIO & VISUAL FORENSIC VECTORIZATION)

import os
import io
import json
import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from bson import ObjectId

from app.core.config import settings
from app.services import storage_service
from app.services.vector_store_service import create_and_store_embeddings_from_chunks
from app.services.forensic.forensic_audio_service import process_audio_file
from app.services.forensic.forensic_visual_service import process_visual_evidence, analyze_cctv_video_forensics

logger = logging.getLogger(__name__)

FORENSIC_MEDIA_COLLECTION = "forensic_media"


def _safe_parse_json(data: Dict[str, Any]) -> str:
    try:
        return json.dumps(data, ensure_ascii=False)
    except Exception:
        return str(data)


async def _update_media_status(db: Any, media_id: ObjectId, status: str, progress: int, message: str):
    await asyncio.to_thread(
        db[FORENSIC_MEDIA_COLLECTION].update_one,
        {"_id": media_id},
        {"$set": {
            "status": status,
            "progress_percent": progress,
            "progress_message": message,
            "updated_at": datetime.now(timezone.utc)
        }}
    )


async def _store_embeddings(
    user_id: str,
    media_id: str,
    case_id: str,
    file_name: str,
    text_content: str
):
    if not text_content or len(text_content.strip()) < 10:
        return
    try:
        chunks = [text_content[i:i+1500] for i in range(0, len(text_content), 1200)]
        metadatas = [{"page": 1, "source": file_name, "media_id": media_id} for _ in chunks]
        await asyncio.to_thread(
            create_and_store_embeddings_from_chunks,
            user_id=user_id,
            document_id=media_id,
            case_id=case_id,
            file_name=file_name,
            chunks=chunks,
            metadatas=metadatas
        )
    except Exception as e:
        logger.warning(f"Embedding storage failed for media {media_id}: {e}")


async def process_audio_media_background(db: Any, media_id_str: str):
    """
    Download audio, run transcription/analysis, store results, create embeddings.
    """
    media_id = ObjectId(media_id_str)
    doc = await asyncio.to_thread(db[FORENSIC_MEDIA_COLLECTION].find_one, {"_id": media_id})
    if not doc:
        logger.error(f"Audio media {media_id_str} not found")
        return

    user_id = str(doc.get("owner_id"))
    case_id = str(doc.get("case_id"))
    file_name = doc.get("file_name", "audio.mp3")
    storage_key = doc.get("storage_key")
    if not storage_key:
        await _update_media_status(db, media_id, "ERROR", 100, "Skedari mungon në storage")
        return

    try:
        await _update_media_status(db, media_id, "PROCESSING", 30, "Duke shkarkuar audion...")
        file_bytes = await asyncio.to_thread(storage_service.download_file_as_bytes, storage_key)

        await _update_media_status(db, media_id, "PROCESSING", 60, "Duke transkriptuar dhe analizuar...")
        result = await asyncio.to_thread(process_audio_file, file_bytes, doc.get("case_context", ""))
        transcript = result.get("formatted_transcript", "")
        analysis = result.get("forensic_intelligence", {})

        # Build extracted text from transcript and key analysis fields
        text_for_embedding = transcript + "\n" + _safe_parse_json(analysis)

        # Store in DB
        await asyncio.to_thread(
            db[FORENSIC_MEDIA_COLLECTION].update_one,
            {"_id": media_id},
            {"$set": {
                "extracted_text": text_for_embedding,
                "transcript": transcript,
                "analysis": analysis,
                "status": "PROCESSING",
                "progress_percent": 80,
                "progress_message": "Duke vektorizuar...",
                "updated_at": datetime.now(timezone.utc)
            }}
        )

        # Create embeddings
        await _store_embeddings(user_id, media_id_str, case_id, file_name, text_for_embedding)

        await _update_media_status(db, media_id, "READY", 100, "Gati")

    except Exception as e:
        logger.error(f"Audio media processing failed for {media_id_str}: {e}")
        await _update_media_status(db, media_id, "ERROR", 100, f"Gabim: {str(e)[:200]}")


async def process_visual_media_background(db: Any, media_id_str: str):
    """
    Download image/video, run forensic analysis, store results, create embeddings.
    """
    media_id = ObjectId(media_id_str)
    doc = await asyncio.to_thread(db[FORENSIC_MEDIA_COLLECTION].find_one, {"_id": media_id})
    if not doc:
        logger.error(f"Visual media {media_id_str} not found")
        return

    user_id = str(doc.get("owner_id"))
    case_id = str(doc.get("case_id"))
    file_name = doc.get("file_name", "evidence.jpg")
    media_type = doc.get("media_type", "image")
    storage_key = doc.get("storage_key")
    if not storage_key:
        await _update_media_status(db, media_id, "ERROR", 100, "Skedari mungon në storage")
        return

    try:
        await _update_media_status(db, media_id, "PROCESSING", 30, "Duke shkarkuar provën...")
        file_bytes = await asyncio.to_thread(storage_service.download_file_as_bytes, storage_key)

        await _update_media_status(db, media_id, "PROCESSING", 60, "Duke analizuar forenzikisht...")
        if media_type == "video":
            result = await asyncio.to_thread(analyze_cctv_video_forensics, file_bytes, file_name, doc.get("case_context", ""))
            # For video, we can embed the forensic report summary and chronology
            text_for_embedding = _safe_parse_json(result.get("forensic_report", {}))
        else:
            result = await asyncio.to_thread(process_visual_evidence, file_bytes, doc.get("case_context", ""))
            # For image, embed vision text, exif, forensic opinion
            text_parts = [
                result.get("vision_detection", {}).get("text_detected", ""),
                _safe_parse_json(result.get("exif_metadata", {})),
                _safe_parse_json(result.get("forensic_opinion", {})),
                _safe_parse_json(result.get("tamper_analysis", {}))
            ]
            text_for_embedding = "\n".join([p for p in text_parts if p])

        await asyncio.to_thread(
            db[FORENSIC_MEDIA_COLLECTION].update_one,
            {"_id": media_id},
            {"$set": {
                "extracted_text": text_for_embedding,
                "analysis": result,
                "status": "PROCESSING",
                "progress_percent": 80,
                "progress_message": "Duke vektorizuar...",
                "updated_at": datetime.now(timezone.utc)
            }}
        )

        await _store_embeddings(user_id, media_id_str, case_id, file_name, text_for_embedding)

        await _update_media_status(db, media_id, "READY", 100, "Gati")

    except Exception as e:
        logger.error(f"Visual media processing failed for {media_id_str}: {e}")
        await _update_media_status(db, media_id, "ERROR", 100, f"Gabim: {str(e)[:200]}")