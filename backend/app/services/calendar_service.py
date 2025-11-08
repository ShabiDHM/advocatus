# FILE: backend/app/services/calendar_service.py
# DEFINITIVE VERSION 1.1 (TYPE CORRECTION):
# 1. Corrected the 'status' assignment to use the 'EventStatus' enum.
# 2. Corrected the 'exclude' parameter in 'model_dump' to use a set instead of a list.

from motor.motor_asyncio import AsyncIOMotorClient
from app.models.calendar import CalendarEventInDB, CalendarEventCreate, EventStatus # PHOENIX PROTOCOL FIX 1
from app.models.common import PyObjectId
from typing import List
from fastapi import HTTPException, status
from datetime import datetime

class CalendarService:
    def __init__(self, client: AsyncIOMotorClient):
        self.db = client.get_database()
        self.collection = self.db.get_collection("calendar_events")

    async def create_event(self, event_data: CalendarEventCreate, user_id: PyObjectId) -> CalendarEventInDB:
        event_dict = event_data.model_dump()
        event_dict["user_id"] = user_id
        
        case = await self.db.cases.find_one({"_id": event_data.case_id, "user_id": user_id})
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found or does not belong to the current user."
            )
            
        now = datetime.utcnow()
        event_in_db = CalendarEventInDB(
            **event_dict,
            created_at=now,
            updated_at=now,
            status=EventStatus.PENDING # PHOENIX PROTOCOL FIX 2
        )
        
        result = await self.collection.insert_one(
            event_in_db.model_dump(by_alias=True, exclude={"id"}) # PHOENIX PROTOCOL FIX 3
        )
        
        created_event = await self.collection.find_one({"_id": result.inserted_id})
        if not created_event:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create and retrieve event.")
        return CalendarEventInDB.model_validate(created_event)

    async def get_events_for_user(self, user_id: PyObjectId) -> List[CalendarEventInDB]:
        events = []
        cursor = self.collection.find({"user_id": user_id}).sort("start_date", 1)
        async for event in cursor:
            events.append(CalendarEventInDB.model_validate(event))
        return events

    async def delete_event(self, event_id: PyObjectId, user_id: PyObjectId):
        delete_result = await self.collection.delete_one({"_id": event_id, "user_id": user_id})
        if delete_result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found or you do not have permission to delete it."
            )
        return True