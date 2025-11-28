# FILE: backend/app/services/calendar_service.py
# PHOENIX PROTOCOL - ALERTS LOGIC
# 1. LOGIC: Counts 'PENDING' events occurring in the next 7 days.
# 2. COMPATIBILITY: Handles both ISO Strings and DateTime objects.

from __future__ import annotations
from typing import List, Any
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from fastapi import HTTPException, status

from app.models.calendar import CalendarEventInDB, CalendarEventCreate, EventStatus

class CalendarService:
    def __init__(self, client: Any):
        self.db: Any = client.get_default_database()

    async def create_event(self, event_data: CalendarEventCreate, user_id: ObjectId) -> CalendarEventInDB:
        # Verify case ownership
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
        event_dict["owner_id"] = user_id
        event_dict.pop("user_id", None)
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
        return CalendarEventInDB.model_validate(created_event)

    async def get_events_for_user(self, user_id: ObjectId) -> List[CalendarEventInDB]:
        events_cursor = self.db.calendar_events.find({"owner_id": user_id}).sort("start_date", 1)
        events = [CalendarEventInDB.model_validate(event_doc) async for event_doc in events_cursor]
        return events

    async def delete_event(self, event_id: ObjectId, user_id: ObjectId) -> bool:
        delete_result = await self.db.calendar_events.delete_one(
            {"_id": event_id, "owner_id": user_id}
        )
        if delete_result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Event not found.")
        return True

    # --- THE ALERT LOGIC ---
    async def get_upcoming_alerts_count(self, user_id: ObjectId, days: int = 7) -> int:
        """
        Returns count of PENDING events starting in the next 'days'.
        """
        now = datetime.now(timezone.utc)
        future = now + timedelta(days=days)
        
        now_str = now.isoformat()
        future_str = future.isoformat()
        
        query = {
            "owner_id": user_id,
            "status": "PENDING",
            "$or": [
                # Matches ISO String dates (e.g. from Extraction)
                {"start_date": {"$gte": now_str, "$lte": future_str}},
                # Matches DateTime objects (e.g. from Manual Entry)
                {"start_date": {"$gte": now, "$lte": future}}
            ]
        }
        
        return await self.db.calendar_events.count_documents(query)