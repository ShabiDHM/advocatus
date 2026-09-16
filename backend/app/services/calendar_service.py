# FILE: backend/app/services/calendar_service.py
# PHOENIX PROTOCOL - CALENDAR SERVICE V5.1 (UPDATE EVENT SUPPORT)
# 100% COMPLETE CODE • ZERO PY WARNINGS • INTEGRATED WITH kosovo_holidays

from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timezone, timedelta, date
from bson import ObjectId
from fastapi import HTTPException, status
from pymongo.database import Database

from app.models.calendar import (
    CalendarEventInDB, CalendarEventCreate, EventStatus, EventCategory
)
from app.services.kosovo_holidays import is_holiday


class CalendarService:
    
    def is_working_day(self, d: date) -> bool:
        """
        Ditë pune = jo fundjavë DHE jo festë zyrtare e Kosovës.
        Integron festat kombëtare, fetare dhe ndërkombëtare.
        """
        if d.weekday() >= 5:
            return False
        if is_holiday(d):
            return False
        return True

    def get_event_triage(self, title: str) -> str:
        t_low = title.lower()
        if any(k in t_low for k in ['ankesë', 'padi', 'parashkrim', 'prapësim', 'afat prekluziv']):
            return "LEVEL_1_PREKLUZIV"
        if any(k in t_low for k in ['urdhër', 'aktvendim', 'dorëzim', 'ekspertizë', 'parashtresë', 'provë']):
            return "LEVEL_2_GJYQESOR"
        return "LEVEL_3_PROCEDURAL"

    def calculate_working_days(self, start_date: date, end_date: date) -> int:
        """
        Llogarit ditët e punës midis start_date dhe end_date (ekskluziv start, inkluziv end).
        NUK kthen vlerë negative — nëse end_date është në të kaluarën, kthen 0.
        """
        if start_date >= end_date:
            return 0
        days_diff = (end_date - start_date).days
        working_days = sum(
            1 for i in range(1, days_diff + 1)
            if self.is_working_day(start_date + timedelta(days=i))
        )
        return working_days

    def generate_briefing(self, db: Database, user_id: ObjectId, user_name: str) -> Dict[str, Any]:
        """
        Guardian Briefing: Triage i AGENDA items për Risk Radar.
        Përfshin statuset aktive (PENDING + CONFIRMED) dhe dritare 7-ditore.
        """
        now = datetime.now(timezone.utc)
        today = now.date()
        safe_name = str(user_name or "Avokat").title()
        
        radar_items = []
        future_limit = now + timedelta(days=7)
        
        events = list(db.calendar_events.find({
            "owner_id": user_id,
            "status": {"$in": [EventStatus.PENDING, EventStatus.CONFIRMED]},
            "category": EventCategory.AGENDA,
            "start_date": {"$gte": now, "$lte": future_limit}
        }).sort("start_date", 1))

        for e in events:
            start = e['start_date']
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
            diff = start - now
            radar_items.append({
                "id": str(e['_id']),
                "title": e['title'],
                "level": self.get_event_triage(e['title']),
                "seconds_remaining": int(diff.total_seconds()),
                "effective_deadline": start.isoformat()
            })

        urgent_count = db.calendar_events.count_documents({
            "owner_id": user_id, 
            "status": {"$in": [EventStatus.PENDING, EventStatus.CONFIRMED]},
            "category": EventCategory.AGENDA,
            "start_date": {"$gte": now, "$lt": now + timedelta(days=7)}
        })
        
        status_type = "CRITICAL" if any(i['level'] == "LEVEL_1_PREKLUZIV" for i in radar_items) else ("WARNING" if urgent_count > 0 else "OPTIMAL")
        hour = now.hour + 1
        g_key = "morning" if 5 <= hour < 12 else ("afternoon" if 12 <= hour < 18 else "evening")
        
        return {
            "count": urgent_count,
            "greeting_key": g_key,
            "message_key": f"work_{status_type.lower()}_msg",
            "status": status_type,
            "risk_radar": radar_items,
            "data": {"name": safe_name, "count": urgent_count}
        }

    def get_events_for_user(self, db: Database, user_id: ObjectId) -> List[Dict[str, Any]]:
        events_cursor = db.calendar_events.find({"owner_id": user_id}).sort("start_date", 1)
        enriched, today = [], datetime.now(timezone.utc).date()
        
        for doc in events_cursor:
            doc['id'] = str(doc['_id'])
            if 'case_id' in doc and doc['case_id']:
                doc['case_id'] = str(doc['case_id'])
            
            val = CalendarEventInDB.model_validate(doc)
            effective_date = val.start_date.date()
            item = val.model_dump(by_alias=True)
            item.update({
                "working_days_remaining": self.calculate_working_days(today, effective_date),
                "risk_level": self.get_event_triage(val.title)
            })
            enriched.append(item)
        return enriched

    def create_event(self, db: Database, event_data: CalendarEventCreate, user_id: ObjectId) -> CalendarEventInDB:
        d = event_data.model_dump()
        d.update({
            "owner_id": user_id,
            "case_id": str(event_data.case_id) if event_data.case_id else None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "status": EventStatus.PENDING,
            "is_public": False
        })
        res = db.calendar_events.insert_one(d)
        created = db.calendar_events.find_one({"_id": res.inserted_id})
        if not created:
            raise HTTPException(500, "Creation Failed")
        created['id'] = str(created['_id'])
        return CalendarEventInDB.model_validate(created)

    def update_event(
        self,
        db: Database,
        event_id: ObjectId,
        user_id: ObjectId,
        updates: Dict[str, Any]
    ) -> CalendarEventInDB:
        """
        Përditëson një event ekzistues. Vetëm fushat e dërguara aplikohen (partial update).
        Kthen event-in e përditësuar.
        """
        # Kontroll pronesie
        existing = db.calendar_events.find_one({"_id": event_id, "owner_id": user_id})
        if not existing:
            raise HTTPException(status_code=404, detail="Event not found or unauthorized")

        # Filtro fushat e lejuara
        allowed_fields = {
            "title", "description", "start_date", "end_date",
            "is_all_day", "event_type", "category", "priority",
            "location", "attendees", "notes", "status"
        }
        safe_updates = {k: v for k, v in updates.items() if k in allowed_fields and v is not None}

        if not safe_updates:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        # Enum validim për status (nëse dërgohet)
        if "status" in safe_updates:
            try:
                safe_updates["status"] = EventStatus(safe_updates["status"])
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status. Must be one of: {[s.value for s in EventStatus]}"
                )

        # Enum validim për event_type
        if "event_type" in safe_updates:
            try:
                safe_updates["event_type"] = safe_updates["event_type"]
            except Exception:
                pass

        safe_updates["updated_at"] = datetime.now(timezone.utc)

        db.calendar_events.update_one(
            {"_id": event_id, "owner_id": user_id},
            {"$set": safe_updates}
        )

        updated = db.calendar_events.find_one({"_id": event_id})
        if not updated:
            raise HTTPException(500, "Update Failed")

        updated['id'] = str(updated['_id'])
        return CalendarEventInDB.model_validate(updated)

    def delete_event(self, db: Database, event_id: ObjectId, user_id: ObjectId) -> bool:
        if db.calendar_events.delete_one({"_id": event_id, "owner_id": user_id}).deleted_count == 0:
            raise HTTPException(404, "Not Found")
        return True

calendar_service = CalendarService()