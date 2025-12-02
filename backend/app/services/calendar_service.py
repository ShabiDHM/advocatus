# FILE: backend/app/services/calendar_service.py
# PHOENIX PROTOCOL - TYPE CONVERSION FIX
# 1. FIX: Manually converted ObjectId fields to strings before Pydantic validation.
# 2. STATUS: Resolves the '500 Internal Server Error' on the calendar page.

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
        
        # PHOENIX FIX: Manual conversion after creation
        if created_event:
            created_event['id'] = str(created_event['_id'])
            if 'case_id' in created_event and isinstance(created_event['case_id'], ObjectId):
                created_event['case_id'] = str(created_event['case_id'])
            if 'document_id' in created_event and isinstance(created_event['document_id'], ObjectId):
                created_event['document_id'] = str(created_event['document_id'])
            return CalendarEventInDB.model_validate(created_event)
        
        raise HTTPException(status_code=500, detail="Failed to retrieve created event.")

    async def get_events_for_user(self, user_id: ObjectId) -> List[CalendarEventInDB]:
        events_cursor = self.db.calendar_events.find({"owner_id": user_id}).sort("start_date", 1)
        events = []
        async for event_doc in events_cursor:
            # PHOENIX FIX: Convert ObjectIds to strings before validation
            event_doc['id'] = str(event_doc['_id'])
            if 'case_id' in event_doc and isinstance(event_doc['case_id'], ObjectId):
                event_doc['case_id'] = str(event_doc['case_id'])
            if 'document_id' in event_doc and isinstance(event_doc['document_id'], ObjectId):
                event_doc['document_id'] = str(event_doc['document_id'])
            
            events.append(CalendarEventInDB.model_validate(event_doc))
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