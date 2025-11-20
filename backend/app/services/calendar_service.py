# FILE: backend/app/services/calendar_service.py
# PHOENIX PROTOCOL - SCHEMA ALIGNMENT
# 1. TYPE FIX: Saves 'case_id' as String to match Case Card counters.
# 2. NAMING FIX: Uses 'owner_id' instead of 'user_id' to match Deadline Service.
# 3. COMPATIBILITY: Queries 'owner_id' to ensure extracted deadlines appear on the calendar.

from __future__ import annotations
from typing import List, Any
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import HTTPException, status

from app.models.calendar import CalendarEventInDB, CalendarEventCreate, EventStatus

class CalendarService:
    def __init__(self, client: Any):
        self.db: Any = client.get_default_database()

    async def create_event(self, event_data: CalendarEventCreate, user_id: ObjectId) -> CalendarEventInDB:
        # Verify case ownership using ObjectId
        case = await self.db.cases.find_one({
            "_id": event_data.case_id,
            "owner_id": user_id
        })
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found or does not belong to the current user."
            )

        event_dict = event_data.model_dump()
        
        # PHOENIX FIX 1: Standardize on 'owner_id' (matches deadline_service)
        event_dict["owner_id"] = user_id
        # Remove user_id if it exists to avoid confusion
        event_dict.pop("user_id", None)

        # PHOENIX FIX 2: Store case_id as String (matches case_service counters)
        event_dict["case_id"] = str(event_data.case_id)
        
        now = datetime.now(timezone.utc)
        event_document = {
            **event_dict,
            "created_at": now,
            "updated_at": now,
            "status": EventStatus.PENDING
        }

        result = await self.db.calendar_events.insert_one(event_document)

        created_event = await self.db.calendar_events.find_one({"_id": result.inserted_id})
        if not created_event:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Failed to create and retrieve event."
            )
        return CalendarEventInDB.model_validate(created_event)

    async def get_events_for_user(self, user_id: ObjectId) -> List[CalendarEventInDB]:
        # PHOENIX FIX: Query 'owner_id' to find both manual AND extracted events
        events_cursor = self.db.calendar_events.find({"owner_id": user_id}).sort("start_date", 1)
        events = [CalendarEventInDB.model_validate(event_doc) async for event_doc in events_cursor]
        return events

    async def delete_event(self, event_id: ObjectId, user_id: ObjectId) -> bool:
        # PHOENIX FIX: Check 'owner_id' permission
        delete_result = await self.db.calendar_events.delete_one(
            {"_id": event_id, "owner_id": user_id}
        )
        if delete_result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found or you do not have permission to delete it."
            )
        return True