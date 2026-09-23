# FILE: backend/app/services/calendar_service.py
# PHOENIX PROTOCOL - CALENDAR SERVICE V7.0 (CASE-SCOPED ORG-AWARE)
# V7.0: CASE-SCOPED — event-et e një case-i shpërndahen midis të gjithë anëtarëve
#        me akses (org-aware). Event-et personale (case_id=None) mbeten vetëm owner.
#        - get_events_for_user: owner OR case me akses
#        - update_event/delete_event: verifiko akses përmes case-it
#        - generate_briefing: përfshin event-et e case-ve të përbashkëta
# V6.0: VOICE → EVENT PARSER.

import logging
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timezone, timedelta, date
from bson import ObjectId
from fastapi import HTTPException, status
from pymongo.database import Database

from app.models.calendar import CalendarEventInDB, CalendarEventCreate, EventStatus, EventCategory
from app.services.kosovo_holidays import is_holiday

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# V7.0: HELPERS — case-scoped access
# ═══════════════════════════════════════════════════════════════════════════

def _get_user_accessible_case_ids(db: Database, user) -> List[Any]:
    """
    Kthen listën e ID-ve të case-ve ku user ka akses (org-aware).
    Përdor _build_case_access_query nga case_service.
    Kthen listë me ObjectId + str për fleksibilitet.
    """
    try:
        from app.services.case_service import _build_case_access_query
        cases = db.cases.find(_build_case_access_query(user), {"_id": 1})
        ids = []
        for c in cases:
            cid = c["_id"]
            ids.append(cid)
            ids.append(str(cid))
        return ids
    except Exception as e:
        logger.warning(f"⚠️ [Calendar V7.0] Could not load accessible cases: {e}")
        return []


def _check_event_access(db: Database, event_doc: Dict[str, Any], user) -> bool:
    """
    V7.0: Kontrollon nëse user ka akses në një event.
    - Owner → gjithmonë OK
    - Event me case_id → kontrollo akses në case
    - Event personal i tjetrit → DENIED
    """
    if not event_doc:
        return False

    # 1. Owner?
    owner_id = event_doc.get("owner_id")
    if owner_id and str(owner_id) == str(user.id):
        return True

    # 2. Ka case_id?
    case_id = event_doc.get("case_id")
    if not case_id:
        return False  # event personal i tjetrit

    # 3. Kontrollo akses në case
    try:
        from app.services.case_service import get_case_for_user
        c_oid = ObjectId(case_id) if ObjectId.is_valid(str(case_id)) else case_id
        case = get_case_for_user(db, c_oid, user)
        return case is not None
    except Exception as e:
        logger.warning(f"⚠️ [Calendar V7.0] Access check failed for event {event_doc.get('_id')}: {e}")
        return False


