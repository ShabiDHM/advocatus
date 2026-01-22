# FILE: backend/app/services/deadline_service.py
# PHOENIX PROTOCOL - DEADLINE ENGINE V6.1 (KEYWORD IRONCLAD)
# 1. CRITICAL UPGRADE: Adds "Keyword Guard" to catch files named 'financa', 'fatura', etc.
#    This solves cases where MIME types or Extensions are ambiguous.
# 2. FIXED: Properly utilizes the SPREADSHEET_EXTENSIONS tuple (including .txt).
# 3. RESULT: Any file looking like a financial record goes to Knowledge Base, NOT Calendar.

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
from ..models.calendar import EventType, EventStatus, EventPriority 

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

# 1. MIME Types to block
SPREADSHEET_MIME_TYPES = [
    "text/csv", 
    "application/csv",
    "text/x-csv",
    "application/x-csv",
    "text/comma-separated-values",
    "text/x-comma-separated-values",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
    "application/vnd.ms-excel",
    "application/octet-stream", 
    "text/plain" 
]

# 2. Extensions to block
SPREADSHEET_EXTENSIONS = ('.csv', '.xlsx', '.xls', '.ods', '.numbers', '.txt', '.dat')

# 3. Filename Keywords to block (The Ironclad Layer)
SPREADSHEET_KEYWORDS = ["financa", "finance", "fatura", "invoice", "pasqyra", "bank", "transaksion", "statement"]

def _is_spreadsheet_file(doc: DocumentOut) -> bool:
    """
    Multi-layered check to determine if a document is a spreadsheet/invoice list.
    """
    filename = doc.file_name.lower() if doc.file_name else ""
    
    # Layer A: Filename Keywords (Catch "financa_2026.pdf" if needed, or ambiguous CSVs)
    for keyword in SPREADSHEET_KEYWORDS:
        if keyword in filename:
            return True

    # Layer B: File Extension
    if filename.endswith(SPREADSHEET_EXTENSIONS):
        return True
        
    # Layer C: Explicit MIME Type
    if doc.mime_type in SPREADSHEET_MIME_TYPES:
        if "csv" in doc.mime_type or "spreadsheet" in doc.mime_type or "excel" in doc.mime_type:
            return True
            
    return False

def _clean_json_string(json_str: str) -> str:
    cleaned = re.sub(r'^```json\s*', '', json_str, flags=re.MULTILINE)
    cleaned = re.sub(r'^```\s*', '', cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r'```\s*$', '', cleaned, flags=re.MULTILINE)
    return cleaned.strip()

def _preprocess_date_text(text: str) -> str:
    text_lower = text.lower()
    for sq, en in AL_MONTHS.items():
        text_lower = text_lower.replace(sq, en)
    return text_lower

def _extract_dates_with_regex(text: str) -> List[Dict[str, str]]:
    matches = []
    
    text_pattern = r'\b(\d{1,2})\s+(Janar|Shkurt|Mars|Prill|Maj|Qershor|Korrik|Gusht|Shtator|Tetor|Nëntor|Dhjetor)\s*(\d{4})?\b'
    numeric_pattern = r'\b(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})\b'

    found_text = re.findall(text_pattern, text, re.IGNORECASE)
    for day, month, year in found_text:
        if not year: year = str(datetime.now().year)
        matches.append({"title": "Afat (Tekst)", "date_text": f"{day} {month} {year}", "description": "Ekstraktuar nga regex (tekst)."})

    found_numeric = re.findall(numeric_pattern, text)
    for day, month, year in found_numeric:
        full_year = year
        if len(year) == 2: full_year = "20" + year
        matches.append({"title": "Afat (Numerik)", "date_text": f"{day}.{month}.{full_year}", "description": "Ekstraktuar nga regex (numerik)."})

    return matches

