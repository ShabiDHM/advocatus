# FILE: backend/app/services/deadline_service.py
# PHOENIX PROTOCOL - DEADLINE ENGINE V5.0 (ROBUST EXTRACTION)
# 1. FIX: Resolves JSON Schema conflict (List vs Object) by enforcing root dictionary.
# 2. FIX: Removes aggressive 'future-only' filtering to ensure timeline completeness.
# 3. FIX: Standardizes 'case_id' handling to ensure Mongo queries match.

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

logger = structlog.get_logger(__name__)

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY") 
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat" 

# PHOENIX: Manual Albanian-to-English Mapping for Robust Parsing
AL_MONTHS = {
    "janar": "January", "shkurt": "February", "mars": "March", "prill": "April",
    "maj": "May", "qershor": "June", "korrik": "July", "gusht": "August",
    "shtator": "September", "tetor": "October", "nëntor": "November", "nentor": "November",
    "dhjetor": "December"
}

def _clean_json_string(json_str: str) -> str:
    """Removes markdown formatting to ensure pure JSON parsing."""
    cleaned = re.sub(r'^```json\s*', '', json_str, flags=re.MULTILINE)
    cleaned = re.sub(r'^```\s*', '', cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r'```\s*$', '', cleaned, flags=re.MULTILINE)
    return cleaned.strip()

def _preprocess_date_text(text: str) -> str:
    """Replaces Albanian months with English to help dateparser."""
    text_lower = text.lower()
    for sq, en in AL_MONTHS.items():
        text_lower = text_lower.replace(sq, en)
    return text_lower

def _extract_dates_with_regex(text: str) -> List[Dict[str, str]]:
    matches = []
    
    # 1. Textual: "12 Dhjetor 2025" or "12 Dhjetor"
    # Matches: DD Month YYYY (optional YYYY)
    text_pattern = r'\b(\d{1,2})\s+(Janar|Shkurt|Mars|Prill|Maj|Qershor|Korrik|Gusht|Shtator|Tetor|Nëntor|Dhjetor)\s*(\d{4})?\b'
    
    # 2. Numeric: "12.12.2025" or "12/12/25"
    numeric_pattern = r'\b(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})\b'

    found_text = re.findall(text_pattern, text, re.IGNORECASE)
    for day, month, year in found_text:
        if not year: year = str(datetime.now().year)
        matches.append({"title": "Afat (Tekst)", "date_text": f"{day} {month} {year}", "description": "Ekstraktuar nga regex (tekst)."})

    found_numeric = re.findall(numeric_pattern, text)
    for day, month, year in found_numeric:
        # Normalize year "25" -> "2025"
        full_year = year
        if len(year) == 2: full_year = "20" + year
        matches.append({"title": "Afat (Numerik)", "date_text": f"{day}.{month}.{full_year}", "description": "Ekstraktuar nga regex (numerik)."})

    return matches

def _extract_dates_with_llm(full_text: str) -> List[Dict[str, str]]:
    # Limit context window to avoid token limits
    truncated_text = full_text[:25000]
    current_date = datetime.now().strftime("%d %B %Y")
    
    # IMPROVED PROMPT: Explicitly requests a JSON Object wrapper "events"
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
                # Relaxed to "json_object" now that we return a root dict
                response_format={"type": "json_object"},
                temperature=0.1
            )
            
            raw_content = response.choices[0].message.content or "{}"
            cleaned_content = _clean_json_string(raw_content)
            data = json.loads(cleaned_content)
            
            # Robust parsing: Check for 'events' key, then fallback to direct list
            if isinstance(data, dict):
                return data.get("events", [])
            elif isinstance(data, list):
                return data
            return []
            
        except Exception as e:
            logger.warning(f"LLM Extraction Failed: {e}")
            # Fallback is handled by caller
    
    return []

def extract_and_save_deadlines(db: Database, document_id: str, full_text: str):
    log = logger.bind(document_id=document_id)
    
    try:
        doc_oid = ObjectId(document_id)
        document = db.documents.find_one({"_id": doc_oid})
    except Exception as e:
        log.error(f"Invalid Document ID: {e}")
        return

    if not document: 
        log.warning("Document not found for deadline extraction.")
        return

    # Normalize IDs for Consistency
    case_id_str = str(document.get("case_id", ""))
    owner_id = document.get("owner_id")
    
    # Ensure owner_id is ObjectId if possible, but keep consistent with User model
    if isinstance(owner_id, str):
        try: owner_id = ObjectId(owner_id)
        except: pass

    # 1. Extraction Strategy
    events = _extract_dates_with_llm(full_text)
    
    # Fallback to Regex if LLM returns nothing
    if not events:
        log.info("LLM returned no events, falling back to Regex.")
        events = _extract_dates_with_regex(full_text[:10000])

    if not events:
        log.info("No dates found via LLM or Regex.")
        return

    # 2. Processing & Filtering
    valid_events = []
    
    # We remove the 30-day cutoff. History is valuable in legal cases.
    # The Dashboard will filter "Alerts" (future only), but "Events" should show everything.
    
    for item in events:
        raw_date = item.get("date_text", "")
        if not raw_date: continue
        
        # Preprocess: Albanian -> English
        clean_date_str = _preprocess_date_text(raw_date)
        
        # Parse: Removed 'future' preference to allow historical accuracy
        parsed = dateparser.parse(
            clean_date_str, 
            settings={'DATE_ORDER': 'DMY'}
        )
        
        if not parsed: 
            continue
        
        # Determine Status
        now = datetime.now()
        status = "PENDING"
        if parsed < now:
            status = "RESOLVED" # Past events are implicitly resolved/done
        
        # Create Event Object
        valid_events.append({
            "case_id": case_id_str,       # Stored as string for query compatibility
            "caseId": case_id_str,        # Redundancy for frontend legacy support
            "owner_id": owner_id,
            "document_id": document_id,
            "title": item.get("title", "Datë e Ekstraktuar"),
            "description": f"{item.get('description', '')}\n(Burimi: {document.get('file_name', 'Dokument')})",
            "start_date": parsed,         # BSON Date
            "end_date": parsed,           # BSON Date
            "is_all_day": True,
            "event_type": "DEADLINE",
            "status": status,
            "priority": "HIGH" if parsed > now else "NORMAL",
            "created_at": datetime.now(timezone.utc)
        })

    # 3. Persistence
    if valid_events:
        try:
            # Clean up previous extractions for this document to avoid duplicates
            db.calendar_events.delete_many({"document_id": document_id, "event_type": "DEADLINE"})
            
            result = db.calendar_events.insert_many(valid_events)
            log.info("deadline_service.saved", count=len(valid_events), inserted_ids=[str(id) for id in result.inserted_ids])
        except Exception as e:
            log.error(f"Failed to save events to DB: {e}")
    else:
        log.info("No valid dates could be parsed from the extraction results.")