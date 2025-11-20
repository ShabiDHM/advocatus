# FILE: backend/app/services/deadline_service.py
# PHOENIX PROTOCOL - SYNTAX FIX
# 1. FIXED: Replaced JavaScript '||' with Python 'or'.
# 2. LOGIC: Ensured robust return paths.

import os
import json
import structlog
import dateparser
import re
from datetime import datetime
from typing import List, Dict, Any
from bson import ObjectId
from pymongo.database import Database
from groq import Groq

logger = structlog.get_logger(__name__)

def _clean_json_string(json_str: str) -> str:
    # Remove ```json and ``` wrappers
    cleaned = re.sub(r'^```json\s*', '', json_str, flags=re.MULTILINE)
    cleaned = re.sub(r'^```\s*', '', cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r'```\s*$', '', cleaned, flags=re.MULTILINE)
    return cleaned.strip()

def _extract_dates_with_regex(text: str) -> List[Dict[str, str]]:
    """Backup method: simple regex to find things looking like dates."""
    matches = []
    # Simple pattern for "DD Month YYYY" in Albanian/English
    date_pattern = r'\b(\d{1,2})\s+(Janar|Shkurt|Mars|Prill|Maj|Qershor|Korrik|Gusht|Shtator|Tetor|Nëntor|Dhjetor|January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b'
    
    found = re.findall(date_pattern, text, re.IGNORECASE)
    for day, month, year in found:
        date_str = f"{day} {month} {year}"
        matches.append({
            "title": "Afat i Gjetur (Regex)",
            "date_text": date_str,
            "description": f"U gjet data: {date_str}"
        })
    return matches

def _extract_dates_with_llm(full_text: str) -> List[Dict[str, str]]:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        logger.warning("deadline_service.no_api_key")
        return []

    client = Groq(api_key=api_key)
    truncated_text = full_text[:15000] 

    prompt = f"""
    Analyze the following legal text and identify strict deadlines.
    Return ONLY a valid JSON array. 
    
    [
      {{
        "title": "Deadline Title",
        "date_text": "DD Month YYYY",
        "description": "Brief context"
      }}
    ]

    TEXT:
    {truncated_text}
    """

    try:
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a legal assistant. Output JSON only."},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.1-70b-versatile", 
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        
        response_content = completion.choices[0].message.content
        # FIX: Changed '||' to 'or'
        cleaned_content = _clean_json_string(response_content or "")
        
        try:
            data = json.loads(cleaned_content)
            # Handle wrapper keys
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, list): return value
                return []
            if isinstance(data, list): return data
        except json.JSONDecodeError:
            logger.warning("deadline_service.json_failed_trying_regex")
            return _extract_dates_with_regex(response_content or "")

        return []

    except Exception as e:
        logger.error("deadline_service.llm_failure", error=str(e))
        return _extract_dates_with_regex(truncated_text)

def extract_and_save_deadlines(db: Database, document_id: str, full_text: str):
    log = logger.bind(document_id=document_id)
    
    try:
        doc_oid = ObjectId(document_id)
        document = db.documents.find_one({"_id": doc_oid})
    except Exception:
        return

    if not document or not full_text:
        return

    case_id_str = str(document.get("case_id", ""))
    owner_id_str = str(document.get("owner_id", ""))

    log.info("deadline_service.starting")
    
    raw_deadlines = _extract_dates_with_llm(full_text)
    
    if not raw_deadlines:
        log.info("deadline_service.llm_empty_trying_regex")
        raw_deadlines = _extract_dates_with_regex(full_text[:5000])

    if not raw_deadlines:
        log.info("deadline_service.nothing_found")
        return

    events_to_insert = []
    
    for item in raw_deadlines:
        date_text = item.get("date_text", "")
        if not date_text: continue

        parsed_date = dateparser.parse(date_text, languages=['sq', 'en'])
        
        if not parsed_date:
            continue

        event = {
            "case_id": case_id_str,
            "owner_id": owner_id_str,
            "document_id": document_id,
            "title": item.get("title", "Afat i Nxjerrë"),
            "description": item.get("description", "") + f"\n\n(Burimi: {document.get('file_name', 'Document')})",
            "start_date": parsed_date.isoformat(),
            "end_date": parsed_date.isoformat(),
            "is_all_day": True,
            "event_type": "DEADLINE",
            "priority": "HIGH",
            "status": "PENDING",
            "created_at": datetime.utcnow(),
            "location": "",
            "attendees": []
        }
        events_to_insert.append(event)

    if events_to_insert:
        result = db.calendar_events.insert_many(events_to_insert)
        log.info("deadline_service.success", count=len(result.inserted_ids))