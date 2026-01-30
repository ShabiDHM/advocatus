# FILE: backend/app/services/calendar_service.py
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timezone, timedelta, date
from bson import ObjectId
from fastapi import HTTPException, status
from pymongo.database import Database

from app.models.calendar import CalendarEventInDB, CalendarEventCreate, EventStatus

# --- KUJDESTARI ENGINE: HOLIDAY MAP (Translation Keys) ---
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
    # Variable Dates
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
            if self.is_working_day(start_date + timedelta(days=i)): working_days += 1
        return working_days - 1

    def generate_briefing(self, user_name: str, urgent_count: int) -> Dict[str, Any]:
        """
        PHOENIX V2: Returns keys and data for frontend i18n translation.
        """
        now = datetime.now(timezone.utc)
        today = now.date()
        hour = now.hour + 1 # Simple UTC+1 adjustment
        
        # 1. Greeting Key
        if 5 <= hour < 12: g_key = "morning"
        elif 12 <= hour < 18: g_key = "afternoon"
        else: g_key = "evening"

        # 2. Holiday Logic
        if today in KOSOVO_HOLIDAYS_MAP:
            return {
                "greeting_key": "holiday_greet",
                "message_key": "holiday_msg",
                "status": "HOLIDAY",
                "data": {"name": user_name, "holiday": KOSOVO_HOLIDAYS_MAP[today]}
            }

        # 3. Weekend Logic
        if today.weekday() >= 5:
            return {
                "greeting_key": g_key,
                "message_key": "weekend_msg" if today.weekday() == 5 else "sunday_msg",
                "status": "WEEKEND",
                "data": {"name": user_name}
            }

        # 4. Work Day Logic
        status_type = "OPTIMAL" if urgent_count == 0 else ("WARNING" if urgent_count <= 2 else "CRITICAL")
        return {
            "greeting_key": g_key,
            "message_key": f"work_{status_type.lower()}_msg",
            "status": status_type,
            "data": {"name": user_name, "count": urgent_count}
        }

    def get_events_for_user(self, db: Database, user_id: ObjectId) -> List[Dict[str, Any]]:
        events_cursor = db.calendar_events.find({"owner_id": user_id}).sort("start_date", 1)
        enriched = []
        today = datetime.now(timezone.utc).date()
        for doc in events_cursor:
            doc['id'] = str(doc['_id'])
            if 'case_id' in doc: doc['case_id'] = str(doc['case_id'])
            val = CalendarEventInDB.model_validate(doc)
            e_date = val.start_date.date()
            eff_date, is_ext = self.get_effective_deadline(e_date)
            
            item = val.model_dump(by_alias=True)
            item.update({
                "working_days_remaining": self.calculate_working_days(today, eff_date),
                "effective_deadline": datetime(eff_date.year, eff_date.month, eff_date.day),
                "is_extended": is_ext
            })
            enriched.append(item)
        return enriched

    def create_event(self, db, data, u_id):
        # Implementation remains the same as previous synchronized state
        d = data.model_dump(); d["owner_id"] = u_id; d["case_id"] = str(data.case_id) if data.case_id else None
        now = datetime.now(timezone.utc); d.update({"created_at": now, "updated_at": now, "status": EventStatus.PENDING})
        res = db.calendar_events.insert_one(d); created = db.calendar_events.find_one({"_id": res.inserted_id})
        created['id'] = str(created['_id']); return CalendarEventInDB.model_validate(created)

    def delete_event(self, db, e_id, u_id):
        if db.calendar_events.delete_one({"_id": e_id, "owner_id": u_id}).deleted_count == 0:
            raise HTTPException(404, "Event not found")
        return True

    def get_upcoming_alerts_count(self, db, u_id, days=7):
        now = datetime.now(timezone.utc); fut = now + timedelta(days=days)
        return db.calendar_events.count_documents({"owner_id": u_id, "status": "PENDING", "start_date": {"$gte": now, "$lt": fut}})

calendar_service = CalendarService()