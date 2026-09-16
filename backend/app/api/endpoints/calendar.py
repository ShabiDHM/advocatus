# FILE: backend/app/api/endpoints/calendar.py
# PHOENIX PROTOCOL - CALENDAR API V8.0 (VOICE ERROR GUARD)
from fastapi import APIRouter, Depends, status, HTTPException, Response, Body, UploadFile, File, Form
from typing import List, Dict, Any, Optional
from bson import ObjectId
from bson.errors import InvalidId
from pydantic import BaseModel
from pymongo.database import Database
import asyncio
import os
import tempfile
import logging

from app.services.calendar_service import calendar_service
from app.services.transcription_service import transcription_service
from app.models.calendar import CalendarEventOut, CalendarEventCreate
from app.api.endpoints.dependencies import get_current_user, get_db
from app.models.user import UserInDB

router = APIRouter()
logger = logging.getLogger(__name__)


class RiskAlert(BaseModel):
    id: str
    title: str
    level: str
    seconds_remaining: int
    effective_deadline: str


class BriefingResponse(BaseModel):
    count: int
    greeting_key: str
    message_key: str
    status: str
    data: Dict[str, Any]
    risk_radar: List[RiskAlert]


class VoiceParseRequest(BaseModel):
    text: str


# Prefiksat e njohura të error-it nga transcription_service
TRANSCRIPTION_ERROR_PREFIXES = (
    "[Gabim gjatë transkriptimit:",
    "[Nuk u detektua",
    "[Zëri nuk mund të transkriptohej",
)


def _is_transcription_error(text: str) -> bool:
    """Kontrollon nëse teksti i transkriptimit është error, jo tekst i vlefshëm."""
    if not text or not text.strip():
        return True
    cleaned = text.strip()
    for prefix in TRANSCRIPTION_ERROR_PREFIXES:
        if cleaned.startswith(prefix):
            return True
    return False


@router.get("/alerts", response_model=BriefingResponse)
async def get_alerts_briefing(
    current_user: UserInDB = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Returns the Guardian briefing. Fixes root-level 'count' requirement."""
    display_name = current_user.full_name or current_user.username
    
    briefing_data = await asyncio.to_thread(
        calendar_service.generate_briefing,
        db=db,
        user_id=current_user.id,
        user_name=display_name
    )
    
    return BriefingResponse(**briefing_data)


@router.get("/events", response_model=List[CalendarEventOut])
async def get_all_user_events(
    current_user: UserInDB = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    return await asyncio.to_thread(calendar_service.get_events_for_user, db=db, user_id=current_user.id)


@router.post("/events", response_model=CalendarEventOut, status_code=status.HTTP_201_CREATED)
async def create_new_event(
    event_data: CalendarEventCreate,
    current_user: UserInDB = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    return await asyncio.to_thread(calendar_service.create_event, db=db, event_data=event_data, user_id=current_user.id)


@router.patch("/events/{event_id}", response_model=CalendarEventOut)
async def update_user_event(
    event_id: str,
    payload: Dict[str, Any] = Body(...),
    current_user: UserInDB = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    try:
        object_id = ObjectId(event_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid event ID")

    return await asyncio.to_thread(
        calendar_service.update_event,
        db=db,
        event_id=object_id,
        user_id=current_user.id,
        updates=payload
    )


@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_event(
    event_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    try:
        object_id = ObjectId(event_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid event ID")
    await asyncio.to_thread(calendar_service.delete_event, db=db, event_id=object_id, user_id=current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ==========================================================
# VOICE → EVENT ENDPOINTS
# ==========================================================

@router.post("/voice-parse")
async def parse_voice_text(
    payload: VoiceParseRequest,
    current_user: UserInDB = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """
    Analizon tekstin e transkriptuar dhe kthen detajet e strukturuara të një event-i.
    Përdoret nga frontend kur audio është transkriptuar tashmë.
    """
    text = (payload.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Teksti është i zbrazët.")
    
    if len(text) > 5000:
        raise HTTPException(status_code=400, detail="Teksti është shumë i gjatë (max 5000 karaktere).")
    
    if _is_transcription_error(text):
        raise HTTPException(
            status_code=422,
            detail="Teksti i dhënë nuk përmban përmbajtje të vlefshme për analizë."
        )
    
    try:
        user_cases = list(db.cases.find(
            {"owner_id": current_user.id},
            {"title": 1, "case_number": 1}
        ).limit(50))
        case_titles = [c.get("title") or c.get("case_number") or "" for c in user_cases if c.get("title") or c.get("case_number")]
    except Exception as e:
        logger.warning(f"Could not load case titles for voice parse: {e}")
        case_titles = []
    
    result = await asyncio.to_thread(
        calendar_service.parse_voice_text_to_event,
        text=text,
        case_titles=case_titles
    )
    
    if not result:
        raise HTTPException(
            status_code=422,
            detail="Nuk mund të nxirreshin detajet e event-it nga teksti. Provoni të ripërcaktoni me fjalë të qarta."
        )
    
    return {"success": True, "parsed": result}


@router.post("/voice-transcribe")
async def transcribe_voice_and_parse(
    file: UploadFile = File(...),
    current_user: UserInDB = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """
    Merr një audio file, e transkripton me AssemblyAI, dhe e parse-on në një event të strukturuar.
    """
    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Skedari audio është i zbrazët.")
    
    if len(raw_bytes) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Skedari audio është mbi 20 MB.")
    
    original_filename = file.filename or "voice.webm"
    ext = os.path.splitext(original_filename)[1].lower() or ".webm"
    if ext not in [".webm", ".mp3", ".wav", ".m4a", ".ogg", ".aac", ".opus", ".flac"]:
        ext = ".webm"
    
    temp_fd, temp_path = tempfile.mkstemp(suffix=ext)
    os.close(temp_fd)
    try:
        with open(temp_path, "wb") as f:
            f.write(raw_bytes)
    except Exception as e:
        if os.path.exists(temp_path):
            try: os.remove(temp_path)
            except Exception: pass
        raise HTTPException(status_code=500, detail=f"Dështoi ruajtja e skedarit: {e}")
    
    transcription_text = ""
    try:
        transcription_text = await asyncio.to_thread(
            transcription_service.transcribe,
            temp_path
        )
    except Exception as e:
        logger.error(f"❌ Voice transcription exception: {e}")
        transcription_text = ""
    finally:
        if os.path.exists(temp_path):
            try: os.remove(temp_path)
            except Exception: pass
    
    # FIX: Kontroll i plotë për error strings
    if not transcription_text or not transcription_text.strip():
        raise HTTPException(
            status_code=422,
            detail="Transkriptimi dështoi ose nuk u detektua zë i kuptueshëm."
        )
    
    if _is_transcription_error(transcription_text):
        clean_error = transcription_text.strip().strip("[]").strip()
        logger.error(f"❌ Voice transcription returned error: {clean_error}")
        raise HTTPException(
            status_code=422,
            detail=f"Transkriptimi dështoi. {clean_error}"
        )
    
    try:
        user_cases = list(db.cases.find(
            {"owner_id": current_user.id},
            {"title": 1, "case_number": 1}
        ).limit(50))
        case_titles = [c.get("title") or c.get("case_number") or "" for c in user_cases if c.get("title") or c.get("case_number")]
    except Exception:
        case_titles = []
    
    parsed = await asyncio.to_thread(
        calendar_service.parse_voice_text_to_event,
        text=transcription_text,
        case_titles=case_titles
    )
    
    return {
        "success": True,
        "transcription": transcription_text,
        "parsed": parsed or {},
    }