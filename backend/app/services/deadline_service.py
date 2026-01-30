# FILE: backend/app/services/deadline_service.py
# PHOENIX PROTOCOL - DEADLINE ENGINE V7.0 (NOISE REDUCTION)
# 1. UPGRADE: LLM now categorizes dates into 'AGENDA' or 'FACT'.
# 2. LOGIC: Facts (Birthdays, historical events) are stored but excluded from UI Agenda.
# 3. RESULT: Calendar only shows actionable professional events.

import os
import json
import structlog
import dateparser
import re
from datetime import datetime, timezone, timedelta
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

SPREADSHEET_EXTENSIONS = ('.csv', '.xlsx', '.xls', '.ods', '.numbers', '.txt', '.dat')
SPREADSHEET_KEYWORDS = ["financa", "finance", "fatura", "invoice", "pasqyra", "bank", "transaksion", "statement"]

def _is_spreadsheet_file(doc: DocumentOut) -> bool:
    filename = doc.file_name.lower() if doc.file_name else ""
    for keyword in SPREADSHEET_KEYWORDS:
        if keyword in filename: return True
    if filename.endswith(SPREADSHEET_EXTENSIONS): return True
    return False

def _preprocess_date_text(text: str) -> str:
    text_lower = text.lower()
    for sq, en in AL_MONTHS.items():
        text_lower = text_lower.replace(sq, en)
    return text_lower

def _extract_dates_with_llm(full_text: str) -> List[Dict[str, str]]:
    truncated_text = full_text[:25000]
    current_date = datetime.now().strftime("%d %B %Y")
    
    # PHOENIX: Upgraded prompt for noise reduction
    system_prompt = f"""
    Ti je "Kujdestari i Afateve". DATA SOT: {current_date}.
    DETYRA: Analizo tekstin dhe nxirr TË GJITHA datat. Kategorizo secilën.
    
    KATEGORITË (FUSHË E DETYRUESHME 'category'):
    1. "AGENDA": Afate ligjore, seanca, takime, taksa, afate dorëzimi (çfarë duhet të jetë në kalendar).
    2. "FACT": Datëlindje, data martese, data lëshimi të vjetra, fakte historike të rastit (vetëm për metadata).

    RREGULLA:
    1. Injoro datat e cituara në nene të ligjit.
    2. Përshkruaj shkurt (max 5 fjalë).

    FORMATI JSON:
    {{
      "events": [
         {{ "title": "Datëlindja e Palës", "date_text": "12 Maj 1985", "category": "FACT", "description": "Informacion personal" }},
         {{ "title": "Ankesë", "date_text": "15 Shkurt 2026", "category": "AGENDA", "description": "Afati i fundit për ankesë" }}
      ]
    }}
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
            data = json.loads(response.choices[0].message.content or "{}")
            return data.get("events", [])
        except Exception as e:
            logger.warning(f"LLM Extraction Failed: {e}")
    return []

def extract_and_save_deadlines(db: Database, document_id: str, full_text: str):
    log = logger.bind(document_id=document_id)
    try:
        doc_oid = ObjectId(document_id)
        document_raw = db.documents.find_one({"_id": doc_oid})
        if not document_raw: return
        document = DocumentOut.model_validate(document_raw)
    except Exception as e:
        log.error(f"Doc fetch failed: {e}")
        return

    events = _extract_dates_with_llm(full_text)
    if not events: return

    if _is_spreadsheet_file(document):
        db.documents.update_one({"_id": doc_oid}, {"$set": {"ai_metadata.extracted_invoice_dates": events}})
        db.calendar_events.delete_many({"document_id": document_id})
        return

    valid_events = []
    for item in events:
        raw_date = item.get("date_text", "")
        if not raw_date: continue
        
        parsed = dateparser.parse(_preprocess_date_text(raw_date), settings={'DATE_ORDER': 'DMY'})
        if not parsed: continue
        
        # PHOENIX: Set category strictly based on LLM decision
        cat = EventCategory.FACT if item.get("category") == "FACT" else EventCategory.AGENDA
        
        now = datetime.now()
        status_to_assign = EventStatus.RESOLVED if parsed < now else EventStatus.PENDING
        priority_to_assign = EventPriority.HIGH if (parsed > now and cat == EventCategory.AGENDA) else EventPriority.NORMAL
        
        valid_events.append({
            "case_id": str(document.case_id),       
            "owner_id": document.owner_id,
            "document_id": document_id,
            "title": item.get("title", "Datë e Ekstraktuar"),
            "category": cat, # PHOENIX: Categorization
            "description": f"{item.get('description', '')}\n(Burimi: {document.file_name})", 
            "start_date": parsed,         
            "end_date": parsed,           
            "is_all_day": True,
            "event_type": EventType.DEADLINE if cat == EventCategory.AGENDA else EventType.OTHER, 
            "status": status_to_assign,     
            "priority": priority_to_assign, 
            "created_at": datetime.now(timezone.utc)
        })

    if valid_events:
        db.calendar_events.delete_many({"document_id": document_id}) 
        db.calendar_events.insert_many(valid_events)