class CalendarService:

    def is_working_day(self, d: date) -> bool:
        """Ditë pune = jo fundjavë DHE jo festë zyrtare e Kosovës."""
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
        """Llogarit ditët e punës midis start_date dhe end_date."""
        if start_date >= end_date:
            return 0
        days_diff = (end_date - start_date).days
        working_days = sum(
            1 for i in range(1, days_diff + 1)
            if self.is_working_day(start_date + timedelta(days=i))
        )
        return working_days

    def _build_events_query(self, db: Database, user) -> Dict[str, Any]:
        """
        V7.0: Query për event-et që user mund të shohë:
        - owner_id == user.id (event-et e veta)
        - OSE case_id IN case-t me akses (event-et e case-ve të përbashkëta)
        """
        case_ids = _get_user_accessible_case_ids(db, user)

        # Personal clauses
        personal = [
            {"owner_id": user.id},
            {"owner_id": str(user.id)},
        ]

        # Case-scoped clauses
        case_clauses: List[Dict[str, Any]] = []
        if case_ids:
            case_clauses.append({"case_id": {"$in": case_ids}})

        all_clauses = personal + case_clauses
        return {"$or": all_clauses}

    def generate_briefing(self, db: Database, user, user_name: str) -> Dict[str, Any]:
        """
        V7.0: Guardian Briefing — përfshin event-et e case-ve të përbashkëta.
        """
        # Backward compat: nëse user është vetëm user_id (i vjetër), kthehemi në mode personal
        if not hasattr(user, "id"):
            user_id = user
            now = datetime.now(timezone.utc)
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
            safe_name = str(user_name or "Avokat").title()
            return {
                "count": urgent_count,
                "greeting_key": g_key,
                "message_key": f"work_{status_type.lower()}_msg",
                "status": status_type,
                "risk_radar": radar_items,
                "data": {"name": safe_name, "count": urgent_count}
            }

        # V7.0: Full org-aware
        now = datetime.now(timezone.utc)
        safe_name = str(user_name or "Avokat").title()
        radar_items = []
        future_limit = now + timedelta(days=7)

        base_query = self._build_events_query(db, user)
        full_query = {
            "$and": [
                base_query,
                {
                    "status": {"$in": [EventStatus.PENDING, EventStatus.CONFIRMED]},
                    "category": EventCategory.AGENDA,
                    "start_date": {"$gte": now, "$lte": future_limit},
                }
            ]
        }

        events = list(db.calendar_events.find(full_query).sort("start_date", 1))

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

        count_query = {
            "$and": [
                base_query,
                {
                    "status": {"$in": [EventStatus.PENDING, EventStatus.CONFIRMED]},
                    "category": EventCategory.AGENDA,
                    "start_date": {"$gte": now, "$lt": now + timedelta(days=7)},
                }
            ]
        }
        urgent_count = db.calendar_events.count_documents(count_query)

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

    def get_events_for_user(self, db: Database, user) -> List[Dict[str, Any]]:
        """
        V7.0: Kthen event-et e user-it + event-et e case-ve ku ai ka akses.
        """
        # Backward compat: user_id i vjetër
        if not hasattr(user, "id"):
            query = {"owner_id": user}
        else:
            query = self._build_events_query(db, user)

        events_cursor = db.calendar_events.find(query).sort("start_date", 1)
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
        """
        V7.0: Krijon event. Nëse ka case_id, verifikohet aksesi.
        """
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
        user,  # V7.0: pranon UserInDB ose user_id (backward compat)
        updates: Dict[str, Any]
    ) -> CalendarEventInDB:
        """
        V7.0: Përditëson event. Kontrollon akses përmes owner OR case.
        """
        existing = db.calendar_events.find_one({"_id": event_id})
        if not existing:
            raise HTTPException(status_code=404, detail="Event not found")

        # V7.0: Kontroll aksesi
        if hasattr(user, "id"):
            has_access = _check_event_access(db, existing, user)
        else:
            # Backward compat
            has_access = str(existing.get("owner_id")) == str(user)

        if not has_access:
            raise HTTPException(status_code=404, detail="Event not found or unauthorized")

        allowed_fields = {
            "title", "description", "start_date", "end_date",
            "is_all_day", "event_type", "category", "priority",
            "location", "attendees", "notes", "status"
        }
        safe_updates = {k: v for k, v in updates.items() if k in allowed_fields and v is not None}

        if not safe_updates:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        if "status" in safe_updates:
            try:
                safe_updates["status"] = EventStatus(safe_updates["status"])
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status. Must be one of: {[s.value for s in EventStatus]}"
                )

        safe_updates["updated_at"] = datetime.now(timezone.utc)

        db.calendar_events.update_one(
            {"_id": event_id},
            {"$set": safe_updates}
        )

        updated = db.calendar_events.find_one({"_id": event_id})
        if not updated:
            raise HTTPException(500, "Update Failed")

        updated['id'] = str(updated['_id'])
        return CalendarEventInDB.model_validate(updated)

    def delete_event(self, db: Database, event_id: ObjectId, user) -> bool:
        """
        V7.0: Fshin event. Kontrollon akses përmes owner OR case.
        """
        existing = db.calendar_events.find_one({"_id": event_id})
        if not existing:
            raise HTTPException(404, "Not Found")

        # V7.0: Kontroll aksesi
        if hasattr(user, "id"):
            has_access = _check_event_access(db, existing, user)
        else:
            has_access = str(existing.get("owner_id")) == str(user)

        if not has_access:
            raise HTTPException(404, "Not Found")

        db.calendar_events.delete_one({"_id": event_id})
        return True

    # ==========================================================
    # VOICE → EVENT PARSER
    # ==========================================================
    def parse_voice_text_to_event(
        self,
        text: str,
        case_titles: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Analizon tekstin e transkriptuar nga zëri."""
        if not text or not text.strip():
            return {}

        from app.services.llm.llm_client import _call_llm, clean_and_parse_json

        try:
            from zoneinfo import ZoneInfo
            now = datetime.now(ZoneInfo("Europe/Belgrade"))
        except Exception:
            now = datetime.now(timezone.utc)

        today_str = now.strftime("%Y-%m-%d")
        weekday_sq = ["E Hënë", "E Martë", "E Mërkurë", "E Enjte", "E Premte", "E Shtunë", "E Diel"][now.weekday()]

        cases_context = ""
        if case_titles:
            cases_context = "\nRASTET E DISPONUESHME: " + ", ".join(case_titles[:50])

        system_prompt = f"""Ti je asistent i inteligjent ligjor. Detyra jote është të analizosh tekstin e transkriptuar nga zëri dhe të nxjerrësh të dhëna të strukturuara për një event ose shënim kalendarik.

DATA E SOTME: {today_str} ({weekday_sq}){cases_context}

KATEGORITË:
- "AGENDA" = event i planifikuar (takim, seancë, afat, dorëzim, seancë gjyqësore)
- "FACT" = shënim memo, pa datë specifike ose pa veprim të planifikuar

TIPET E EVENT-IT:
- "DEADLINE" = afat, parashkrim, dorëzim
- "HEARING" = seancë dëgjimore, dëshmi
- "COURT_DATE" = seancë gjyqësore, gjykatë
- "MEETING" = takim me klient, koleg, palë
- "FILING" = dorëzim parashtrese, padi, ankesë
- "CONSULTATION" = konsultë
- "PAYMENT" = pagesë, faturë
- "OTHER" = tjetër

PRIORITETI:
- "CRITICAL" = afat prekluziv, urgjent, sot/nesër
- "HIGH" = brenda 3 ditësh, i rëndësishëm
- "MEDIUM" = normal (default)
- "LOW" = i ulët, jo urgjent

RREGULLA:
1. Interpreto datat relative: "nesër" = +1 ditë, "pasnesër" = +2 ditë, "të hënën" = e hëna e ardhshme
2. Nëse nuk përmendet datë për event → përdor të nesërmen si default
3. Nëse është memo/notë pa datë → kategoria "FACT", data = sot
4. Titulli duhet të jetë i shkurtër (max 80 karaktere) dhe përmbledhës
5. Përgjigju VETËM me JSON të vlefshëm, pa shpjegime

FORMATI I PËRGJIGJES (JSON):
{{
  "category": "AGENDA" ose "FACT",
  "title": "string i shkurtër",
  "description": "string përshkrues",
  "event_type": "DEADLINE" | "HEARING" | "COURT_DATE" | "MEETING" | "FILING" | "CONSULTATION" | "PAYMENT" | "OTHER",
  "priority": "CRITICAL" | "HIGH" | "MEDIUM" | "LOW",
  "start_date": "YYYY-MM-DD",
  "location": "string ose bosh"
}}"""

        user_content = f"""TEKSTI I TRANSKRIPTUAR:
"{text}"

Nxirr të dhënat e strukturuara sipas formatit JSON të kërkuar. Përgjigju vetëm me JSON."""

        try:
            raw = _call_llm(
                system_prompt=system_prompt,
                user_content=user_content,
                json_mode=True,
                temperature=0.0
            )
            if not raw:
                logger.warning("⚠️ [Voice Parse] LLM returned empty")
                return {}

            parsed = clean_and_parse_json(raw)
            if not parsed:
                logger.warning(f"⚠️ [Voice Parse] Failed to parse JSON: {raw[:200]}")
                return {}

            valid_categories = {"AGENDA", "FACT"}
            valid_types = {"DEADLINE", "HEARING", "COURT_DATE", "MEETING", "FILING", "CONSULTATION", "PAYMENT", "OTHER"}
            valid_priorities = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}

            category = str(parsed.get("category", "AGENDA")).upper()
            if category not in valid_categories:
                category = "AGENDA"

            event_type = str(parsed.get("event_type", "MEETING")).upper()
            if event_type not in valid_types:
                event_type = "MEETING"

            priority = str(parsed.get("priority", "MEDIUM")).upper()
            if priority not in valid_priorities:
                priority = "MEDIUM"

            start_date_str = parsed.get("start_date")
            fallback_date = (now.date() + timedelta(days=1)) if category == "AGENDA" else now.date()
            try:
                parsed_date = date.fromisoformat(str(start_date_str))
                if parsed_date < now.date():
                    parsed_date = fallback_date
                start_date_final = parsed_date.isoformat()
            except Exception:
                start_date_final = fallback_date.isoformat()

            title = str(parsed.get("title", "")).strip()[:200]
            if not title:
                title = text.strip()[:80]

            description = str(parsed.get("description", "")).strip()[:1000]
            location = str(parsed.get("location", "")).strip()[:200]

            result = {
                "category": category,
                "title": title,
                "description": description,
                "event_type": event_type,
                "priority": priority,
                "start_date": start_date_final,
                "location": location,
            }

            logger.info(f"🎙️ [Voice Parse] '{text[:60]}...' → category={category} type={event_type} priority={priority} date={start_date_final}")
            return result

        except Exception as e:
            logger.error(f"❌ [Voice Parse] Exception: {e}")
            return {}


calendar_service = CalendarService()