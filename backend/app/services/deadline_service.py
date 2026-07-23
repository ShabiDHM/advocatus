# FILE: backend/app/services/deadline_service.py
# PHOENIX PROTOCOL - DEADLINE ENGINE V8.6 (CORRECTED F-STRING BRACES)

import json
import structlog
import dateparser
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from bson import ObjectId
from pymongo.database import Database

from . import document_service, llm_service
from ..models.document import DocumentOut
from ..models.calendar import EventType, EventStatus, EventPriority, EventCategory

logger = structlog.get_logger(__name__)

AL_MONTHS = {
    "janar": "January", "shkurt": "February", "mars": "March", "prill": "April",
    "maj": "May", "qershor": "June", "korrik": "July", "gusht": "August",
    "shtator": "September", "tetor": "October", "nëntor": "November", "nentor": "November",
    "dhjetor": "December"
}

AGENDA_KEYWORDS = [
    "seancë", "seanca", "gjykim", "shqyrtim", "afat", "afati", "dorëzim", "paraqitje",
    "pagesë", "depozitë", "inspektim", "takim", "dëgjim", "seancë dëgjimore",
    "mbrojtje", "ankesë", "padi", "kërkesë", "paradhënie", "provim", "urdhërohet"
]

def _preprocess_date_text(text: str) -> str:
    text_lower = text.lower()
    for sq, en in AL_MONTHS.items():
        text_lower = text_lower.replace(sq, en)
    return text_lower

def _extract_dates_with_llm(full_text: str, doc_category: str) -> List[Dict[str, str]]:
    truncated_text = full_text[:40000]
    current_date = datetime.now().strftime("%d %B %Y")
    
    logger.info(f"Deadline Engine input text length: {len(truncated_text)}")
    
    system_prompt = f"""
    Ti je "Senior Legal Analyst" për Gjykatat e Kosovës. DATA SOT: {current_date}.
    DETYRA: Analizo këtë procesverbal ose aktvendim gjyqësor ({doc_category}) dhe nxirr çdo afat kohor, urdhër veprimi për avokatin, ose datë seance.
    
    KUSHTET E RREPTA:
    - Kërko për fjalë kyçe si "në afat prej X ditëve", "urdhërohet", "shtyhet seanca", "caktuar për datën".
    - **AGENDA**: Afate ligjore të ardhshme ose urdhëresa që kërkojnë veprim procedural (p.sh. dorëzim prokure brenda 7 ditëve).
    - **FACT**: Ngjarje të kaluara (p.sh. seanca e mbajtur më 15 korrik 2026).
    
    Kthe VETËM një objekt JSON në këtë format exact:
    {{
      "events": [
        {{"title": "Titulli i afatit ose urdhrit", "date_text": "Data ose afati kohor i shprehur në tekst", "category": "AGENDA", "description": "Përshkrimi i saktë i detyrimit"}}
      ]
    }}
    """

    try:
        raw_content = llm_service._call_llm(system_prompt, truncated_text, json_mode=True, temperature=0.1, model=llm_service.FAST_MODEL)
        data = llm_service.clean_and_parse_json(raw_content)
        events = data.get("events", [])
        logger.info(f"LLM extracted events count: {len(events)}")
        return events
    except Exception as e:
        logger.warning(f"LLM Deadline Extraction Failed: {e}")
        return []

def extract_and_save_deadlines(db: Database, document_id: str, full_text: str, doc_category: str = "Unknown"):
    log = logger.bind(document_id=document_id, category=doc_category)
    try:
        doc_oid = ObjectId(document_id)
        document_raw = db.documents.find_one({"_id": doc_oid})
        if not document_raw: return
        document = DocumentOut.model_validate(document_raw)
    except Exception:
        return

    extracted_items = _extract_dates_with_llm(full_text, doc_category)
    if not extracted_items:
        log.info("No events extracted from document.")
        return

    calendar_events = []
    metadata_chronology = []
    now = datetime.now()

    for item in extracted_items:
        raw_date = item.get("date_text", "")
        if not raw_date:
            continue
        
        parsed = dateparser.parse(_preprocess_date_text(raw_date), settings={'DATE_ORDER': 'DMY'})
        if not parsed:
            continue
        
        llm_category = item.get("category", "FACT")
        description = item.get("description", "")
        title = item.get("title", "")
        
        is_future = parsed >= now
        is_not_chat = doc_category.upper() not in ["CHAT_LOG", "WHATSAPP", "BISEDË"]
        contains_keyword = any(kw in description.lower() or kw in title.lower() for kw in AGENDA_KEYWORDS)
        
        final_category = llm_category
        if is_future and is_not_chat and contains_keyword:
            if final_category != "AGENDA":
                logger.info(f"Fallback: overriding {llm_category} to AGENDA for date {raw_date} (keyword match)")
                final_category = "AGENDA"
        
        metadata_chronology.append({
            "title": title,
            "date": parsed,
            "category": final_category,
            "description": description
        })

        is_agenda = final_category == "AGENDA"
        if is_agenda and is_future and is_not_chat:
            calendar_events.append({
                "case_id": str(document.case_id),       
                "owner_id": document.owner_id,
                "document_id": document_id,
                "title": title,
                "category": EventCategory.AGENDA,
                "description": f"{description}\n(Burimi: {document.file_name})", 
                "start_date": parsed,         
                "end_date": parsed,           
                "is_all_day": True,
                "event_type": EventType.DEADLINE, 
                "status": EventStatus.PENDING,     
                "priority": EventPriority.HIGH, 
                "created_at": datetime.now(timezone.utc)
            })
            log.info("Added to calendar", title=title, date=parsed.isoformat())

    db.documents.update_one(
        {"_id": doc_oid}, 
        {"$set": {"ai_metadata.case_chronology": metadata_chronology}}
    )
    log.info("Saved chronology items", count=len(metadata_chronology))

    db.calendar_events.delete_many({"document_id": document_id}) 
    if calendar_events:
        db.calendar_events.insert_many(calendar_events)
        log.info("calendar.events_synced", count=len(calendar_events))
    else:
        log.info("calendar.no_actionable_events_found")