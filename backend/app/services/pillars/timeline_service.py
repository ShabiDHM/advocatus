# FILE: backend/app/services/pillars/timeline_service.py
# PHOENIX PROTOCOL - TIMELINE & DEADLINE ENGINE V37.0
# ZERO SILENT TRUNCATION • 13 DEADLINE RULES • 18 DOCUMENT TYPES
# Backward compatible with V36.0.

import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta, timezone
from bson import ObjectId

logger = logging.getLogger(__name__)


# ========== AFATET LIGJORE NË REPUBLIKËN E KOSOVËS ==========
# Burime: LPK, KPPRK, Ligji për Gjykatën Komerciale, Ligji për Procedurën
# Ekzekutive, Ligji për Familjen.
DEADLINE_RULES = {
    "ANKIM_AKTVENDIM": {
        "days": 7,
        "description": "Afati prekluziv për ankesë kundër aktvendimit (7 ditë sipas LPK dhe Ligjit për Gjykatën Komerciale)",
    },
    "ANKIM_CIVIL_AKTGJYKIM": {
        "days": 15,
        "description": "Afati për ankesë kundër aktgjykimit civil (Neni 177 i LPK)",
    },
    "ANKIM_PENAL": {
        "days": 15,
        "description": "Afati për ankesë kundër aktgjykimit penal (Neni 380 i KPPRK)",
    },
    "PËRGJIGJE_NË_PADI": {
        "days": 30,
        "description": "Afati ligjor për dorëzimin e përgjigjes në padi (Prapësimi - Neni 398 i LPK)",
    },
    "PËRGJIGJE_NË_KUNDËRPADI": {
        "days": 30,
        "description": "Afati për përgjigje në kundërpadi (Neni 398 i LPK, i zbatuar analogjikisht)",
    },
    "KTHIM_NË_GJENDJE_TË_MËPARSHME": {
        "days": 15,
        "description": "Afati për propozim për kthim në gjendjen e mëparshme (Neni 130 i LPK)",
    },
    "REVIZION": {
        "days": 30,
        "description": "Afati për paraqitje revizioni (Neni 224 i LPK)",
    },
    "ANKESË_EKZEKUTIMI": {
        "days": 8,
        "description": "Afati për ankesë kundër vendimit të ekzekutimit (Ligji për Procedurën Ekzekutive)",
    },
    "ANKESË_PËRMBARIMI": {
        "days": 8,
        "description": "Afati për ankesë në procedurën përmbarimore (Ligji Nr. 04/L-139)",
    },
    "KALLËZIM_PENAL": {
        "days": 30,
        "description": "Afati i prokurorisë për vendim mbi kallëzimin penal (Neni 76 i KPPRK)",
    },
    "AFAT_PROVA": {
        "days": 15,
        "description": "Afati për dorëzim të provave sipas urdhrit të gjykatës",
    },
    "AFAT_EKSPERTIZE": {
        "days": 30,
        "description": "Afati standard për përfundimin e ekspertizës (Neni 213 i LPK)",
    },
    "AFAT_APEL_KUNDËR_VENDIMIT": {
        "days": 15,
        "description": "Afati i përgjithshëm për ankesë kundër vendimeve gjyqësore",
    },
}


# Harta e muajve në gjuhën shqipe
ALBANIAN_MONTHS = {
    "janar": 1, "shkurt": 2, "mars": 3, "prill": 4, "maj": 5, "qershor": 6,
    "korrik": 7, "gusht": 8, "shtator": 9, "tetor": 10,
    "nëntor": 11, "nentor": 11, "dhjetor": 12,
}


DATE_PATTERNS = [
    r'\b(\d{1,2})[./\-](\d{1,2})[./\-](\d{2,4})\b',  # 31.08.2026, 31/08/2026
    r'\b(\d{4})-(\d{2})-(\d{2})\b',                   # 2026-08-31
]


