# FILE: backend/app/services/pillars/timeline_service.py
# PHOENIX PROTOCOL - TIMELINE SERVICE V1.0 (CHRONOLOGY & DEADLINE ENGINE)

import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta, timezone
from bson import ObjectId

logger = logging.getLogger(__name__)

# ========== AFATET LIGJORE NË KOSOVË ==========
DEADLINE_RULES = {
    "ANKIM_CIVIL": {
        "days": 15,
        "description": "Afati për ankim kundër aktvendimit/aktgjykimit civil (LPK)"
    },
    "ANKIM_PENAL": {
        "days": 15,
        "description": "Afati për ankim kundër aktgjykimit penal (KPPRK)"
    },
    "KALLËZIM_PENAL": {
        "days": None,  # Nuk ka afat të parashkrimit për vepra të rënda
        "description": "Kallëzimi penal mund të parashtrohet sa herë që zbulohen elemente të veprës penale"
    },
    "KËRKESË_PËR_RISHQYRTIM": {
        "days": 30,
        "description": "Afati për kërkesë për rishqyrtim (LPK)"
    },
    "PADI_CIVILE": {
        "days": None,  # Afati i parashkrimit varet nga lloji i kërkesës
        "description": "Padia civile ka afate parashkrimi sipas LMD-së"
    },
    "MASË_EMERGJENTE": {
        "days": 0,  # Menjëherë
        "description": "Masa emergjente kërkohet menjëherë kur ka rrezik"
    }
}

# ========== LLOJET E DOKUMENTEVE DHE DATAT ==========
DATE_PATTERNS = [
    r'(\d{1,2})[./](\d{1,2})[./](\d{2,4})',  # 19.01.2024, 19/01/2024
    r'(\d{4})-(\d{2})-(\d{2})',                 # 2024-01-19
]

DOCUMENT_TYPE_KEYWORDS = {
    "VENDIM": ["aktvendim", "aktgjykim", "vendim", "vendimin"],
    "ANKESË": ["ankesë", "ankese", "ankim", "apel"],
    "KALLËZIM": ["kallëzim", "kallezim", "kallzim"],
    "RAPORT": ["raport", "ekspertizë", "ekspertize", "procesverbal"],
    "KËRKESË": ["kërkesë", "kerkese", "kërkesën", "kerkesen"],
    "MARRËVESHJE": ["marrëveshje", "marreveshje", "marrëveshjen"],
    "URDHËR": ["urdhër", "urdher", "urdhërmbrojtje", "urdhermbrojtje"],
}