def _extract_dates_with_llm(full_text: str) -> List[Dict[str, str]]:
    truncated_text = full_text[:25000]
    current_date = datetime.now().strftime("%d %B %Y")
    
    system_prompt = f"""
    Ti je "Zyrtar Ligjor". DATA SOT: {current_date}.
    
    DETYRA: Analizo tekstin dhe gjej TË GJITHA datat e rëndësishme (seanca, afate, nënshkrime kontratash, data lëshimi).
    
    RREGULLA:
    1. Përfshi datat e kaluara DHE datat e ardhshme.
    2. Injoro datat e parëndësishme (p.sh. datat e cituara në ligje).
    3. Përshkruaj shkurt (max 5 fjalë) ngjarjen.

    FORMATI JSON (TË DETYRUESHËM):
    {{
      "events": [
         {{ "title": "Seanca Gjyqësore", "date_text": "25 Dhjetor 2025", "description": "Dëgjimi i dëshmitarëve" }},
         {{ "title": "Nënshkrimi", "date_text": "10 Janar 2024", "description": "Data e kontratës" }}
      ]
    }}
    """

    if DEEPSEEK_API_KEY:
        try:
            client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=OPENROUTER_BASE_URL)
            response = client.chat.completions.create(
                model=OPENROUTER_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt}, 
                    {"role": "user", "content": truncated_text}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            
            # PHOENIX FIX: Correct list access
            raw_content = response.choices[0].message.content or "{}" 
            cleaned_content = _clean_json_string(raw_content)
            data = json.loads(cleaned_content)
            
            if isinstance(data, dict):
                return data.get("events", [])
            elif isinstance(data, list):
                return data
            return []
            
        except Exception as e:
            logger.warning(f"LLM Extraction Failed: {e}")
    
    return []

def extract_and_save_deadlines(db: Database, document_id: str, full_text: str):
    log = logger.bind(document_id=document_id)
    
    try:
        doc_oid = ObjectId(document_id)
        document_raw = db.documents.find_one({"_id": doc_oid})
        document = DocumentOut.model_validate(document_raw)
    except Exception as e:
        log.error(f"Invalid Document ID or Document not found: {e}")
        return

    if not document: 
        log.warning("Document not found for deadline extraction.")
        return

    case_id_str = str(document.case_id)
    owner_id = document.owner_id
    
    # 1. ALWAYS extract dates (Required for Knowledge Base)
    events = _extract_dates_with_llm(full_text)
    if not events:
        log.info("LLM returned no events, falling back to Regex.")
        events = _extract_dates_with_regex(full_text[:10000])

    if not events:
        log.info("No dates found via LLM or Regex.")
        return

    # 2. KEYWORD & EXTENSION GUARD
    # Checks Filename Keywords ("financa", "fatura") AND Extensions
    if _is_spreadsheet_file(document):
        log.info(f"File detected as Finance/Data Record (File: {document.file_name}). Processing for Metadata only.")
        
        try:
            # A. Save to Document Metadata (Knowledge Base)
            db.documents.update_one(
                {"_id": doc_oid},
                {"$set": {"ai_metadata.extracted_invoice_dates": events}}
            )
            
            # B. CLEANUP: Delete any Calendar Events for this file.
            delete_query = {
                "$or": [
                    {"document_id": document_id},
                    {"documentId": document_id}
                ]
            }
            delete_result = db.calendar_events.delete_many(delete_query)
            
            if delete_result.deleted_count > 0:
                log.info(f"Cleaned up {delete_result.deleted_count} events (Keyword Guard Triggered).")
                
        except Exception as e:
            log.error(f"Failed to update document metadata for spreadsheet: {e}")
            
        return # STOP. Do not proceed to create new calendar events.

    # 3. STANDARD DOCUMENT LOGIC (PDF/Docx)
    # Create Calendar Events for the UI
    valid_events = []
    
    for item in events:
        raw_date = item.get("date_text", "")
        if not raw_date: continue
        
        clean_date_str = _preprocess_date_text(raw_date)
        
        parsed = dateparser.parse(
            clean_date_str, 
            settings={'DATE_ORDER': 'DMY'}
        )
        
        if not parsed: 
            continue
        
        now = datetime.now()
        status_to_assign = EventStatus.RESOLVED if parsed < now else EventStatus.PENDING
        priority_to_assign = EventPriority.HIGH if parsed > now else EventPriority.NORMAL
        
        valid_events.append({
            "case_id": case_id_str,       
            "owner_id": owner_id,
            "document_id": document_id,
            "title": item.get("title", "Datë e Ekstraktuar"),
            "description": f"{item.get('description', '')}\n(Burimi: {document.file_name})", 
            "start_date": parsed,         
            "end_date": parsed,           
            "is_all_day": True,
            "event_type": EventType.DEADLINE, 
            "status": status_to_assign,     
            "priority": priority_to_assign, 
            "created_at": datetime.now(timezone.utc)
        })

    if valid_events:
        try:
            # Always clean up before inserting to prevent duplicates
            db.calendar_events.delete_many({"document_id": document_id}) 
            
            result = db.calendar_events.insert_many(valid_events)
            log.info("deadline_service.saved", count=len(valid_events), inserted_ids=[str(id) for id in result.inserted_ids])
        except Exception as e:
            log.error(f"Failed to save events to DB: {e}")
    else:
        log.info("No valid dates could be parsed from the extraction results.")