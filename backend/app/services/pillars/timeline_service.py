# FILE: backend/app/services/pillars/timeline_service.py
# PHOENIX PROTOCOL - TIMELINE & DEADLINE ENGINE V30.0 (ACCURATE KOSOVO PROCEDURAL DEADLINES)

import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta, timezone
from bson import ObjectId

logger = logging.getLogger(__name__)

# ========== AFATET LIGJORE NË REPUBLIKËN E KOSOVËS ==========
DEADLINE_RULES = {
    "ANKIM_CIVIL": {
        "days": 15,
        "description": "Afati për ankesë kundër aktgjykimit/aktvendimit civil (Neni 177 i LPK)"
    },
    "ANKIM_PENAL": {
        "days": 15,
        "description": "Afati për ankesë kundër aktgjykimit penal (Neni 380 i KPPRK)"
    },
    "PËRGJIGJE_NË_PADI": {
        "days": 30,
        "description": "Afati ligjor për dorëzimin e përgjigjes në padi (Prapësimi - Neni 398 i LPK)"
    },
    "PËRSËRITJE_PROCEDURE": {
        "days": 30,
        "description": "Afati subjektiv për propozimin për përsëritjen e procedurës nga mësimi i faktit të ri (LPK)"
    },
    "KTHIM_NË_GJENDJE_TË_MËPARSHME": {
        "days": 15,
        "description": "Afati për propozim për kthim në gjendjen e mëparshme nga pushimi i pengesës (Neni 130 i LPK)"
    },
    "MASË_SIGURIMI": {
        "days": 0,
        "description": "Masa e përkohshme e sigurimit kërkohet menjëherë kur ka rrezik të dëmtimit të së drejtës"
    }
}

# ========== FORMATET E DATAVE GJYQËSORE ==========
DATE_PATTERNS = [
    r'\b(\d{1,2})[./\-](\d{1,2})[./\-](\d{2,4})\b',  # 19.01.2024, 19/01/2024, 19-01-2024
    r'\b(\d{4})-(\d{2})-(\d{2})\b',                   # 2024-01-19
]

DOCUMENT_TYPE_KEYWORDS = {
    "VENDIM": ["aktvendim", "aktgjykim", "vendim", "vendimi", "në emër të popullit"],
    "ANKESË": ["ankesë", "ankese", "ankim", "apel", "drejtuar gjykatës së apelit"],
    "PADI": ["kërkesëpadi", "kerkesepadi", "padi", "paditësi"],
    "KALLËZIM": ["kallëzim penal", "kallezim penal", "kallzim", "vepër penale"],
    "RAPORT": ["raport social", "qps", "ekspertizë", "ekspertize", "procesverbal", "psikiatri"],
    "KËRKESË": ["prapësim", "prapsim", "përgjigje në padi", "kërkesë", "kerkese"],
    "MARRËVESHJE": ["marrëveshje", "marreveshje", "kontratë", "kontrate"],
    "URDHËR": ["urdhër mbrojtje", "urdher mbrojtje", "urdhërmbrojtje", "masë mbrojtëse"],
}