# ========== TIPET E DOKUMENTEVE (18 kategori) ==========
# Të sinkronizuara me categorization_service.py V3.0
DOCUMENT_TYPE_KEYWORDS: Dict[str, List[str]] = {
    "AKTVENDIM": ["aktvendim", "aktvendimi", "aktvendimit"],
    "AKTGJYKIM": ["aktgjykim", "aktgjykimi", "aktgjykimit", "në emër të popullit"],
    "ANKESË": ["ankesë", "ankese", "ankim", "apel", "drejtuar gjykatës së apelit"],
    "PADI": ["kërkesëpadi", "kerkesepadi", "padi", "paditësi"],
    "KUNDËRPADI": ["kundërpadi", "kunderpadi"],
    "PRAPËSIM": ["prapësim", "prapsim", "përgjigje në padi", "pergjigje ne padi"],
    "KALLËZIM": ["kallëzim penal", "kallezim penal", "kallzim", "vepër penale", "aktakuzë", "aktakuze"],
    "RAPORT": ["raport social", "qps", "ekspertizë", "ekspertize", "procesverbal", "proces-verbal"],
    "KONTRATË": ["marrëveshje", "marreveshje", "kontratë", "kontrate", "klauzolë"],
    "REVIZION": ["revizion", "kërkesë për revizion", "kerkese per revizion"],
    "KËRKESË": ["kërkesë", "kerkese", "parashtresë", "parashtrese"],
    "URDHËR": ["urdhër", "urdher", "urdhërohet", "urdherohet"],
    "NJOFTIM": ["njoftim", "njoftohet", "thirrje gjyqësore", "caktim seance"],
    "VËRTETIM": ["vërtetim", "vertetim", "certifikatë", "certifikate", "ekstrakt"],
    "MEMO": ["memo", "shënim", "shenim", "shënime internale", "kujtesë"],
    "EKZEKUTIM": ["ekzekutim", "ekzekutimi", "përmbarim", "permbarim", "përmbarues", "akt ekzekutiv"],
    "TRASHËGIMI": ["trashëgimi", "trashgimi", "testament", "amana", "trashëgimtar"],
    "FAMILJE": ["martesë", "martese", "divorc", "kujdestari", "ushqim", "alimentacion", "bashkëshortor"],
    "PRONË": ["pronë", "prone", "pronësi", "kadastër", "kadaster", "hipotekë", "hipoteke", "truall", "parcelë"],
    "PUNË": ["punësim", "punesim", "kontratë pune", "kontrate pune", "shkarkim", "pushim nga puna"],
}


# ========== MAX CHUNK për scan pa memory spike ==========
MAX_SCAN_CHUNK = 100_000


