# FILE: backend/app/api/endpoints/calendar.py
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

class ShareUpdateRequest(BaseModel):
    is_public: bool

# PHOENIX: New response model for the intelligent briefing
class BriefingResponse(BaseModel):
    count: int
    greeting: str
    message: str
    status: str

@router.get("/alerts", response_model=BriefingResponse)
async def get_alerts_briefing(
    current_user: UserInDB = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    """
    Returns a personalized 'Kujdestari' briefing.
    Includes count, greeting, and context-aware status message.
    """
    # 1. Get the raw count
    count = await asyncio.to_thread(calendar_service.get_upcoming_alerts_count, db=db, user_id=current_user.id)
    
    # 2. Generate the Persona message
    # We use user.full_name if available, otherwise email or generic
    user_name = current_user.full_name if current_user.full_name else "Avokat"
    briefing_data = calendar_service.generate_briefing(user_name, count)
    
    # 3. Return combined data
    return BriefingResponse(
        count=count,
        greeting=briefing_data["greeting"],
        message=briefing_data["message"],
        status=briefing_data["status"]
    )

@router.post("/events", response_model=CalendarEventOut, status_code=status.HTTP_201_CREATED)
async def create_new_event(
    event_data: CalendarEventCreate,
    current_user: UserInDB = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    return await asyncio.to_thread(calendar_service.create_event, db=db, event_data=event_data, user_id=current_user.id)

@router.put("/events/{event_id}/share", status_code=status.HTTP_200_OK)
async def update_event_share_status(
    event_id: str,
    update_data: ShareUpdateRequest,
    current_user: UserInDB = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    try:
        object_id = ObjectId(event_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid event ID")

    collection = db["calendar_events"]

    def _update():
        event = collection.find_one({"_id": object_id, "user_id": current_user.id})
        if not event:
            return None
        
        result = collection.update_one(
            {"_id": object_id},
            {"$set": {"is_public": update_data.is_public}}
        )
        return result, event.get("is_public", False)

    result_data = await asyncio.to_thread(_update)
    
    if result_data is None:
        raise HTTPException(status_code=404, detail="Event not found or permission denied.")

    update_result, old_status = result_data

    if update_result.modified_count == 1:
        return {"status": "success", "is_public": update_data.is_public}
    
    return {"status": "no_change", "is_public": old_status}

@router.get("/events", response_model=List[CalendarEventOut])
async def get_all_user_events(
    current_user: UserInDB = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    return await asyncio.to_thread(calendar_service.get_events_for_user, db=db, user_id=current_user.id)

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