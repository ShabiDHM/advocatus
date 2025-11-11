# FILE: backend/app/api/endpoints/calendar.py
# CORRECTED: Fixed parameter passing to match service method signature

from fastapi import APIRouter, Depends, status
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
    Creates a new calendar event associated with the current user.
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
    Retrieves all calendar events for the currently authenticated user.
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
    Deletes a specific calendar event by its ID, ensuring the user has permission.
    """
    await calendar_service.delete_event(event_id=event_id, user_id=current_user.id)
    return