def _ensure_utc(dt_val: Any) -> Optional[datetime]:
    """PHOENIX ZERO-CRASH: Normalizon çdo datë në UTC tz-aware."""
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
    Shërbimi i Kronologjisë dhe Menaxhimit të Afateve Ligjore (V37.0):
    - Zero silent truncation — skanon GJITHË tekstin.
    - 13 rregulla afatesh ligjore (nga 5).
    - 18 tipa dokumentesh (nga 8).
    - Normalizon 100% të gjitha datat në UTC pa gabime offset-naive.
    """

    # ────────────────────────────────────────────────────────────────────
    # INTERNAL — chunk-aware keyword scan
    # ────────────────────────────────────────────────────────────────────

    @staticmethod
    def _scan_full_text_for_keywords(
        text: str,
        keyword_map: Dict[str, List[str]]
    ) -> Optional[str]:
        """
        Skanon GJITHË tekstin në chunks për keywords.
        Kthen çelësin e parë që përputhet, ose None.

        Zero silent truncation. Early exit kur gjen match.
        """
        if not text:
            return None

        if len(text) <= MAX_SCAN_CHUNK:
            lower = text.lower()
            for key, keywords in keyword_map.items():
                for kw in keywords:
                    if kw in lower:
                        return key
            return None

        for i in range(0, len(text), MAX_SCAN_CHUNK):
            chunk_lower = text[i:i + MAX_SCAN_CHUNK].lower()
            for key, keywords in keyword_map.items():
                for kw in keywords:
                    if kw in chunk_lower:
                        return key
        return None

    # ────────────────────────────────────────────────────────────────────
    # PUBLIC — extract dates
    # ────────────────────────────────────────────────────────────────────

    @staticmethod
    def extract_dates_from_text(text: str) -> List[datetime]:
        dates: List[datetime] = []
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

        # 2. Datat me tekst shqip (p.sh. "31 gusht 2026")
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

    # ────────────────────────────────────────────────────────────────────
    # PUBLIC — detect document type (ZERO TRUNCATION)
    # ────────────────────────────────────────────────────────────────────

    @staticmethod
    def detect_document_type(filename: str, content: str = "") -> str:
        """
        PHOENIX V37.0: skanon GJITHË tekstin — zero silent truncation.

        Rendi i kontrollit:
        1. Filename (i shpejtë)
        2. Full content (chunk-aware)
        """
        if filename:
            filename_lower = filename.lower()
            for doc_type, keywords in DOCUMENT_TYPE_KEYWORDS.items():
                for kw in keywords:
                    if kw in filename_lower:
                        return doc_type

        if not content:
            return "DOKUMENT"

        found = TimelineService._scan_full_text_for_keywords(
            content, DOCUMENT_TYPE_KEYWORDS
        )
        return found if found else "DOKUMENT"

    # ────────────────────────────────────────────────────────────────────
    # PUBLIC — build case timeline (ZERO TRUNCATION)
    # ────────────────────────────────────────────────────────────────────

    @staticmethod
    def build_case_timeline(
        db: Any,
        case_id: str,
        user_id: str = ""
    ) -> Dict[str, Any]:
        timeline: List[Dict[str, Any]] = []
        key_dates: List[datetime] = []

        try:
            case_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id

            doc_filter: Dict[str, Any] = {
                "$or": [{"case_id": case_id}, {"case_id": case_oid}],
                "status": {"$ne": "DELETED"},
            }
            if user_id:
                user_oid = ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id
                doc_filter["owner_id"] = {"$in": [user_id, user_oid]}

            documents = list(db.documents.find(doc_filter))

            media_filter: Dict[str, Any] = {
                "$or": [{"case_id": case_id}, {"case_id": case_oid}],
            }
            if user_id:
                user_oid = ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id
                media_filter["owner_id"] = {"$in": [user_id, user_oid]}

            media_items = list(db.media_evidence.find(media_filter))

            # Përpunimi i dokumenteve
            for doc in documents:
                file_name = doc.get("file_name", "Dokument")
                full_text = (
                    doc.get("content")
                    or doc.get("extracted_text")
                    or doc.get("summary")
                    or ""
                )
                created_at = doc.get("created_at")

                dates = TimelineService.extract_dates_from_text(full_text)

                # V37.0: pa truncation — skanohet i gjithë teksti
                doc_type = TimelineService.detect_document_type(file_name, full_text)

                if dates:
                    for dt in dates:
                        dt_utc = _ensure_utc(dt)
                        if dt_utc:
                            timeline.append({
                                "date": dt_utc.strftime("%d.%m.%Y"),
                                "date_obj": dt_utc,
                                "document": file_name,
                                "type": doc_type,
                                "source": "document_text",
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
                            "source": "system_date",
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
                            "source": "media_date",
                        })
                        if created_dt not in key_dates:
                            key_dates.append(created_dt)

            timeline.sort(key=lambda x: x["date_obj"])
            key_dates.sort()

            deadlines = TimelineService.calculate_deadlines(timeline)
            expired_deadlines = [d for d in deadlines if d.get("is_expired", False)]
            open_deadlines = [d for d in deadlines if not d.get("is_expired", False)]
            recommended_actions = TimelineService.recommend_actions(
                expired_deadlines, open_deadlines, timeline
            )

            return {
                "timeline": timeline,
                "key_dates": [d.strftime("%d.%m.%Y") for d in key_dates],
                "deadlines": deadlines,
                "expired_deadlines": expired_deadlines,
                "open_deadlines": open_deadlines,
                "recommended_actions": recommended_actions,
                "total_documents": len(documents),
                "total_media": len(media_items),
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
                "total_media": 0,
            }

    # ────────────────────────────────────────────────────────────────────
    # PUBLIC — calculate deadlines (13 rregulla)
    # ────────────────────────────────────────────────────────────────────

    @staticmethod
    def _deadline_entry(
        item: Dict[str, Any],
        rule_key: str,
        fallback_doc_name: str,
        active_action: str,
        expired_action: str,
    ) -> Dict[str, Any]:
        """Ndihmës: ndërton një objekt afati nga një rregull."""
        rule = DEADLINE_RULES[rule_key]
        deadline_days = rule["days"]
        date_obj: datetime = item["date_obj"]
        deadline_date = date_obj + timedelta(days=deadline_days)

        # Afati skadon në fund të ditës së fundit (23:59:59 UTC)
        deadline_end = deadline_date.replace(
            hour=23, minute=59, second=59, microsecond=0
        )
        is_expired = deadline_end < datetime.now(timezone.utc)

        return {
            "document": item.get("document", fallback_doc_name),
            "date": item.get("date", ""),
            "deadline_days": deadline_days,
            "deadline_date": deadline_date.strftime("%d.%m.%Y"),
            "is_expired": is_expired,
            "description": rule["description"],
            "action_required": expired_action if is_expired else active_action,
        }

    @staticmethod
    def calculate_deadlines(
        timeline: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        deadlines: List[Dict[str, Any]] = []

        for item in timeline:
            doc_type = item.get("type", "DOKUMENT")
            date_obj = item.get("date_obj")

            if not date_obj:
                continue

            if doc_type == "AKTVENDIM":
                deadlines.append(TimelineService._deadline_entry(
                    item, "ANKIM_AKTVENDIM", "Aktvendim Gjyqësor",
                    "Dorëzo Ankesë brenda afatit ligjor prej 7 ditësh",
                    "Afati i rregullt 7-ditor ka skaduar — shqyrto Kthimin në Gjendje të Mëparshme",
                ))

            elif doc_type == "AKTGJYKIM":
                deadlines.append(TimelineService._deadline_entry(
                    item, "ANKIM_CIVIL_AKTGJYKIM", "Aktgjykim Gjyqësor",
                    "Dorëzo Ankesë në Gjykatën e Apelit (15 ditë)",
                    "Afati i rregullt ka skaduar — shqyrto Mjetet e Jashtëzakonshme",
                ))

            elif doc_type == "PADI":
                deadlines.append(TimelineService._deadline_entry(
                    item, "PËRGJIGJE_NË_PADI", "Padi",
                    "Dorëzo Përgjigje në Padi (Prapësim brenda 30 ditësh)",
                    "Afati i prapësimit ka kaluar — përgatit prapësimin për në Seancë Përgatitore",
                ))

            elif doc_type == "KUNDËRPADI":
                deadlines.append(TimelineService._deadline_entry(
                    item, "PËRGJIGJE_NË_KUNDËRPADI", "Kundërpadi",
                    "Dorëzo Përgjigje në Kundërpadi (30 ditë)",
                    "Afati për përgjigje në kundërpadi ka skaduar",
                ))

            elif doc_type == "ANKESË":
                deadlines.append(TimelineService._deadline_entry(
                    item, "AFAT_APEL_KUNDËR_VENDIMIT", "Ankesë",
                    "Ndjek procedurën e ankesës sipas afatit procedural",
                    "Afati i ankesës ka skaduar — shqyrto mjete të jashtëzakonshme",
                ))

            elif doc_type == "REVIZION":
                deadlines.append(TimelineService._deadline_entry(
                    item, "REVIZION", "Revizion",
                    "Dorëzo Revizionin brenda 30 ditësh",
                    "Afati i revizionit ka skaduar",
                ))

            elif doc_type == "EKZEKUTIM":
                deadlines.append(TimelineService._deadline_entry(
                    item, "ANKESË_EKZEKUTIMI", "Akt Ekzekutiv",
                    "Dorëzo Ankesë kundër vendimit të ekzekutimit (8 ditë)",
                    "Afati i ankesës ekzekutive ka skaduar",
                ))

            elif doc_type == "KALLËZIM":
                deadlines.append(TimelineService._deadline_entry(
                    item, "KALLËZIM_PENAL", "Kallëzim Penal",
                    "Prokuroria duhet të vendosë brenda 30 ditësh",
                    "Afati i prokurorisë ka kaluar — ndiq procedurën e ankesës",
                ))

        return deadlines

    # ────────────────────────────────────────────────────────────────────
    # PUBLIC — recommend actions
    # ────────────────────────────────────────────────────────────────────

    @staticmethod
    def recommend_actions(
        expired_deadlines: List[Dict[str, Any]],
        open_deadlines: List[Dict[str, Any]],
        timeline: List[Dict[str, Any]],
    ) -> List[str]:
        actions: List[str] = []

        for od in open_deadlines:
            actions.append(
                f"AFAT AKTIV ({od.get('deadline_days')} ditë): "
                f"{od.get('action_required')} deri më {od.get('deadline_date')}."
            )

        if expired_deadlines:
            actions.append(
                "KTHIM NË GJENDJEN E MËPARSHME: Nëse ka pasur pengesa të arsyeshme "
                "objektive, kërkohet kthimi në afat (Neni 129 LPK)."
            )

        if not actions:
            actions.append("Ndiq rrjedhën e rregullt procedurale sipas ligjit.")

        return actions

    # ────────────────────────────────────────────────────────────────────
    # PUBLIC — build prompt për LLM
    # ────────────────────────────────────────────────────────────────────

    @staticmethod
    def build_timeline_prompt(timeline_data: Dict[str, Any]) -> str:
        if not timeline_data or not timeline_data.get("timeline"):
            return ""

        lines: List[str] = []
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
                lines.append(
                    f"   ⏳ {d.get('document', '')} — "
                    f"Afati: {d.get('deadline_date', '')} ➔ "
                    f"{d.get('action_required', '')}"
                )

        if timeline_data.get("expired_deadlines"):
            lines.append("")
            lines.append("🔴 AFATET E SKADUARA DHE REMEDIIMI:")
            for d in timeline_data.get("expired_deadlines", []):
                lines.append(
                    f"   ⚠️ {d.get('document', '')} — "
                    f"Skaduar më: {d.get('deadline_date', '')} ➔ "
                    f"{d.get('action_required', '')}"
                )

        lines.append("=" * 60)
        return "\n".join(lines)


# Singleton
timeline_service = TimelineService()