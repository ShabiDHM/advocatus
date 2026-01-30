# FILE: backend/app/api/endpoints/calendar.py
# PHOENIX PROTOCOL - CALENDAR API V4.0 (SYNCHRONIZATION FIX)
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

# PHOENIX: Pydantic Model for Intelligent Briefing
class BriefingResponse(BaseModel):
    count: int
    greeting_key: str
    message_key: str
    status: str
    data: Dict[str, Any]

@router.get("/alerts", response_model=BriefingResponse)
async def get_alerts_briefing(
    current_user: UserInDB = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """
    Returns a personalized i18n-ready 'Kujdestari' briefing.
    PHOENIX FIX: Parameter name aligned to 'user_id'.
    """
    count = await asyncio.to_thread(
        calendar_service.get_upcoming_alerts_count, 
        db=db, 
        user_id=current_user.id
    )
    
    display_name = current_user.full_name if current_user.full_name else current_user.username
    briefing_data = calendar_service.generate_briefing(display_name, count)
    
    return BriefingResponse(
        count=count,
        greeting_key=briefing_data["greeting_key"],
        message_key=briefing_data["message_key"],
        status=briefing_data["status"],
        data=briefing_data["data"]
    )

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