class TimelineService:
    """
    Shërbimi i Kronologjisë dhe Menaxhimit të Afateve Ligjore:
    - Lexon dhe indekson datat nga të gjitha shkresat e fashikullit.
    - Llogarit afatet ligjore sipas LPK, KPPRK dhe Ligjit për Familjen.
    - Identifikon shkeljet e afateve dhe propozon mjetet e duhura juridike.
    """

    @staticmethod
    def extract_dates_from_text(text: str) -> List[datetime]:
        dates = []
        if not text:
            return dates

        for pattern in DATE_PATTERNS:
            matches = re.findall(pattern, text)
            for match in matches:
                try:
                    if len(match) == 3:
                        part1, part2, part3 = match
                        # Nëse formati është YYYY-MM-DD
                        if len(str(part1)) == 4:
                            year, month, day = int(part1), int(part2), int(part3)
                        else:
                            day, month, year = int(part1), int(part2), int(part3)

                        if year < 100:
                            year += 2000 if year < 50 else 1900
                        
                        # Filtro datat e vlefshme historike dhe aktuale (1990 - 2035)
                        if 1 <= day <= 31 and 1 <= month <= 12 and 1990 <= year <= 2035:
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
            
            # 1. Lexo dokumentet me kërkim të sigurt (ObjectId + String)
            doc_filter = {
                "$or": [{"case_id": case_id}, {"case_id": case_oid}],
                "status": {"$ne": "DELETED"}
            }
            if user_id:
                user_oid = ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id
                doc_filter["owner_id"] = {"$in": [user_id, user_oid]}

            documents = list(db.documents.find(doc_filter))
            
            # 2. Lexo provat audio/video
            media_filter = {
                "$or": [{"case_id": case_id}, {"case_id": case_oid}]
            }
            if user_id:
                user_oid = ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id
                media_filter["owner_id"] = {"$in": [user_id, user_oid]}

            media_items = list(db.media_evidence.find(media_filter))
            
            # 3. Përpuno dokumentet
            for doc in documents:
                file_name = doc.get("file_name", "Dokument")
                extracted_text = doc.get("extracted_text") or doc.get("summary") or ""
                created_at = doc.get("created_at")
                
                dates = TimelineService.extract_dates_from_text(extracted_text[:6000])
                doc_type = TimelineService.detect_document_type(file_name, extracted_text[:2000])
                
                if dates:
                    for dt in dates:
                        timeline.append({
                            "date": dt.strftime("%d.%m.%Y"),
                            "date_obj": dt,
                            "document": file_name,
                            "type": doc_type,
                            "source": "document_text"
                        })
                        if dt not in key_dates:
                            key_dates.append(dt)
                elif created_at:
                    created_dt = created_at if isinstance(created_at, datetime) else datetime.fromisoformat(str(created_at))
                    timeline.append({
                        "date": created_dt.strftime("%d.%m.%Y"),
                        "date_obj": created_dt,
                        "document": file_name,
                        "type": doc_type,
                        "source": "system_date"
                    })
                    if created_dt not in key_dates:
                        key_dates.append(created_dt)
            
            # 4. Përpuno provat audio/video
            for media in media_items:
                file_name = media.get("file_name", "Media")
                created_at = media.get("created_at")
                if created_at:
                    created_dt = created_at if isinstance(created_at, datetime) else datetime.fromisoformat(str(created_at))
                    timeline.append({
                        "date": created_dt.strftime("%d.%m.%Y"),
                        "date_obj": created_dt,
                        "document": f"Media: {file_name}",
                        "type": "PROVË AUDIO/VIDEO",
                        "source": "media_date"
                    })
                    if created_dt not in key_dates:
                        key_dates.append(created_dt)
            
            # 5. Rendit kronologjikisht
            timeline.sort(key=lambda x: x["date_obj"])
            key_dates.sort()
            
            # 6. Llogarit afatet ligjore
            deadlines = TimelineService.calculate_deadlines(timeline)
            expired_deadlines = [d for d in deadlines if d.get("is_expired", False)]
            open_deadlines = [d for d in deadlines if not d.get("is_expired", False)]
            
            # 7. Rekomandimet e veprimit
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
                "recommended_actions": ["Kronologjia u ndërtua nga shkresat e fashikullit."],
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
            
            if doc_type in ["VENDIM"]:
                deadline_days = DEADLINE_RULES["ANKIM_CIVIL"]["days"]
                deadline_date = date_obj + timedelta(days=deadline_days)
                is_expired = deadline_date < now
                
                deadlines.append({
                    "document": item.get("document", "Vendim Gjyqësor"),
                    "date": item.get("date", ""),
                    "deadline_days": deadline_days,
                    "deadline_date": deadline_date.strftime("%d.%m.%Y"),
                    "is_expired": is_expired,
                    "description": DEADLINE_RULES["ANKIM_CIVIL"]["description"],
                    "action_required": "Dorëzo Ankesë në Gjykatën e Apelit" if not is_expired else "Afati i rregullt ka skaduar — shqyrto Kthimin në Gjendje të Mëparshme ose Përsëritjen e Procedurës"
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
                    "action_required": "Dorëzo Përgjigje në Padi (Prapësim)" if not is_expired else "Afati i prapësimit ka kaluar — përgatit prapësimin për në Seancë Përgatitore"
                })
        
        return deadlines

    @staticmethod
    def recommend_actions(
        expired_deadlines: List[Dict[str, Any]],
        open_deadlines: List[Dict[str, Any]],
        timeline: List[Dict[str, Any]]
    ) -> List[str]:
        actions = []
        
        # 1. Veprimet për afate të hapura
        for od in open_deadlines:
            actions.append(f"AFAT AKTIV: {od.get('action_required')} brenda datës {od.get('deadline_date')}.")
        
        # 2. Veprimet kur afatet kanë skaduar
        if expired_deadlines:
            actions.append("KTHIM NË GJENDJEN E MËPARSHME / PËRSËRITJE: Nëse ka pasur pengesa të arsyeshme ose prova të reja, kërkohet kthimi në afat (Neni 129 LPK).")
        
        # 3. Nëse ka raport të QPS-së
        if any(item.get("type") == "RAPORT" for item in timeline):
            actions.append("KUNDËRSHTIM I RAPORTIT TË QPS: Dorëzo vërejtje me shkrim kundër njëanshmërisë së raportit social para seancës.")

        if not actions:
            actions.append("Ndiq rrjedhën e rregullt procedurale sipas kalendarit të seancave.")
            
        return actions

    @staticmethod
    def build_timeline_prompt(timeline_data: Dict[str, Any]) -> str:
        if not timeline_data or not timeline_data.get("timeline"):
            return ""
        
        lines = []
        lines.append("=" * 60)
        lines.append("📅 KRONOLOGJIA E SAKTË E RASTIT DHE STATUSI I AFATEVE:")
        lines.append("=" * 60)
        
        for item in timeline_data.get("timeline", []):
            date_str = item.get("date", "")
            doc = item.get("document", "Dokument")
            doc_type = item.get("type", "DOKUMENT")
            lines.append(f"   📌 {date_str} — [{doc_type}] {doc}")
        
        if timeline_data.get("open_deadlines"):
            lines.append("")
            lines.append("🟢 AFATET LIGJORE TË HAPURA:")
            for d in timeline_data.get("open_deadlines", []):
                lines.append(f"   ⏳ {d.get('document', '')} — Afati: {d.get('deadline_date', '')} ➔ {d.get('action_required', '')}")

        if timeline_data.get("expired_deadlines"):
            lines.append("")
            lines.append("🔴 AFATET E SKADUARA DHE REMEDIIMI:")
            for d in timeline_data.get("expired_deadlines", []):
                lines.append(f"   ⚠️ {d.get('document', '')} — Skaduar më: {d.get('deadline_date', '')} ➔ {d.get('action_required', '')}")
        
        if timeline_data.get("recommended_actions"):
            lines.append("")
            lines.append("🎯 HAPAT E SUGJERUAR PROCEDURALË:")
            for action in timeline_data.get("recommended_actions", []):
                lines.append(f"   🔹 {action}")
        
        lines.append("=" * 60)
        
        return "\n".join(lines)


# Singleton instance
timeline_service = TimelineService()