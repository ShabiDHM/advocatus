# FILE: backend/app/services/calendar_service.py
# PHOENIX PROTOCOL - CALENDAR SERVICE V3.0 (SYNC INSTANCE)
# 1. FIX: Converted to synchronous 'def' to match PyMongo architecture.
# 2. FIX: Added 'calendar_service' instantiation at the bottom.
# 3. STATUS: Compatible with the new router and db.py.

from typing import List
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from fastapi import HTTPException, status
from pymongo.database import Database

from app.models.calendar import CalendarEventInDB, CalendarEventCreate, EventStatus

class CalendarService:
    
    def create_event(self, db: Database, event_data: CalendarEventCreate, user_id: ObjectId) -> CalendarEventInDB:
        # Verify case ownership if case_id is provided
        if event_data.case_id:
            case = db.cases.find_one({
                "_id": ObjectId(event_data.case_id),
                "$or": [{"owner_id": user_id}, {"user_id": user_id}]
            })
            if not case:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Case not found or does not belong to the current user."
                )

        event_dict = event_data.model_dump()
        event_dict["owner_id"] = user_id
        
        if event_data.case_id:
            event_dict["case_id"] = str(event_data.case_id)
        else:
            event_dict["case_id"] = None
        
        now = datetime.now(timezone.utc)
        event_document = {
            **event_dict,
            "created_at": now,
            "updated_at": now,
            "status": EventStatus.PENDING
        }

        result = db.calendar_events.insert_one(event_document)
        created_event = db.calendar_events.find_one({"_id": result.inserted_id})
        
        if created_event:
            # PHOENIX FIX: Manual string conversion for robustness
            created_event['id'] = str(created_event['_id'])
            if 'case_id' in created_event and isinstance(created_event['case_id'], ObjectId):
                created_event['case_id'] = str(created_event['case_id'])
            
            return CalendarEventInDB.model_validate(created_event)
        
        raise HTTPException(status_code=500, detail="Failed to retrieve created event.")

    def get_events_for_user(self, db: Database, user_id: ObjectId) -> List[CalendarEventInDB]:
        events_cursor = db.calendar_events.find({"owner_id": user_id}).sort("start_date", 1)
        events = []
        for event_doc in events_cursor:
            event_doc['id'] = str(event_doc['_id'])
            if 'case_id' in event_doc and isinstance(event_doc['case_id'], ObjectId):
                event_doc['case_id'] = str(event_doc['case_id'])
            
            events.append(CalendarEventInDB.model_validate(event_doc))
        return events

    def delete_event(self, db: Database, event_id: ObjectId, user_id: ObjectId) -> bool:
        delete_result = db.calendar_events.delete_one(
            {"_id": event_id, "owner_id": user_id}
        )
        if delete_result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Event not found.")
        return True

    def get_upcoming_alerts_count(self, db: Database, user_id: ObjectId, days: int = 7) -> int:
        now = datetime.now(timezone.utc)
        future = now + timedelta(days=days)
        
        # Robust query matching both ISO strings and Date objects
        now_str = now.isoformat()
        future_str = future.isoformat()

        query = {
            "owner_id": user_id,
            "status": "PENDING",
            "$or": [
                {"start_date": {"$gte": now, "$lt": future}},
                {"start_date": {"$gte": now_str, "$lt": future_str}}
            ]
        }
        
        return db.calendar_events.count_documents(query)

# --- CRITICAL INSTANTIATION ---
calendar_service = CalendarService()