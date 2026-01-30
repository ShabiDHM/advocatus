# FILE: backend/app/api/endpoints/calendar.py
# PHOENIX PROTOCOL - CALENDAR API V5.1 (VALIDATION FIX)
from fastapi import APIRouter, Depends, status, HTTPException, Response
from typing import List, Dict, Any
from bson import ObjectId
from bson.errors import InvalidId
from pydantic import BaseModel
from pymongo.database import Database
import asyncio

from app.services.calendar_service import calendar_service
from app.models.calendar import CalendarEventOut, CalendarEventCreate
from app.api.endpoints.dependencies import get_current_user, get_db
from app.models.user import UserInDB

router = APIRouter()

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

@router.get("/alerts", response_model=BriefingResponse)
async def get_alerts_briefing(
    current_user: UserInDB = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """Returns the Guardian briefing. Fixes root-level 'count' requirement."""
    # We pass the raw name to the service; it handles .title() internally now
    display_name = current_user.full_name or current_user.username
    
    briefing_data = await asyncio.to_thread(
        calendar_service.generate_briefing,
        db=db,
        user_id=current_user.id,
        user_name=display_name
    )
    
    # Return directly. Service V3.2 guaranteed the 'count' key is present at root.
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