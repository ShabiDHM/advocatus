# FILE: backend/app/services/calendar_service.py
# COMPLETELY CLEANED VERSION - No type annotation issues

from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import HTTPException, status
from datetime import datetime
from typing import List
from bson import ObjectId

# Direct imports without TYPE_CHECKING complexity
from app.models.calendar import CalendarEventInDB, CalendarEventCreate, EventStatus


class CalendarService:
    def __init__(self, client: AsyncIOMotorClient):
        self.db = client.get_database()
        self.collection = self.db.get_collection("calendar_events")

    async def create_event(self, event_data: CalendarEventCreate, user_id: ObjectId) -> CalendarEventInDB:
        # Verify case exists and belongs to user
        case = await self.db.cases.find_one({
            "_id": event_data.case_id,
            "owner_id": user_id
        })
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found or does not belong to the current user."
            )

        # Prepare event data
        event_dict = event_data.model_dump()
        event_dict["user_id"] = user_id

        # Create event in database
        now = datetime.utcnow()
        event_in_db = CalendarEventInDB(
            **event_dict,
            created_at=now,
            updated_at=now,
            status=EventStatus.PENDING
        )

        # Insert into database
        result = await self.collection.insert_one(
            event_in_db.model_dump(by_alias=True, exclude={"id"})
        )

        # Retrieve and return created event
        created_event = await self.collection.find_one({"_id": result.inserted_id})
        if not created_event:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Failed to create and retrieve event."
            )
        return CalendarEventInDB.model_validate(created_event)

    async def get_events_for_user(self, user_id: ObjectId) -> List[CalendarEventInDB]:
        events = []
        cursor = self.collection.find({"user_id": user_id}).sort("start_date", 1)
        async for event in cursor:
            events.append(CalendarEventInDB.model_validate(event))
        return events

    async def delete_event(self, event_id: ObjectId, user_id: ObjectId) -> bool:
        delete_result = await self.collection.delete_one(
            {"_id": event_id, "user_id": user_id}
        )
        if delete_result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found or you do not have permission to delete it."
            )
        return True