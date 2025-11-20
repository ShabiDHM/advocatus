# FILE: backend/app/services/deadline_service.py
# PHOENIX PROTOCOL - DEADLINE EXTRACTION IMPLEMENTATION
# 1. IMPLEMENTED: Real LLM extraction via Groq (replacing the empty stub).
# 2. PARSING: Uses 'dateparser' to convert text dates to ISO format.
# 3. PERSISTENCE: Saves extracted items to 'calendar_events' collection.

import os
import json
import structlog
import dateparser
from datetime import datetime
from typing import List, Dict, Any
from bson import ObjectId
from pymongo.database import Database
from groq import Groq

logger = structlog.get_logger(__name__)

def _extract_dates_with_llm(full_text: str) -> List[Dict[str, str]]:
    """
    Uses Groq to extract deadlines from text.
    Returns a list of dicts: [{'title': '...', 'date': 'YYYY-MM-DD', 'description': '...'}]
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        logger.warning("deadline_service.no_api_key")
        return []

    client = Groq(api_key=api_key)
    
    # Truncate text if too long to fit context window
    truncated_text = full_text[:15000] 

    prompt = f"""
    Analyze the following legal text and identify strict deadlines, court dates, or expiry dates.
    Return ONLY a valid JSON array. Do not output any other text.
    
    JSON Structure:
    [
      {{
        "title": "Short title of the deadline (e.g. Appeal Submission)",
        "date_text": "The exact date string found in text",
        "description": "Context about this deadline"
      }}
    ]

    If no specific dates are found, return [].

    TEXT:
    {truncated_text}
    """

    try:
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a legal assistant extracting deadlines. Output JSON only."},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.1-70b-versatile", 
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        
        response_content = completion.choices[0].message.content
        if not response_content:
            return []

        # Parse JSON response
        data = json.loads(response_content)
        
        # Handle cases where LLM returns a wrapper object key like "deadlines": [...]
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, list):
                    return value
            return []
        
        if isinstance(data, list):
            return data
            
        return []

    except Exception as e:
        logger.error("deadline_service.llm_failure", error=str(e))
        return []

def extract_and_save_deadlines(db: Database, document_id: str, full_text: str):
    """
    Orchestrates the extraction and saving of deadlines as Calendar Events.
    """
    log = logger.bind(document_id=document_id)
    
    # 1. Verify Document
    try:
        doc_oid = ObjectId(document_id)
        document = db.documents.find_one({"_id": doc_oid})
    except Exception:
        log.error("deadline_service.invalid_id")
        return

    if not document or not full_text:
        log.warning("deadline_service.skipped", reason="No document or text")
        return

    case_id_str = str(document.get("case_id", ""))
    owner_id_str = str(document.get("owner_id", ""))

    # 2. Run Extraction
    log.info("deadline_service.starting_extraction")
    raw_deadlines = _extract_dates_with_llm(full_text)
    
    if not raw_deadlines:
        log.info("deadline_service.no_deadlines_found")
        return

    # 3. Process and Save
    events_to_insert = []
    
    for item in raw_deadlines:
        date_text = item.get("date_text", "")
        # Attempt to parse date
        parsed_date = dateparser.parse(date_text)
        
        if not parsed_date:
            continue

        # Construct Calendar Event
        event = {
            "case_id": case_id_str,
            "owner_id": owner_id_str, # Important for ownership permissions
            "document_id": document_id, # Link back to source doc
            "title": item.get("title", "Extracted Deadline"),
            "description": item.get("description", "") + f"\n\n(Source: {document.get('file_name', 'Document')})",
            "start_date": parsed_date.isoformat(),
            "end_date": parsed_date.isoformat(), # Deadlines are points in time
            "is_all_day": True,
            "event_type": "DEADLINE", # Matches Types.ts
            "priority": "HIGH",
            "status": "PENDING",
            "created_at": datetime.utcnow(),
            "location": "",
            "attendees": []
        }
        events_to_insert.append(event)

    if events_to_insert:
        result = db.calendar_events.insert_many(events_to_insert)
        log.info("deadline_service.saved", count=len(result.inserted_ids))
    else:
        log.info("deadline_service.completed_no_valid_dates")