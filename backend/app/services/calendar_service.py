# FILE: backend/app/services/calendar_service.py
# DEFINITIVE VERSION (ARCHITECTURAL CURE):
# 1. DISEASE CURED: The circular import dependency has been resolved by moving the
#    model imports into a `TYPE_CHECKING` block.
# 2. ARCHITECTURAL PATTERN: This is the standard, correct Python pattern for
#    handling type hints that would otherwise create import loops. The type checker
#    can see the types, but the circular dependency is broken at runtime.
# 3. SYSTEM INTEGRITY RESTORED: This clears the final Pylance error, completing
#    the full restoration of the backend system's integrity.

from __future__ import annotations
from typing import List, TYPE_CHECKING
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import HTTPException, status
from datetime import datetime

# CURE: Use a TYPE_CHECKING block to import types needed for hints.
# This makes them available to the linter without causing a circular import at runtime.
if TYPE_CHECKING:
    from app.models.calendar import CalendarEventInDB, CalendarEventCreate, EventStatus
    from app.models.common import PyObjectId
    from app.models.user import UserInDB


class CalendarService:
    def __init__(self, client: AsyncIOMotorClient):
        self.db = client.get_database()
        self.collection = self.db.get_collection("calendar_events")

    # Note: The type hints "UserInDB", "CalendarEventCreate", etc. are now implicitly
    # treated as forward references, which is exactly what we need.
    async def create_event(self, event_data: "CalendarEventCreate", current_user: "UserInDB") -> "CalendarEventInDB":
        from app.models.calendar import CalendarEventInDB, EventStatus

        case = await self.db.cases.find_one({
            "_id": event_data.case_id,
            "owner_id": current_user.id
        })
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found or does not belong to the current user."
            )

        event_dict = event_data.model_dump()
        event_dict["user_id"] = current_user.id

        now = datetime.utcnow()
        event_in_db = CalendarEventInDB(
            **event_dict,
            created_at=now,
            updated_at=now,
            status=EventStatus.PENDING
        )

        result = await self.collection.insert_one(
            event_in_db.model_dump(by_alias=True, exclude={"id"})
        )

        created_event = await self.collection.find_one({"_id": result.inserted_id})
        if not created_event:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create and retrieve event.")
        return CalendarEventInDB.model_validate(created_event)

    async def get_events_for_user(self, user_id: "PyObjectId") -> List["CalendarEventInDB"]:
        from app.models.calendar import CalendarEventInDB
        events = []
        cursor = self.collection.find({"user_id": user_id}).sort("start_date", 1)
        async for event in cursor:
            events.append(CalendarEventInDB.model_validate(event))
        return events

    async def delete_event(self, event_id: "PyObjectId", user_id: "PyObjectId"):
        delete_result = await self.collection.delete_one({"_id": event_id, "user_id": user_id})
        if delete_result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found or you do not have permission to delete it."
            )
        return True