# FILE: backend/app/services/calendar_service.py
# PHOENIX PROTOCOL - CALENDAR SERVICE V2.5 (PARAMETER ALIGNMENT & WISDOM)
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timezone, timedelta, date
from bson import ObjectId
from fastapi import HTTPException, status
from pymongo.database import Database

from app.models.calendar import CalendarEventInDB, CalendarEventCreate, EventStatus

KOSOVO_HOLIDAYS_MAP: Dict[date, str] = {
    date(2026, 1, 1): "new_year", date(2026, 1, 2): "new_year",
    date(2026, 1, 7): "orthodox_christmas", date(2026, 2, 17): "independence_day",
    date(2026, 4, 9): "constitution_day", date(2026, 4, 3): "catholic_easter",
    date(2026, 4, 5): "catholic_easter", date(2026, 4, 10): "orthodox_easter",
    date(2026, 4, 12): "orthodox_easter", date(2026, 5, 1): "labor_day",
    date(2026, 5, 9): "europe_day", date(2026, 12, 25): "catholic_christmas",
    date(2026, 3, 21): "fiter_bajram", date(2026, 3, 22): "fiter_bajram",
    date(2026, 5, 28): "kurban_bajram", date(2026, 5, 29): "kurban_bajram",
}

class CalendarService:
    
    def is_working_day(self, d: date) -> bool:
        if d.weekday() >= 5: return False
        return d not in KOSOVO_HOLIDAYS_MAP

    def get_effective_deadline(self, target_date: date) -> Tuple[date, bool]:
        current, extended = target_date, False
        while not self.is_working_day(current):
            current += timedelta(days=1)
            extended = True
        return current, extended

    def calculate_working_days(self, start_date: date, end_date: date) -> int:
        if start_date > end_date: return -1 * (start_date - end_date).days
        days_diff = (end_date - start_date).days
        working_days = sum(1 for i in range(days_diff + 1) if self.is_working_day(start_date + timedelta(days=i)))
        return working_days - 1

    def generate_briefing(self, user_name: str, urgent_count: int) -> Dict[str, Any]:
        """Ensures the name is titled and quotes are generated for Optimal status."""
        now = datetime.now(timezone.utc)
        today = now.date()
        hour = now.hour + 1
        
        # PHOENIX FIX: Guaranteed Title Case (e.g. Shaban Bala)
        safe_name = str(user_name or "Avokat").title()
        
        if 5 <= hour < 12: g_key = "morning"
        elif 12 <= hour < 18: g_key = "afternoon"
        else: g_key = "evening"

        resp_data = {"name": safe_name, "count": urgent_count}
        status_type = "OPTIMAL" if urgent_count == 0 else ("WARNING" if urgent_count <= 2 else "CRITICAL")

        if today in KOSOVO_HOLIDAYS_MAP:
            resp_data["holiday"] = KOSOVO_HOLIDAYS_MAP[today]
            return {"greeting_key": "holiday_greet", "message_key": "holiday_msg", "status": "HOLIDAY", "data": resp_data}

        if today.weekday() >= 5:
            return {"greeting_key": g_key, "message_key": "weekend_msg" if today.weekday() == 5 else "sunday_msg", "status": "WEEKEND", "data": resp_data}

        if status_type == "OPTIMAL":
            day_of_year = today.timetuple().tm_yday
            resp_data["quote_key"] = f"quote_{(day_of_year % 10) + 1}"

        return {"greeting_key": g_key, "message_key": f"work_{status_type.lower()}_msg", "status": status_type, "data": resp_data}

    def get_events_for_user(self, db: Database, user_id: ObjectId) -> List[Dict[str, Any]]:
        events_cursor = db.calendar_events.find({"owner_id": user_id}).sort("start_date", 1)
        enriched, today = [], datetime.now(timezone.utc).date()
        for doc in events_cursor:
            doc['id'] = str(doc['_id'])
            if 'case_id' in doc and doc['case_id']: doc['case_id'] = str(doc['case_id'])
            val = CalendarEventInDB.model_validate(doc)
            eff_date, is_ext = self.get_effective_deadline(val.start_date.date())
            item = val.model_dump(by_alias=True)
            item.update({
                "working_days_remaining": self.calculate_working_days(today, eff_date),
                "effective_deadline": datetime(eff_date.year, eff_date.month, eff_date.day, tzinfo=timezone.utc),
                "is_extended": is_ext
            })
            enriched.append(item)
        return enriched

    def create_event(self, db: Database, event_data: CalendarEventCreate, user_id: ObjectId) -> CalendarEventInDB:
        """PHOENIX FIX: Parameter names aligned to calendar.py calls."""
        event_dict = event_data.model_dump()
        event_dict.update({
            "owner_id": user_id, 
            "case_id": str(event_data.case_id) if event_data.case_id else None, 
            "created_at": datetime.now(timezone.utc), 
            "updated_at": datetime.now(timezone.utc), 
            "status": EventStatus.PENDING, 
            "is_public": False
        })
        res = db.calendar_events.insert_one(event_dict)
        created = db.calendar_events.find_one({"_id": res.inserted_id})
        if not created: raise HTTPException(500, "Creation Failed")
        created['id'] = str(created['_id'])
        return CalendarEventInDB.model_validate(created)

    def delete_event(self, db: Database, event_id: ObjectId, user_id: ObjectId) -> bool:
        """PHOENIX FIX: Parameter names aligned to calendar.py calls."""
        if db.calendar_events.delete_one({"_id": event_id, "owner_id": user_id}).deleted_count == 0: 
            raise HTTPException(404, "Not Found")
        return True

    def get_upcoming_alerts_count(self, db: Database, user_id: ObjectId, days: int = 7) -> int:
        now = datetime.now(timezone.utc)
        return db.calendar_events.count_documents({
            "owner_id": user_id, 
            "status": EventStatus.PENDING, 
            "start_date": {"$gte": now, "$lt": now + timedelta(days=days)}
        })

calendar_service = CalendarService()