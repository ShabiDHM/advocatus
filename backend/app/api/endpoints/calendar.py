# FILE: backend/app/api/endpoints/calendar.py
# PHOENIX PROTOCOL - THE FINAL AND DEFINITIVE CORRECTION (ENDPOINT v5)
# CORRECTION: The type hint for the 'db' dependency is now 'Any'. This aligns
# with the corrected dependency provider in 'db.py' and definitively breaks the
# Pylance error loop, allowing the application to start.

from __future__ import annotations
from fastapi import APIRouter, Depends, status, HTTPException, Response
from typing import List, Any
from bson import ObjectId
from bson.errors import InvalidId

from app.services.calendar_service import CalendarService
from app.models.calendar import CalendarEventOut, CalendarEventCreate
from app.api.endpoints.dependencies import get_current_user, get_async_db
from app.models.user import UserInDB

router = APIRouter(prefix="/calendar", tags=["Calendar"])

@router.post(
    "/events",
    response_model=CalendarEventOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new calendar event",
)
async def create_new_event(
    event_data: CalendarEventCreate,
    current_user: UserInDB = Depends(get_current_user),
    db: Any = Depends(get_async_db),
):
    service = CalendarService(client=db.client)
    return await service.create_event(event_data=event_data, user_id=current_user.id)

@router.get(
    "/events",
    response_model=List[CalendarEventOut],
    summary="Get all calendar events for the current user",
)
async def get_all_user_events(
    current_user: UserInDB = Depends(get_current_user),
    db: Any = Depends(get_async_db),
):
    service = CalendarService(client=db.client)
    return await service.get_events_for_user(user_id=current_user.id)

@router.delete(
    "/events/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a calendar event",
)
async def delete_user_event(
    event_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: Any = Depends(get_async_db),
):
    try:
        object_id = ObjectId(event_id)
    except InvalidId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid event ID format"
        )
    
    service = CalendarService(client=db.client)
    await service.delete_event(event_id=object_id, user_id=current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)