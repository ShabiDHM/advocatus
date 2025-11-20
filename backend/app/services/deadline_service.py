# FILE: backend/app/services/deadline_service.py
# PHOENIX PROTOCOL - QUALITY UPGRADE
# 1. TITLES: Regex fallback now uses a clean static title, not random text snippets.
# 2. AI: Simplified prompt to increase success rate of meaningful titles.
# 3. DEDUPLICATION: Ensures only one event per date per document.

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
    cleaned = re.sub(r'^```json\s*', '', json_str, flags=re.MULTILINE)
    cleaned = re.sub(r'^```\s*', '', cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r'```\s*$', '', cleaned, flags=re.MULTILINE)
    return cleaned.strip()

def _extract_dates_with_regex(text: str) -> List[Dict[str, str]]:
    """
    Backup method: Finds dates.
    """
    matches = []
    # Regex capturing date AND surrounding context
    date_pattern = r'(.{0,30})\b(\d{1,2})\s+(Janar|Shkurt|Mars|Prill|Maj|Qershor|Korrik|Gusht|Shtator|Tetor|Nëntor|Dhjetor|January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b(.{0,30})'
    
    found = re.findall(date_pattern, text, re.IGNORECASE)
    for pre, day, month, year, post in found:
        date_str = f"{day} {month} {year}"
        
        matches.append({
            "title": "Afat i Gjetur (Automati)", # Clean title
            "date_text": date_str,
            "description": f"Konteksti: ...{pre.strip()} {date_str} {post.strip()}..."
        })
    return matches

def _extract_dates_with_llm(full_text: str) -> List[Dict[str, str]]:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key: return []

    client = Groq(api_key=api_key)
    truncated_text = full_text[:15000] 

    # PHOENIX FIX: Simplified prompt for better JSON compliance
    prompt = f"""
    Ti je asistent ligjor. Lexo tekstin dhe gjej datat ose afatet.
    Kthe vetëm JSON.
    
    Shembull:
    [
      {{
        "title": "Nënshkrimi i Kontratës",
        "date_text": "5 Nëntor 2025",
        "description": "Palët do të nënshkruajnë marrëveshjen."
      }}
    ]

    Teksti:
    {truncated_text}
    """

    try:
        completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-70b-versatile", 
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        
        content = _clean_json_string(completion.choices[0].message.content or "")
        data = json.loads(content)
        
        if isinstance(data, dict):
            for val in data.values():
                if isinstance(val, list): return val
            return []
        return data if isinstance(data, list) else []

    except Exception:
        return _extract_dates_with_regex(truncated_text)

def delete_deadlines_by_document_id(db: Database, document_id: str):
    try:
        db.calendar_events.delete_many({"document_id": document_id})
    except Exception:
        pass

def extract_and_save_deadlines(db: Database, document_id: str, full_text: str):
    log = logger.bind(document_id=document_id)
    
    try:
        doc_oid = ObjectId(document_id)
        document = db.documents.find_one({"_id": doc_oid})
    except Exception:
        return

    if not document or not full_text: return

    case_id_str = str(document.get("case_id", ""))
    owner_id = document.get("owner_id")
    if isinstance(owner_id, str):
        try: owner_id = ObjectId(owner_id)
        except: pass

    # 1. Extract
    raw_deadlines = _extract_dates_with_llm(full_text)
    if not raw_deadlines:
        raw_deadlines = _extract_dates_with_regex(full_text[:5000])

    if not raw_deadlines: return

    # 2. Deduplicate by Date
    unique_events = {}

    for item in raw_deadlines:
        date_text = item.get("date_text", "")
        if not date_text: continue

        parsed_date = dateparser.parse(date_text, languages=['sq', 'en'])
        if not parsed_date: continue
        
        iso_date = parsed_date.date().isoformat()

        # Use the title from the LLM if available, otherwise fallback
        title = item.get('title', "Afat Ligjor")
        if len(title) > 50: title = title[:47] + "..."

        if iso_date in unique_events:
             # If date exists, append info, don't duplicate
             unique_events[iso_date]["description"] += f"\n\n• {title}: {item.get('description', '')}"
        else:
            unique_events[iso_date] = {
                "case_id": case_id_str,
                "owner_id": owner_id,
                "document_id": document_id,
                "title": title,
                "description": item.get("description", "") + f"\n(Burimi: {document.get('file_name')})",
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

    # 3. Insert
    if unique_events:
        db.calendar_events.insert_many(list(unique_events.values()))
        log.info("deadline_service.success", count=len(unique_events))