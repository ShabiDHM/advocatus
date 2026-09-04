# FILE: backend/app/services/pillars/timeline_service.py
# PHOENIX PROTOCOL - TIMELINE & DEADLINE ENGINE V36.0 (TIMEZONE-SAFE UTC NORMALIZER & 7-DAY AKTVENDIM DEADLINES)

import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta, timezone
from bson import ObjectId

logger = logging.getLogger(__name__)

# ========== AFATET LIGJORE NË REPUBLIKËN E KOSOVËS ==========
DEADLINE_RULES = {
    "ANKIM_AKTVENDIM": {
        "days": 7,
        "description": "Afati prekluziv për ankesë kundër aktvendimit (7 ditë sipas LPK dhe Ligjit për Gjykatën Komerciale)"
    },
    "ANKIM_CIVIL_AKTGJYKIM": {
        "days": 15,
        "description": "Afati për ankesë kundër aktgjykimit civil (Neni 177 i LPK)"
    },
    "ANKIM_PENAL": {
        "days": 15,
        "description": "Afati për ankesë kundër aktgjykimit penal (Neni 380 i KPPRK)"
    },
    "PËRGJIGJE_NË_PADI": {
        "days": 30,
        "description": "Afati ligjor për dorëzimin e përgjigjes në padi (Prapësimi - Neni 398 i LPK)"
    },
    "KTHIM_NË_GJENDJE_TË_MËPARSHME": {
        "days": 15,
        "description": "Afati për propozim për kthim në gjendjen e mëparshme (Neni 130 i LPK)"
    }
}

# Harta e muajve në gjuhën shqipe
ALBANIAN_MONTHS = {
    "janar": 1, "shkurt": 2, "mars": 3, "prill": 4, "maj": 5, "qershor": 6,
    "korrik": 7, "gusht": 8, "shtator": 9, "tetor": 10, "nëntor": 11, "nentor": 11, "dhjetor": 12
}

DATE_PATTERNS = [
    r'\b(\d{1,2})[./\-](\d{1,2})[./\-](\d{2,4})\b',  # 31.08.2026, 31/08/2026
    r'\b(\d{4})-(\d{2})-(\d{2})\b',                   # 2026-08-31
]

DOCUMENT_TYPE_KEYWORDS = {
    "AKTVENDIM": ["aktvendim", "aktvendimi", "aktvendimit"],
    "AKTGJYKIM": ["aktgjykim", "aktgjykimi", "aktgjykimit", "në emër të popullit"],
    "ANKESË": ["ankesë", "ankese", "ankim", "apel", "drejtuar gjykatës së apelit"],
    "PADI": ["kërkesëpadi", "kerkesepadi", "padi", "paditësi"],
    "KUNDËRPADI": ["kundërpadi", "kunderpadi"],
    "KALLËZIM": ["kallëzim penal", "kallezim penal", "kallzim", "vepër penale", "aktakuzë"],
    "RAPORT": ["raport social", "qps", "ekspertizë", "ekspertize", "procesverbal"],
    "KONTRATË": ["marrëveshje", "marreveshje", "kontratë", "kontrate"],
}


def _ensure_utc(dt_val: Any) -> Optional[datetime]:
    """PHOENIX ZERO-CRASH: Normalizon çdo datë në UTC tz-aware për të shmangur përplasjet offset-naive vs aware."""
    if not dt_val:
        return None
    if isinstance(dt_val, str):
        try:
            dt_clean = dt_val.replace('Z', '+00:00')
            dt_val = datetime.fromisoformat(dt_clean)
        except Exception:
            return None
    if isinstance(dt_val, datetime):
        if dt_val.tzinfo is None:
            return dt_val.replace(tzinfo=timezone.utc)
        return dt_val.astimezone(timezone.utc)
    return None


