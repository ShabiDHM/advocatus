# FILE: backend/app/services/calendar_service.py
# PHOENIX PROTOCOL - CALENDAR SERVICE V2.3 (WISDOM ENGINE)
from typing import List, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta, date
from bson import ObjectId
from fastapi import HTTPException, status
from pymongo.database import Database

from app.models.calendar import CalendarEventInDB, CalendarEventCreate, EventStatus

# --- KUJDESTARI ENGINE: HOLIDAY MAP ---
KOSOVO_HOLIDAYS_MAP: Dict[date, str] = {
    date(2026, 1, 1): "new_year",
    date(2026, 1, 2): "new_year",
    date(2026, 1, 7): "orthodox_christmas",
    date(2026, 2, 17): "independence_day",
    date(2026, 4, 9): "constitution_day",
    date(2026, 4, 3): "catholic_easter",
    date(2026, 4, 5): "catholic_easter",
    date(2026, 4, 10): "orthodox_easter",
    date(2026, 4, 12): "orthodox_easter",
    date(2026, 5, 1): "labor_day",
    date(2026, 5, 9): "europe_day",
    date(2026, 12, 25): "catholic_christmas",
    date(2026, 3, 21): "fiter_bajram",
    date(2026, 3, 22): "fiter_bajram",
    date(2026, 5, 28): "kurban_bajram",
    date(2026, 5, 29): "kurban_bajram",
}

class CalendarService:
    
    def is_working_day(self, d: date) -> bool:
        if d.weekday() >= 5: return False
        if d in KOSOVO_HOLIDAYS_MAP: return False
        return True

    def get_effective_deadline(self, target_date: date) -> Tuple[date, bool]:
        current = target_date
        extended = False
        while not self.is_working_day(current):
            current += timedelta(days=1)
            extended = True
        return current, extended

    def calculate_working_days(self, start_date: date, end_date: date) -> int:
        if start_date > end_date: return -1 * (start_date - end_date).days
        days_diff = (end_date - start_date).days
        working_days = 0
        for i in range(days_diff + 1):
            if self.is_working_day(start_date + timedelta(days=i)):
                working_days += 1
        return working_days - 1

    def generate_briefing(self, user_name: str, urgent_count: int) -> Dict[str, Any]:
        """Produces i18n keys and rotates motivational quotes on Optimal status."""
        now = datetime.now(timezone.utc)
        today = now.date()
        hour = now.hour + 1
        
        if 5 <= hour < 12: g_key = "morning"
        elif 12 <= hour < 18: g_key = "afternoon"
        else: g_key = "evening"

        # Base response data
        resp_data = {"name": user_name, "count": urgent_count}

        # 1. Holiday Logic
        if today in KOSOVO_HOLIDAYS_MAP:
            resp_data["holiday"] = KOSOVO_HOLIDAYS_MAP[today]
            return {
                "greeting_key": "holiday_greet",
                "message_key": "holiday_msg",
                "status": "HOLIDAY",
                "data": resp_data
            }

        # 2. Weekend Logic
        if today.weekday() >= 5:
            return {
                "greeting_key": g_key,
                "message_key": "weekend_msg" if today.weekday() == 5 else "sunday_msg",
                "status": "WEEKEND",
                "data": resp_data
            }

        # 3. Work Day Logic + Quote Injection
        status_type = "OPTIMAL" if urgent_count == 0 else ("WARNING" if urgent_count <= 2 else "CRITICAL")
        
        if status_type == "OPTIMAL":
            # Rotate through 10 quotes based on the day of the year
            day_of_year = today.timetuple().tm_yday
            resp_data["quote_key"] = f"quote_{ (day_of_year % 10) + 1 }"

        return {
            "greeting_key": g_key,
            "message_key": f"work_{status_type.lower()}_msg",
            "status": status_type,
            "data": resp_data
        }

    def get_events_for_user(self, db: Database, user_id: ObjectId) -> List[Dict[str, Any]]:
        events_cursor = db.calendar_events.find({"owner_id": user_id}).sort("start_date", 1)
        enriched = []
        today = datetime.now(timezone.utc).date()
        for doc in events_cursor:
            doc['id'] = str(doc['_id'])
            if 'case_id' in doc and doc['case_id']: doc['case_id'] = str(doc['case_id'])
            val = CalendarEventInDB.model_validate(doc)
            original_date = val.start_date.date()
            effective_date, is_extended = self.get_effective_deadline(original_date)
            item = val.model_dump(by_alias=True)
            item.update({
                "working_days_remaining": self.calculate_working_days(today, effective_date),
                "effective_deadline": datetime(effective_date.year, effective_date.month, effective_date.day, tzinfo=timezone.utc),
                "is_extended": is_extended
            })
            enriched.append(item)
        return enriched

    def create_event(self, db: Database, event_data: CalendarEventCreate, user_id: ObjectId) -> CalendarEventInDB:
        event_dict = event_data.model_dump()
        event_dict["owner_id"] = user_id
        event_dict["case_id"] = str(event_data.case_id) if event_data.case_id else None
        now = datetime.now(timezone.utc)
        event_dict.update({"created_at": now, "updated_at": now, "status": EventStatus.PENDING, "is_public": False})
        result = db.calendar_events.insert_one(event_dict)
        created = db.calendar_events.find_one({"_id": result.inserted_id})
        if created is None: raise HTTPException(500, "Creation Failed")
        created['id'] = str(created['_id'])
        return CalendarEventInDB.model_validate(created)

    def delete_event(self, db: Database, event_id: ObjectId, user_id: ObjectId) -> bool:
        if db.calendar_events.delete_one({"_id": event_id, "owner_id": user_id}).deleted_count == 0:
            raise HTTPException(404, "Event not found")
        return True

    def get_upcoming_alerts_count(self, db: Database, user_id: ObjectId, days: int = 7) -> int:
        now = datetime.now(timezone.utc)
        future = now + timedelta(days=days)
        return db.calendar_events.count_documents({
            "owner_id": user_id, 
            "status": EventStatus.PENDING, 
            "start_date": {"$gte": now, "$lt": future}
        })

calendar_service = CalendarService()