class TimelineService:
    """
    Shërbimi i Kronologjisë së Rastit:
    - Lexon të gjitha dokumentet nga fashikulli
    - Nxjerr datat nga çdo dokument
    - Ndërton kronologjinë e saktë të ngjarjeve
    - Identifikon afatet ligjore
    - Dallon se cilat afate kanë skaduar dhe cilat janë të hapura
    - Rekomandon opsionet procedurale të mbetura
    """

    @staticmethod
    def extract_dates_from_text(text: str) -> List[datetime]:
        """Nxjerr të gjitha datat nga një tekst."""
        dates = []
        for pattern in DATE_PATTERNS:
            matches = re.findall(pattern, text)
            for match in matches:
                try:
                    if len(match) == 3:
                        day, month, year = match
                        day = int(day)
                        month = int(month)
                        year = int(year)
                        if year < 100:
                            year += 2000 if year < 50 else 1900
                        if 1 <= day <= 31 and 1 <= month <= 12:
                            dt = datetime(year, month, day, tzinfo=timezone.utc)
                            dates.append(dt)
                except (ValueError, TypeError):
                    continue
        return sorted(set(dates))

    @staticmethod
    def detect_document_type(filename: str, content: str = "") -> str:
        """Zbulon llojin e dokumentit nga emri i skedarit dhe përmbajtja."""
        combined = f"{filename} {content[:2000]}".lower()
        
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
        """
        Ndërton kronologjinë e plotë të rastit nga dokumentet e fashikullit.
        
        Returns:
        {
            "timeline": [
                {"date": "19.01.2024", "document": "Aktvendim C.nr.385/24", "type": "VENDIM"},
                ...
            ],
            "key_dates": [...],
            "deadlines": [...],
            "expired_deadlines": [...],
            "open_deadlines": [...],
            "recommended_actions": [...]
        }
        """
        timeline = []
        key_dates = []
        
        try:
            # 1. Lexo të gjitha dokumentet e çështjes
            documents = []
            if user_id:
                documents = list(db.documents.find({"case_id": case_id, "owner_id": user_id}))
            else:
                case_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
                documents = list(db.documents.find({"case_id": case_id}))
            
            # 2. Lexo media evidence
            media_items = []
            if user_id:
                media_items = list(db.media_evidence.find({"case_id": case_id, "owner_id": user_id}))
            else:
                media_items = list(db.media_evidence.find({"case_id": case_id}))
            
            # 3. Ndërto timeline nga dokumentet
            for doc in documents:
                file_name = doc.get("file_name", "Dokument")
                extracted_text = doc.get("extracted_text") or doc.get("summary") or ""
                created_at = doc.get("created_at")
                
                # Nxjerr datat nga teksti
                dates = TimelineService.extract_dates_from_text(extracted_text[:5000])
                
                doc_type = TimelineService.detect_document_type(file_name, extracted_text[:2000])
                
                if dates:
                    for dt in dates:
                        timeline.append({
                            "date": dt.strftime("%d.%m.%Y"),
                            "date_obj": dt,
                            "document": file_name,
                            "type": doc_type,
                            "source": "document"
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
                        "source": "created_at"
                    })
                    if created_dt not in key_dates:
                        key_dates.append(created_dt)
            
            # 4. Ndërto timeline nga media evidence
            for media in media_items:
                file_name = media.get("file_name", "Media")
                transcript = media.get("transcript", "")
                created_at = media.get("created_at")
                
                dates = TimelineService.extract_dates_from_text(transcript[:2000])
                if created_at:
                    created_dt = created_at if isinstance(created_at, datetime) else datetime.fromisoformat(str(created_at))
                    timeline.append({
                        "date": created_dt.strftime("%d.%m.%Y"),
                        "date_obj": created_dt,
                        "document": f"Media: {file_name}",
                        "type": "MEDIA",
                        "source": "media_created"
                    })
                    if created_dt not in key_dates:
                        key_dates.append(created_dt)
            
            # 5. Sorto timeline sipas datës
            timeline.sort(key=lambda x: x["date_obj"])
            key_dates.sort()
            
            # 6. Ndërto listën e afateve
            deadlines = TimelineService.calculate_deadlines(timeline)
            
            # 7. Ndaj afatet e skaduara nga ato të hapura
            expired_deadlines = [d for d in deadlines if d.get("is_expired", False)]
            open_deadlines = [d for d in deadlines if not d.get("is_expired", False)]
            
            # 8. Rekomando veprime
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
                "recommended_actions": ["Nuk u mundësua ndërtimi i kronologjisë së rastit."],
                "total_documents": 0,
                "total_media": 0
            }

    @staticmethod
    def calculate_deadlines(timeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Llogarit afatet ligjore për çdo lloj dokumenti."""
        deadlines = []
        now = datetime.now(timezone.utc)
        
        for item in timeline:
            doc_type = item.get("type", "DOKUMENT")
            date_obj = item.get("date_obj")
            
            if not date_obj:
                continue
            
            # Përcakto afatin sipas llojit të dokumentit
            if doc_type in ["VENDIM"]:
                deadline_days = DEADLINE_RULES["ANKIM_CIVIL"]["days"]
                deadline_date = date_obj + timedelta(days=deadline_days)
                is_expired = deadline_date < now
                
                deadlines.append({
                    "document": item.get("document", "Dokument"),
                    "date": item.get("date", ""),
                    "deadline_days": deadline_days,
                    "deadline_date": deadline_date.strftime("%d.%m.%Y"),
                    "is_expired": is_expired,
                    "description": DEADLINE_RULES["ANKIM_CIVIL"]["description"],
                    "action_required": "Ankim" if not is_expired else "Ankimi ka skaduar — konsidero Kallëzim Penal ose Kërkesë për Rishqyrtim"
                })
            
            elif doc_type in ["ANKESË"]:
                deadline_days = DEADLINE_RULES["ANKIM_CIVIL"]["days"]
                deadline_date = date_obj + timedelta(days=deadline_days)
                is_expired = deadline_date < now
                
                deadlines.append({
                    "document": item.get("document", "Dokument"),
                    "date": item.get("date", ""),
                    "deadline_days": deadline_days,
                    "deadline_date": deadline_date.strftime("%d.%m.%Y"),
                    "is_expired": is_expired,
                    "description": "Afati për përgjigje në ankesë",
                    "action_required": "Përgjigje në ankesë" if not is_expired else "Ankesa ka skaduar"
                })
            
            elif doc_type in ["KALLËZIM"]:
                deadlines.append({
                    "document": item.get("document", "Dokument"),
                    "date": item.get("date", ""),
                    "deadline_days": None,
                    "deadline_date": "Pa afat (varësisht nga vepra penale)",
                    "is_expired": False,
                    "description": DEADLINE_RULES["KALLËZIM_PENAL"]["description"],
                    "action_required": "Kallëzimi penal është gjithmonë i hapur për vepra të rënda"
                })
            
            elif doc_type in ["URDHËR"]:
                deadlines.append({
                    "document": item.get("document", "Dokument"),
                    "date": item.get("date", ""),
                    "deadline_days": 0,
                    "deadline_date": "Menjëherë",
                    "is_expired": False,
                    "description": "Urdhërmbrojtja kërkon veprim të menjëhershëm",
                    "action_required": "Veprim i menjëhershëm për mbrojtje"
                })
        
        return deadlines

    @staticmethod
    def recommend_actions(
        expired_deadlines: List[Dict[str, Any]],
        open_deadlines: List[Dict[str, Any]],
        timeline: List[Dict[str, Any]]
    ) -> List[str]:
        """Rekomandon veprimet procedurale të mbetura."""
        actions = []
        
        # 1. Nëse ka afate të skaduara për ankim
        if any("Ankimi ka skaduar" in d.get("action_required", "") for d in expired_deadlines):
            actions.append("KALLËZIM PENAL: Afatet e ankimit kanë skaduar — parashtroni Kallëzim Penal në PSRK për shkeljet e identifikuara.")
            actions.append("KËRKESË PËR RISHQYRTIM: Nëse ka rrethana të reja, kërkoni rishqyrtim të vendimeve.")
        
        # 2. Nëse ka dokumente të tipit "URDHËR"
        if any(item.get("type") == "URDHËR" for item in timeline):
            actions.append("MASË EMERGJENTE: Kërkoni menjëherë masë mbrojtëse për fëmijën.")
        
        # 3. Nëse ka media evidence
        if any(item.get("type") == "MEDIA" for item in timeline):
            actions.append("PROVË MATERIALE: Transkriptet audio/video janë prova të forta — përfshijini në kallëzim.")
        
        # 4. Nëse ka raporte mjekësore
        if any(item.get("type") == "RAPORT" for item in timeline):
            actions.append("EKSPERTIZË E PAVARUR: Kërkoni ekspertizë të re nga institucion i pavarur.")
        
        # 5. Nëse nuk ka asnjë veprim specifik
        if not actions:
            actions.append("Analizoni dokumentet dhe identifikoni shkeljet për kallëzim penal.")
        
        return actions

    @staticmethod
    def build_timeline_prompt(timeline_data: Dict[str, Any]) -> str:
        """Ndërton pjesën e prompt-it që përmban kronologjinë e rastit."""
        if not timeline_data or not timeline_data.get("timeline"):
            return ""
        
        lines = []
        lines.append("=" * 60)
        lines.append("📅 KRONOLOGJIA E SAKTË E RASTIT (nga dokumentet e fashikullit):")
        lines.append("=" * 60)
        
        for item in timeline_data.get("timeline", []):
            date_str = item.get("date", "")
            doc = item.get("document", "Dokument")
            doc_type = item.get("type", "DOKUMENT")
            lines.append(f"   📌 {date_str} — [{doc_type}] {doc}")
        
        if timeline_data.get("expired_deadlines"):
            lines.append("")
            lines.append("⚠️ AFATET E SKADUARA:")
            for d in timeline_data.get("expired_deadlines", []):
                lines.append(f"   ❌ {d.get('document', '')} — Afati: {d.get('deadline_date', '')} — {d.get('action_required', '')}")
        
        if timeline_data.get("open_deadlines"):
            lines.append("")
            lines.append("✅ AFATET E HAPURA:")
            for d in timeline_data.get("open_deadlines", []):
                lines.append(f"   ✅ {d.get('document', '')} — Afati: {d.get('deadline_date', '')} — {d.get('action_required', '')}")
        
        if timeline_data.get("recommended_actions"):
            lines.append("")
            lines.append("🎯 VEPRIMET E REKOMANDUARA PROCEDURALE:")
            for action in timeline_data.get("recommended_actions", []):
                lines.append(f"   🔹 {action}")
        
        lines.append("=" * 60)
        
        return "\n".join(lines)


# Singleton instance for easy import
timeline_service = TimelineService()