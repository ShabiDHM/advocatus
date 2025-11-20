# FILE: backend/app/services/deadline_service.py
# PHOENIX PROTOCOL - DEADLINE SERVICE (ROBUST JSON & LOCALIZATION FIX)
# 1. PARSING FIX: Strips Markdown code blocks (```json) from LLM response.
# 2. LOCALIZATION: Configures dateparser to explicitly handle Albanian ('sq').
# 3. LOGGING: Added detailed logs to debug extraction counts.

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
    """
    Removes Markdown code blocks and extra whitespace from LLM response.
    """
    # Remove ```json and ``` wrappers
    cleaned = re.sub(r'^```json\s*', '', json_str, flags=re.MULTILINE)
    cleaned = re.sub(r'^```\s*', '', cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r'```\s*$', '', cleaned, flags=re.MULTILINE)
    return cleaned.strip()

def _extract_dates_with_llm(full_text: str) -> List[Dict[str, str]]:
    """
    Uses Groq to extract deadlines. Handles Markdown stripping and JSON parsing.
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        logger.warning("deadline_service.no_api_key")
        return []

    client = Groq(api_key=api_key)
    
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

        # PHOENIX FIX: Clean the string before parsing
        cleaned_content = _clean_json_string(response_content)
        
        try:
            data = json.loads(cleaned_content)
        except json.JSONDecodeError as e:
            logger.error("deadline_service.json_parse_error", content=cleaned_content[:100], error=str(e))
            return []
        
        # Handle wrapper keys like {"deadlines": [...]}
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
    Orchestrates extraction and saving.
    """
    log = logger.bind(document_id=document_id)
    
    try:
        doc_oid = ObjectId(document_id)
        document = db.documents.find_one({"_id": doc_oid})
    except Exception:
        log.error("deadline_service.invalid_id")
        return

    if not document or not full_text:
        log.warning("deadline_service.skipped")
        return

    case_id_str = str(document.get("case_id", ""))
    owner_id_str = str(document.get("owner_id", ""))

    log.info("deadline_service.starting_extraction")
    raw_deadlines = _extract_dates_with_llm(full_text)
    
    if not raw_deadlines:
        log.info("deadline_service.no_deadlines_found")
        return

    events_to_insert = []
    
    for item in raw_deadlines:
        date_text = item.get("date_text", "")
        if not date_text: continue

        # PHOENIX FIX: Explicitly handle Albanian and English
        parsed_date = dateparser.parse(date_text, languages=['sq', 'en'])
        
        if not parsed_date:
            log.warning("deadline_service.date_parse_failed", date_text=date_text)
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
    else:
        log.info("deadline_service.completed_no_valid_dates")