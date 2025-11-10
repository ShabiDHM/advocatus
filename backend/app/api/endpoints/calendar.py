# FILE: backend/app/routers/calendar.py
# PHOENIX PROTOCOL MODIFICATION 46.1 (API ROUTE ALIGNMENT):
# 1. ROUTE CORRECTION: The paths for creating, getting, and deleting events have
#    been corrected to include the '/events' segment.
# 2. This aligns the backend routes with the frontend API calls in api.ts,
#    resolving the '404 Not Found' error and restoring functionality.

from fastapi import APIRouter, Depends, status, HTTPException
from typing import List
from app.services.calendar_service import CalendarService
from app.models.calendar import CalendarEventOut, CalendarEventCreate
from app.api.endpoints.dependencies import get_current_user, get_calendar_service
from app.models.user import UserInDB
from app.models.common import PyObjectId

router = APIRouter()

@router.post(
    "/events",
    response_model=CalendarEventOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new calendar event"
)
async def create_new_event(
    event_data: CalendarEventCreate,
    current_user: UserInDB = Depends(get_current_user),
    calendar_service: CalendarService = Depends(get_calendar_service),
):
    """
    Create a new calendar event associated with the current user and a specific case.
    """
    return await calendar_service.create_event(event_data=event_data, user_id=current_user.id)

@router.get(
    "/events",
    response_model=List[CalendarEventOut],
    summary="Get all calendar events for the current user"
)
async def get_all_user_events(
    current_user: UserInDB = Depends(get_current_user),
    calendar_service: CalendarService = Depends(get_calendar_service),
):
    """
    Retrieve a list of all calendar events belonging to the authenticated user.
    """
    return await calendar_service.get_events_for_user(user_id=current_user.id)

@router.delete(
    "/events/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a calendar event"
)
async def delete_user_event(
    event_id: PyObjectId,
    current_user: UserInDB = Depends(get_current_user),
    calendar_service: CalendarService = Depends(get_calendar_service),
):
    """
    Delete a specific calendar event by its ID.
    """
    await calendar_service.delete_event(event_id=event_id, user_id=current_user.id)
    return