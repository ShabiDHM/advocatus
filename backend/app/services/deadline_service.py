# FILE: backend/app/services/deadline_service.py
# PHOENIX PROTOCOL - DEADLINE ENGINE V8.3 (STRONGER AGENDA CLASSIFICATION + FALLBACK RULES)
# 1. ENHANCED: System prompt now explicitly lists AGENDA examples.
# 2. ADDED: Fallback rule: future dates with procedural keywords are forced to AGENDA.
# 3. ADDED: Logging of fallback overrides.
# 4. STATUS: More reliable calendar population.

import os
import json
import structlog
import dateparser
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from bson import ObjectId
from pymongo.database import Database
from openai import OpenAI 

from . import document_service 
from ..models.document import DocumentOut
from ..models.calendar import EventType, EventStatus, EventPriority, EventCategory

logger = structlog.get_logger(__name__)

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY") 
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat" 

AL_MONTHS = {
    "janar": "January", "shkurt": "February", "mars": "March", "prill": "April",
    "maj": "May", "qershor": "June", "korrik": "July", "gusht": "August",
    "shtator": "September", "tetor": "October", "nëntor": "November", "nentor": "November",
    "dhjetor": "December"
}

# Keywords that indicate a date is likely an actionable agenda item
AGENDA_KEYWORDS = [
    "seancë", "seanca", "gjykim", "shqyrtim", "afat", "afati", "dorëzim", "paraqitje",
    "pagesë", "depozitë", "inspektim", "takim", "dëgjim", "seancë dëgjimore",
    "mbrojtje", "ankesë", "padi", "kërkesë", "paradhënie", "provim"
]

def _preprocess_date_text(text: str) -> str:
    text_lower = text.lower()
    for sq, en in AL_MONTHS.items():
        text_lower = text_lower.replace(sq, en)
    return text_lower

def _extract_dates_with_llm(full_text: str, doc_category: str) -> List[Dict[str, str]]:
    truncated_text = full_text[:25000]
    current_date = datetime.now().strftime("%d %B %Y")
    
    logger.info(f"LLM input text length: {len(truncated_text)}")
    logger.info(f"LLM input text preview: {truncated_text[:500]}...")
    
    # Enhanced prompt with explicit AGENDA examples
    system_prompt = f"""
    Ti je "Senior Legal Analyst". DATA SOT: {current_date}.
    DETYRA: Analizo këtë dokument ({doc_category}) dhe nxirr të gjitha datat e rëndësishme.
    
    RREGULLA TË RREPTA:
    - **AGENDA** janë VETËM afatet ligjore të ardhshme që kërkojnë veprim nga avokati ose palët, si:
        * Seanca gjyqësore, dëgjime, inspektime.
        * Afate për dorëzimin e provave, ekspertizave, ankesave.
        * Pagesa të detyrueshme, paradhënie, depozita.
        * Takime me klientin ose palët e tjera.
    - **FACT** janë të gjitha datat e tjera:
        * Data e ngjarjeve të kaluara (lindje, nënshkrim kontrate, ngjarje historike).
        * Data të mesazheve në biseda (CHAT).
        * Data që nuk kanë ndikim në veprimet e ardhshme ligjore.
    
    KATEGORITË:
    - "AGENDA": Shfaqet në kalendarin e avokatit.
    - "FACT": Përdoret vetëm për kronologji dhe analizë.
    
    Kthe JSON: {{ "events": [ {{ "title": "...", "date_text": "...", "category": "AGENDA|FACT", "description": "..." }} ] }}
    """

    if DEEPSEEK_API_KEY:
        try:
            client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=OPENROUTER_BASE_URL)
            response = client.chat.completions.create(
                model=OPENROUTER_MODEL,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": truncated_text}],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            raw_content = response.choices[0].message.content or "{}"
            logger.info(f"LLM raw response: {raw_content}")
            data = json.loads(raw_content)
            events = data.get("events", [])
            logger.info(f"LLM extracted events count: {len(events)}")
            return events
        except Exception as e:
            logger.warning(f"LLM Extraction Failed: {e}")
            logger.exception("Full traceback:")
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
            log.debug("Skipping item with empty date_text", item=item)
            continue
        
        log.debug("Processing date", raw_date=raw_date)
        
        parsed = dateparser.parse(_preprocess_date_text(raw_date), settings={'DATE_ORDER': 'DMY'})
        if not parsed:
            log.warning("Could not parse date", raw_date=raw_date)
            continue
        
        log.debug("Parsed date", parsed_date=parsed.isoformat())
        
        # Get LLM category (default to FACT if missing)
        llm_category = item.get("category", "FACT")
        description = item.get("description", "")
        title = item.get("title", "")
        
        # --- FALLBACK RULE: Force AGENDA if future and contains procedural keywords ---
        is_future = parsed >= now
        is_not_chat = doc_category.upper() not in ["CHAT_LOG", "WHATSAPP", "BISEDË"]
        contains_keyword = any(kw in description.lower() or kw in title.lower() for kw in AGENDA_KEYWORDS)
        
        final_category = llm_category
        if is_future and is_not_chat and contains_keyword:
            if final_category != "AGENDA":
                logger.info(f"Fallback: overriding {llm_category} to AGENDA for date {raw_date} (keyword match)")
                final_category = "AGENDA"
        
        # Build chronology item
        metadata_chronology.append({
            "title": title,
            "date": parsed,
            "category": final_category,
            "description": description
        })

        is_agenda = final_category == "AGENDA"
        log.debug("Gating checks", 
                  is_agenda=is_agenda, 
                  is_future=is_future, 
                  is_not_chat=is_not_chat,
                  contains_keyword=contains_keyword,
                  final_category=final_category)

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

    # Save chronology metadata
    db.documents.update_one(
        {"_id": doc_oid}, 
        {"$set": {"ai_metadata.case_chronology": metadata_chronology}}
    )
    log.info("Saved chronology items", count=len(metadata_chronology))

    # Replace calendar events for this document
    db.calendar_events.delete_many({"document_id": document_id}) 
    if calendar_events:
        db.calendar_events.insert_many(calendar_events)
        log.info("calendar.events_synced", count=len(calendar_events))
    else:
        log.info("calendar.no_actionable_events_found")