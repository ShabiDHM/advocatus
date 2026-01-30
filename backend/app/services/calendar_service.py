# FILE: backend/app/services/calendar_service.py
# PHOENIX PROTOCOL - CALENDAR SERVICE V3.0 (RISK RADAR CORE)
from typing import List, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta, date
from bson import ObjectId
from fastapi import HTTPException, status
from pymongo.database import Database

from app.models.calendar import CalendarEventInDB, CalendarEventCreate, EventStatus

# --- RISK RADAR TRIAGE CONFIGURATION ---
TRIAGE_KEYWORDS = {
    "LEVEL_1_PREKLUZIV": [
        'ankesë', 'padi', 'kundërpadi', 'parashkrim', 'prapësim', 
        'mjet i jashtëzakonshëm', 'afat prekluziv', 'appeal', 'lawsuit', 'rekomandim'
    ],
    "LEVEL_2_GJYQESOR": [
        'urdhër', 'aktvendim', 'dorëzim', 'ekspertizë', 'parashtresë', 
        'listë e dëshmitarëve', 'përgjigje në padi', 'court order', 'provë'
    ]
}

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

    def get_event_triage(self, title: str) -> str:
        """Determines the legal consequence level."""
        t_low = title.lower()
        if any(k in t_low for k in TRIAGE_KEYWORDS["LEVEL_1_PREKLUZIV"]): return "LEVEL_1_PREKLUZIV"
        if any(k in t_low for k in TRIAGE_KEYWORDS["LEVEL_2_GJYQESOR"]): return "LEVEL_2_GJYQESOR"
        return "LEVEL_3_PROCEDURAL"

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

    def generate_briefing(self, db: Database, user_id: ObjectId, user_name: str) -> Dict[str, Any]:
        """The Guardian Briefing Engine with Risk Radar Triage."""
        now = datetime.now(timezone.utc)
        today = now.date()
        safe_name = str(user_name or "Avokat").title()
        
        # 1. Triage Imminent Risks (Next 48 Hours)
        radar_items = []
        future_limit = now + timedelta(hours=48)
        events = db.calendar_events.find({
            "owner_id": user_id,
            "status": EventStatus.PENDING,
            "start_date": {"$gte": now, "$lte": future_limit}
        }).sort("start_date", 1)

        for e in events:
            level = self.get_event_triage(e['title'])
            diff = e['start_date'] - now
            radar_items.append({
                "id": str(e['_id']),
                "title": e['title'],
                "level": level,
                "seconds_remaining": int(diff.total_seconds()),
                "effective_deadline": e['start_date'].isoformat()
            })

        # 2. General Briefing Context
        urgent_count = self.get_upcoming_alerts_count(db, user_id)
        hour = now.hour + 1
        g_key = "morning" if 5 <= hour < 12 else ("afternoon" if 12 <= hour < 18 else "evening")
        
        status_type = "OPTIMAL"
        if any(i['level'] == "LEVEL_1_PREKLUZIV" for i in radar_items): status_type = "CRITICAL"
        elif any(i['level'] == "LEVEL_2_GJYQESOR" for i in radar_items) or urgent_count > 0: status_type = "WARNING"

        resp_data = {
            "name": safe_name, 
            "count": urgent_count,
            "quote_key": f"quote_{(today.timetuple().tm_yday % 10) + 1}"
        }

        # 3. Holiday/Weekend Override
        if today in KOSOVO_HOLIDAYS_MAP:
            resp_data["holiday"] = KOSOVO_HOLIDAYS_MAP[today]
            return {"greeting_key": "holiday_greet", "message_key": "holiday_msg", "status": "HOLIDAY", "data": resp_data, "risk_radar": radar_items}

        if today.weekday() >= 5:
            return {"greeting_key": g_key, "message_key": "weekend_msg" if today.weekday() == 5 else "sunday_msg", "status": "WEEKEND", "data": resp_data, "risk_radar": radar_items}

        return {
            "greeting_key": g_key, 
            "message_key": f"work_{status_type.lower()}_msg", 
            "status": status_type, 
            "data": resp_data,
            "risk_radar": radar_items
        }

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
                "is_extended": is_ext,
                "risk_level": self.get_event_triage(val.title)
            })
            enriched.append(item)
        return enriched

    def create_event(self, db: Database, event_data: CalendarEventCreate, user_id: ObjectId) -> CalendarEventInDB:
        d = event_data.model_dump()
        d.update({"owner_id": user_id, "case_id": str(event_data.case_id) if event_data.case_id else None, "created_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc), "status": EventStatus.PENDING, "is_public": False})
        res = db.calendar_events.insert_one(d)
        created = db.calendar_events.find_one({"_id": res.inserted_id})
        if not created: raise HTTPException(500, "Creation Failed")
        created['id'] = str(created['_id'])
        return CalendarEventInDB.model_validate(created)

    def delete_event(self, db: Database, event_id: ObjectId, user_id: ObjectId) -> bool:
        if db.calendar_events.delete_one({"_id": event_id, "owner_id": user_id}).deleted_count == 0: 
            raise HTTPException(404, "Not Found")
        return True

    def get_upcoming_alerts_count(self, db: Database, user_id: ObjectId, days: int = 7) -> int:
        now = datetime.now(timezone.utc)
        return db.calendar_events.count_documents({"owner_id": user_id, "status": EventStatus.PENDING, "start_date": {"$gte": now, "$lt": now + timedelta(days=days)}})

calendar_service = CalendarService()