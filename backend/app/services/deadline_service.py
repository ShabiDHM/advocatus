# FILE: backend/app/services/deadline_service.py
# PHOENIX PROTOCOL - DEADLINE ENGINE V4.3 (ALBANIAN LOCALIZATION)
# 1. FIX: Added manual month translation map for robust date parsing.
# 2. FIX: Relaxed future-date filter (allows dates up to 30 days in the past).
# 3. FIX: Ensures 'case_id' is stored as string for consistency.

import os
import json
import structlog
import dateparser
import re
import httpx
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from bson import ObjectId
from pymongo.database import Database
from openai import OpenAI 

logger = structlog.get_logger(__name__)

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY") 
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat" 
LOCAL_LLM_URL = os.environ.get("LOCAL_LLM_URL", "http://local-llm:11434/api/chat")
LOCAL_MODEL_NAME = "llama3"

# PHOENIX: Manual Albanian-to-English Mapping for Robust Parsing
AL_MONTHS = {
    "janar": "January", "shkurt": "February", "mars": "March", "prill": "April",
    "maj": "May", "qershor": "June", "korrik": "July", "gusht": "August",
    "shtator": "September", "tetor": "October", "nëntor": "November", "nentor": "November",
    "dhjetor": "December"
}

def _clean_json_string(json_str: str) -> str:
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
        if len(year) == 2: year = "20" + year
        matches.append({"title": "Afat (Numerik)", "date_text": f"{day}.{month}.{year}", "description": "Ekstraktuar nga regex (numerik)."})

    return matches

def _extract_dates_with_llm(full_text: str) -> List[Dict[str, str]]:
    truncated_text = full_text[:15000]
    current_date = datetime.now().strftime("%d %B %Y")
    
    system_prompt = f"""
    Ti je "Zyrtar Ligjor". DATA SOT: {current_date}.
    DETYRA: Gjej çdo AFAT ose DATË SEANCE në tekst.
    
    RREGULLA KRITIKE:
    1. Injoro datat e dokumentit (p.sh. "Prishtinë, 2020").
    2. Gjej vetëm data për VEPRIME TË ARDHSHME (Seanca, Afate Pagese, Dorëzime).
    3. Përshkruaj shkurt (max 5 fjalë) se çfarë është afati.

    FORMATI JSON:
    [
      {{ "title": "Seance", "date_text": "25 Dhjetor 2025", "description": "Dëgjimi i dëshmitarëve" }}
    ]
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
            data = json.loads(_clean_json_string(response.choices[0].message.content or ""))
            if isinstance(data, dict):
                for val in data.values():
                    if isinstance(val, list): return val
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.warning(f"LLM Extraction Failed: {e}")
    
    return []

def extract_and_save_deadlines(db: Database, document_id: str, full_text: str):
    log = logger.bind(document_id=document_id)
    
    try:
        doc_oid = ObjectId(document_id)
        document = db.documents.find_one({"_id": doc_oid})
    except: return

    if not document: return

    # Normalize IDs
    case_id_str = str(document.get("case_id", ""))
    owner_id = document.get("owner_id")
    if isinstance(owner_id, str):
        try: owner_id = ObjectId(owner_id)
        except: pass

    # 1. Extract
    events = _extract_dates_with_llm(full_text)
    if not events:
        events = _extract_dates_with_regex(full_text[:5000])

    if not events:
        log.info("deadline_service.none_found")
        return

    # 2. Process & Save
    # Allow dates up to 30 days in the past (for recently uploaded active docs)
    cutoff_date = (datetime.now() - timedelta(days=30)).date()
    
    valid_events = []
    
    for item in events:
        raw_date = item.get("date_text", "")
        if not raw_date: continue
        
        # Preprocess Albanian months -> English
        clean_date_str = _preprocess_date_text(raw_date)
        
        parsed = dateparser.parse(
            clean_date_str, 
            settings={'DATE_ORDER': 'DMY', 'PREFER_DATES_FROM': 'future'}
        )
        
        if not parsed: continue
        
        # Filter too old
        if parsed.date() < cutoff_date: continue
        
        # Create Event
        valid_events.append({
            "case_id": case_id_str, # String for broad compatibility
            "owner_id": owner_id,
            "document_id": document_id,
            "title": item.get("title", "Afat Ligjor"),
            "description": f"{item.get('description', '')}\n(Burimi: {document.get('file_name')})",
            "start_date": parsed, # BSON Date
            "end_date": parsed,   # BSON Date
            "is_all_day": True,
            "event_type": "DEADLINE",
            "status": "PENDING",
            "priority": "HIGH",
            "created_at": datetime.now(timezone.utc)
        })

    if valid_events:
        # Delete old extracted deadlines for this doc to prevent duplicates on re-process
        db.calendar_events.delete_many({"document_id": document_id, "event_type": "DEADLINE"})
        db.calendar_events.insert_many(valid_events)
        log.info("deadline_service.saved", count=len(valid_events))