class TimelineService:
    """
    Shërbimi i Kronologjisë dhe Menaxhimit të Afateve Ligjore (V36.0):
    - Normalizon 100% të gjitha datat në UTC pa gabime offset-naive.
    - Përllogarit saktë afatet procedurale sipas ligjeve të Kosovës.
    """

    @staticmethod
    def extract_dates_from_text(text: str) -> List[datetime]:
        dates = []
        if not text:
            return dates

        # 1. Datat numerike (31.08.2026)
        for pattern in DATE_PATTERNS:
            matches = re.findall(pattern, text)
            for match in matches:
                try:
                    if len(match) == 3:
                        part1, part2, part3 = match
                        if len(str(part1)) == 4:
                            year, month, day = int(part1), int(part2), int(part3)
                        else:
                            day, month, year = int(part1), int(part2), int(part3)

                        if year < 100:
                            year += 2000 if year < 50 else 1900
                        
                        if 1 <= day <= 31 and 1 <= month <= 12 and 1990 <= year <= 2035:
                            dt = datetime(year, month, day, tzinfo=timezone.utc)
                            dates.append(dt)
                except (ValueError, TypeError):
                    continue

        # 2. Datat me tekst shqip (p.sh. "31 gusht 2026", "15 korrik 2026")
        months_regex = "|".join(ALBANIAN_MONTHS.keys())
        text_date_pattern = rf'\b(\d{{1,2}})\s+({months_regex})\s+(\d{{4}})\b'
        text_matches = re.findall(text_date_pattern, text, flags=re.IGNORECASE)
        
        for day_str, month_name, year_str in text_matches:
            try:
                day = int(day_str)
                month = ALBANIAN_MONTHS.get(month_name.lower())
                year = int(year_str)
                if month and 1 <= day <= 31 and 1990 <= year <= 2035:
                    dt = datetime(year, month, day, tzinfo=timezone.utc)
                    dates.append(dt)
            except (ValueError, TypeError):
                continue

        return sorted(set(dates))

    @staticmethod
    def detect_document_type(filename: str, content: str = "") -> str:
        combined = f"{filename} {content[:2500]}".lower()
        for doc_type, keywords in DOCUMENT_TYPE_KEYWORDS.items():
            for kw in keywords:
                if kw in combined:
                    return doc_type
        return "DOKUMENT"

    @staticmethod
    def build_case_timeline(
        db: Any,
        case_id: str,
        user_id: str = ""
    ) -> Dict[str, Any]:
        timeline = []
        key_dates = []
        
        try:
            case_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
            
            doc_filter = {
                "$or": [{"case_id": case_id}, {"case_id": case_oid}],
                "status": {"$ne": "DELETED"}
            }
            if user_id:
                user_oid = ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id
                doc_filter["owner_id"] = {"$in": [user_id, user_oid]}

            documents = list(db.documents.find(doc_filter))
            
            media_filter = {
                "$or": [{"case_id": case_id}, {"case_id": case_oid}]
            }
            if user_id:
                user_oid = ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id
                media_filter["owner_id"] = {"$in": [user_id, user_oid]}

            media_items = list(db.media_evidence.find(media_filter))
            
            # Përpunimi i dokumenteve
            for doc in documents:
                file_name = doc.get("file_name", "Dokument")
                full_text = doc.get("content") or doc.get("extracted_text") or doc.get("summary") or ""
                created_at = doc.get("created_at")
                
                dates = TimelineService.extract_dates_from_text(full_text)
                doc_type = TimelineService.detect_document_type(file_name, full_text[:3000])
                
                if dates:
                    for dt in dates:
                        dt_utc = _ensure_utc(dt)
                        if dt_utc:
                            timeline.append({
                                "date": dt_utc.strftime("%d.%m.%Y"),
                                "date_obj": dt_utc,
                                "document": file_name,
                                "type": doc_type,
                                "source": "document_text"
                            })
                            if dt_utc not in key_dates:
                                key_dates.append(dt_utc)
                elif created_at:
                    created_dt = _ensure_utc(created_at)
                    if created_dt:
                        timeline.append({
                            "date": created_dt.strftime("%d.%m.%Y"),
                            "date_obj": created_dt,
                            "document": file_name,
                            "type": doc_type,
                            "source": "system_date"
                        })
                        if created_dt not in key_dates:
                            key_dates.append(created_dt)
            
            # Përpunimi i provave audio/video
            for media in media_items:
                file_name = media.get("file_name", "Media")
                created_at = media.get("created_at")
                if created_at:
                    created_dt = _ensure_utc(created_at)
                    if created_dt:
                        timeline.append({
                            "date": created_dt.strftime("%d.%m.%Y"),
                            "date_obj": created_dt,
                            "document": f"Media: {file_name}",
                            "type": "PROVË AUDIO/VIDEO",
                            "source": "media_date"
                        })
                        if created_dt not in key_dates:
                            key_dates.append(created_dt)
            
            # Renditje e sigurt: të gjitha objektet janë të garantuara UTC
            timeline.sort(key=lambda x: x["date_obj"])
            key_dates.sort()
            
            deadlines = TimelineService.calculate_deadlines(timeline)
            expired_deadlines = [d for d in deadlines if d.get("is_expired", False)]
            open_deadlines = [d for d in deadlines if not d.get("is_expired", False)]
            recommended_actions = TimelineService.recommend_actions(expired_deadlines, open_deadlines, timeline)
            
            return {
                "timeline": timeline,
                "key_dates": [d.strftime("%d.%m.%Y") for d in key_dates],
                "deadlines": deadlines,
                "expired_deadlines": expired_deadlines,
                "open_deadlines": open_deadlines,
                "recommended_actions": recommended_actions,
                "total_documents": len(documents),
                "total_media": len(media_items)
            }
            
        except Exception as e:
            logger.error(f"❌ [Timeline] Gabim gjatë ndërtimit të kronologjisë: {e}")
            return {
                "timeline": [],
                "key_dates": [],
                "deadlines": [],
                "expired_deadlines": [],
                "open_deadlines": [],
                "recommended_actions": ["Kronologjia po rindërtohet nga fashikulli."],
                "total_documents": 0,
                "total_media": 0
            }

    @staticmethod
    def calculate_deadlines(timeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        deadlines = []
        now = datetime.now(timezone.utc)
        
        for item in timeline:
            doc_type = item.get("type", "DOKUMENT")
            date_obj = item.get("date_obj")
            
            if not date_obj:
                continue
            
            if doc_type == "AKTVENDIM":
                deadline_days = DEADLINE_RULES["ANKIM_AKTVENDIM"]["days"]
                deadline_date = date_obj + timedelta(days=deadline_days)
                is_expired = deadline_date < now
                
                deadlines.append({
                    "document": item.get("document", "Aktvendim Gjyqësor"),
                    "date": item.get("date", ""),
                    "deadline_days": deadline_days,
                    "deadline_date": deadline_date.strftime("%d.%m.%Y"),
                    "is_expired": is_expired,
                    "description": DEADLINE_RULES["ANKIM_AKTVENDIM"]["description"],
                    "action_required": "Dorëzo Ankesë brenda afatit ligjor prej 7 ditësh" if not is_expired else "Afati i rregullt 7-ditor ka skaduar — shqyrto Kthimin në Gjendje të Mëparshme"
                })

            elif doc_type == "AKTGJYKIM":
                deadline_days = DEADLINE_RULES["ANKIM_CIVIL_AKTGJYKIM"]["days"]
                deadline_date = date_obj + timedelta(days=deadline_days)
                is_expired = deadline_date < now
                
                deadlines.append({
                    "document": item.get("document", "Aktgjykim Gjyqësor"),
                    "date": item.get("date", ""),
                    "deadline_days": deadline_days,
                    "deadline_date": deadline_date.strftime("%d.%m.%Y"),
                    "is_expired": is_expired,
                    "description": DEADLINE_RULES["ANKIM_CIVIL_AKTGJYKIM"]["description"],
                    "action_required": "Dorëzo Ankesë në Gjykatën e Apelit (15 ditë)" if not is_expired else "Afati i rregullt ka skaduar — shqyrto Mjetet e Jashtëzakonshme"
                })
            
            elif doc_type in ["PADI"]:
                deadline_days = DEADLINE_RULES["PËRGJIGJE_NË_PADI"]["days"]
                deadline_date = date_obj + timedelta(days=deadline_days)
                is_expired = deadline_date < now
                
                deadlines.append({
                    "document": item.get("document", "Padi"),
                    "date": item.get("date", ""),
                    "deadline_days": deadline_days,
                    "deadline_date": deadline_date.strftime("%d.%m.%Y"),
                    "is_expired": is_expired,
                    "description": DEADLINE_RULES["PËRGJIGJE_NË_PADI"]["description"],
                    "action_required": "Dorëzo Përgjigje në Padi (Prapësim brenda 30 ditësh)" if not is_expired else "Afati i prapësimit ka kaluar — përgatit prapësimin për në Seancë Përgatitore"
                })
        
        return deadlines

    @staticmethod
    def recommend_actions(
        expired_deadlines: List[Dict[str, Any]],
        open_deadlines: List[Dict[str, Any]],
        timeline: List[Dict[str, Any]]
    ) -> List[str]:
        actions = []
        for od in open_deadlines:
            actions.append(f"AFAT AKTIV ({od.get('deadline_days')} ditë): {od.get('action_required')} deri më {od.get('deadline_date')}.")
        
        if expired_deadlines:
            actions.append("KTHIM NË GJENDJEN E MËPARSHME: Nëse ka pasur pengesa të arsyeshme objektive, kërkohet kthimi në afat (Neni 129 LPK).")
        
        if not actions:
            actions.append("Ndiq rrjedhën e rregullt procedurale sipas ligjit.")
            
        return actions

    @staticmethod
    def build_timeline_prompt(timeline_data: Dict[str, Any]) -> str:
        if not timeline_data or not timeline_data.get("timeline"):
            return ""
        
        lines = []
        lines.append("=" * 60)
        lines.append("📅 KRONOLOGJIA E SAKTË DHE AFATET LIGJORE TË FASHIKULLIT:")
        lines.append("=" * 60)
        
        for item in timeline_data.get("timeline", []):
            date_str = item.get("date", "")
            doc = item.get("document", "Dokument")
            doc_type = item.get("type", "DOKUMENT")
            lines.append(f"   📌 {date_str} — [{doc_type}] {doc}")
        
        if timeline_data.get("open_deadlines"):
            lines.append("")
            lines.append("🟢 AFATET PROCEDURALE TË HAPURA:")
            for d in timeline_data.get("open_deadlines", []):
                lines.append(f"   ⏳ {d.get('document', '')} — Afati: {d.get('deadline_date', '')} ➔ {d.get('action_required', '')}")

        if timeline_data.get("expired_deadlines"):
            lines.append("")
            lines.append("🔴 AFATET E SKADUARA DHE REMEDIIMI:")
            for d in timeline_data.get("expired_deadlines", []):
                lines.append(f"   ⚠️ {d.get('document', '')} — Skaduar më: {d.get('deadline_date', '')} ➔ {d.get('action_required', '')}")
        
        lines.append("=" * 60)
        return "\n".join(lines)


# Singleton
timeline_service = TimelineService()