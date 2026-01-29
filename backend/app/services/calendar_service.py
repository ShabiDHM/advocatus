# FILE: backend/app/services/calendar_service.py
# PHOENIX PROTOCOL - KUJDESTARI ENGINE V1.0 (KOSOVO HOLIDAYS & LEGAL TRIAGE)
# 1. FEAT: Added 'KOSOVO_HOLIDAYS_2026' set for culturally-aware date calculations.
# 2. FEAT: Implemented 'is_working_day' and 'calculate_working_days' to count only valid workdays.
# 3. LOGIC: Augmented 'get_events_for_user' to inject 'severity' and 'working_days_remaining' into every event.

from typing import List, Dict, Any, Set
from datetime import datetime, timezone, timedelta, date
from bson import ObjectId
from fastapi import HTTPException, status
from pymongo.database import Database

from app.models.calendar import CalendarEventInDB, CalendarEventCreate, EventStatus

# --- KUJDESTARI ENGINE: HOLIDAY & KEYWORD LIBRARY ---

# Official and major religious holidays in Kosovo for 2026.
# This list is the core of the cultural intelligence.
KOSOVO_HOLIDAYS_2026: Set[date] = {
    # Official State Holidays
    date(2026, 1, 1),   # Viti i Ri
    date(2026, 1, 2),   # Viti i Ri
    date(2026, 1, 7),   # Krishtlindjet Ortodokse
    date(2026, 2, 17),  # Dita e Pavarësisë
    date(2026, 4, 9),   # Dita e Kushtetutës
    date(2026, 4, 3),   # Pashkët Katolike (Good Friday - often taken off)
    date(2026, 4, 5),   # Pashkët Katolike
    date(2026, 4, 10),  # Pashkët Ortodokse (Good Friday)
    date(2026, 4, 12),  # Pashkët Ortodokse
    date(2026, 5, 1),   # Dita e Punëtorëve
    date(2026, 5, 9),   # Dita e Evropës
    date(2026, 12, 25), # Krishtlindjet Katolike

    # Religious Holidays (Estimated for 2026 - confirm annually)
    # Fitër Bajrami (approx dates, usually a 2-day public holiday)
    date(2026, 3, 21),
    date(2026, 3, 22), 
    # Kurban Bajrami (approx dates)
    date(2026, 5, 28),
    date(2026, 5, 29),
}

# Keywords to determine the legal consequence of a deadline.
PRECLUSIVE_KEYWORDS = ['ankesë', 'padi', 'kundërpadi', 'parashkrim', 'afat i fundit', 'prekluziv', 'appeal', 'complaint', 'lawsuit']
JUDICIAL_KEYWORDS = ['urdhër', 'gjyqësor', 'dorëzim', 'parashtresë', 'përgjigje', 'ekspertizë', 'court order', 'submission', 'response']


class CalendarService:
    
    # --- KUJDESTARI ENGINE: HELPER FUNCTIONS ---

    def is_working_day(self, d: date) -> bool:
        """Checks if a date is a weekend or a Kosovo public holiday."""
        if d.weekday() >= 5:  # Saturday or Sunday
            return False
        if d in KOSOVO_HOLIDAYS_2026:
            return False
        return True

    def calculate_working_days(self, start_date: date, end_date: date) -> int:
        """Calculates the number of working days between two dates, inclusive of start."""
        if start_date > end_date:
            return 0
        
        # Legal Rule: If deadline falls on a holiday/weekend, it's the next working day.
        # While the deadline itself is extended, the *sense of urgency* should reflect the original date.
        # We calculate based on the actual calendar days to show true time pressure.
        
        days_diff = (end_date - start_date).days
        working_days = 0
        for i in range(days_diff + 1):
            current_day = start_date + timedelta(days=i)
            if self.is_working_day(current_day):
                working_days += 1
        
        # The lawyer needs to work on the day of the deadline, so we subtract 1.
        # 0 means "Today is the last working day". -1 means "You missed it".
        return working_days - 1

    def get_event_severity(self, event_title: str) -> str:
        """Assigns a severity level based on keywords in the event title."""
        title_lower = event_title.lower()
        if any(keyword in title_lower for keyword in PRECLUSIVE_KEYWORDS):
            return "PREKLUZIV"
        if any(keyword in title_lower for keyword in JUDICIAL_KEYWORDS):
            return "GJYQESOR"
        return "PROCEDURAL"

    # --- CORE SERVICE METHODS (MODIFIED) ---

    def create_event(self, db: Database, event_data: CalendarEventCreate, user_id: ObjectId) -> CalendarEventInDB:
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
            created_event['id'] = str(created_event['_id'])
            if 'case_id' in created_event and isinstance(created_event['case_id'], ObjectId):
                created_event['case_id'] = str(created_event['case_id'])
            
            return CalendarEventInDB.model_validate(created_event)
        
        raise HTTPException(status_code=500, detail="Failed to retrieve created event.")

    def get_events_for_user(self, db: Database, user_id: ObjectId) -> List[Dict[str, Any]]:
        """
        PHOENIX MODIFICATION: This now returns a list of enriched dictionaries,
        not just CalendarEventInDB models, to include our new intelligent fields.
        """
        events_cursor = db.calendar_events.find({"owner_id": user_id}).sort("start_date", 1)
        
        enriched_events = []
        today = datetime.now(timezone.utc).date()

        for event_doc in events_cursor:
            # Standard data validation and formatting
            event_doc['id'] = str(event_doc['_id'])
            if 'case_id' in event_doc and isinstance(event_doc['case_id'], ObjectId):
                event_doc['case_id'] = str(event_doc['case_id'])
            
            validated_event = CalendarEventInDB.model_validate(event_doc)
            event_dict = validated_event.model_dump(by_alias=True)
            
            # --- KUJDESTARI INTELLIGENCE INJECTION ---
            event_date = validated_event.start_date.date()
            
            # 1. Calculate working days remaining
            working_days_remaining = self.calculate_working_days(today, event_date)
            
            # 2. Determine severity
            severity = self.get_event_severity(validated_event.title)

            # 3. Add the new fields to the response payload
            event_dict["working_days_remaining"] = working_days_remaining
            event_dict["severity"] = severity
            
            enriched_events.append(event_dict)
            
        return enriched_events

    def delete_event(self, db: Database, event_id: ObjectId, user_id: ObjectId) -> bool:
        delete_result = db.calendar_events.delete_one(
            {"_id": event_id, "owner_id": user_id}
        )
        if delete_result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Event not found.")
        return True

    def get_upcoming_alerts_count(self, db: Database, user_id: ObjectId, days: int = 7) -> int:
        # This function is now less important as the main logic is in get_events_for_user,
        # but we'll keep it for potential other uses.
        now = datetime.now(timezone.utc)
        future = now + timedelta(days=days)
        
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