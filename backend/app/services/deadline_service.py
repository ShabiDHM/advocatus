# FILE: backend/app/services/deadline_service.py
# PHOENIX PROTOCOL - HYBRID EXTRACTION (Cloud -> Local -> Regex)
# 1. TIER 1: Groq (High Precision).
# 2. TIER 2: Local Ollama (Fallback).
# 3. TIER 3: Regex Pattern Matching (Ultimate Safety Net).
# 4. FILTER: Ignores past dates.

import os
import json
import structlog
import dateparser
import re
import httpx
from datetime import datetime
from typing import List, Dict, Any
from bson import ObjectId
from pymongo.database import Database
from groq import Groq

logger = structlog.get_logger(__name__)

# --- CONFIGURATION ---
LOCAL_LLM_URL = os.environ.get("LOCAL_LLM_URL", "http://local-llm:11434/api/chat")
LOCAL_MODEL_NAME = "llama3"

def _clean_json_string(json_str: str) -> str:
    """Standardizes JSON string cleaning."""
    cleaned = re.sub(r'^```json\s*', '', json_str, flags=re.MULTILINE)
    cleaned = re.sub(r'^```\s*', '', cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r'```\s*$', '', cleaned, flags=re.MULTILINE)
    return cleaned.strip()

def _extract_dates_with_regex(text: str) -> List[Dict[str, str]]:
    """Tier 3: Mechanical extraction."""
    matches = []
    # Regex capturing date AND surrounding context (approx 30 chars)
    date_pattern = r'(.{0,30})\b(\d{1,2})\s+(Janar|Shkurt|Mars|Prill|Maj|Qershor|Korrik|Gusht|Shtator|Tetor|Nëntor|Dhjetor|January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b(.{0,30})'
    
    found = re.findall(date_pattern, text, re.IGNORECASE)
    for pre, day, month, year, post in found:
        date_str = f"{day} {month} {year}"
        matches.append({
            "title": "Afat i Gjetur",
            "date_text": date_str,
            "description": f"Konteksti: ...{pre.strip()} {date_str} {post.strip()}..."
        })
    return matches

def _call_local_llm(prompt: str) -> str:
    """Tier 2: Local AI extraction."""
    logger.info("🔄 Switching to LOCAL LLM for Deadlines...")
    try:
        payload = {
            "model": LOCAL_MODEL_NAME,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "format": "json" # Force JSON mode in Ollama
        }
        
        with httpx.Client(timeout=45.0) as client:
            response = client.post(LOCAL_LLM_URL, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("message", {}).get("content", "")
            
    except Exception as e:
        logger.warning(f"⚠️ Local LLM Failed: {e}")
        return ""

def _extract_dates_with_llm(full_text: str) -> List[Dict[str, str]]:
    truncated_text = full_text[:15000] 
    
    system_instruction = """
    Ti je asistent ligjor. Lexo tekstin dhe gjej datat ose afatet.
    Kthe vetëm JSON.
    Format: [{"title": "...", "date_text": "...", "description": "..."}]
    """
    
    prompt = f"{system_instruction}\n\nTeksti:\n{truncated_text}"

    # --- TIER 1: GROQ CLOUD ---
    api_key = os.environ.get("GROQ_API_KEY")
    if api_key:
        try:
            client = Groq(api_key=api_key)
            completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile", 
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            content = completion.choices[0].message.content or ""
            data = json.loads(_clean_json_string(content))
            
            # Normalize response structure
            if isinstance(data, dict):
                for val in data.values():
                    if isinstance(val, list): return val
                return []
            return data if isinstance(data, list) else []

        except Exception as e:
            logger.warning(f"⚠️ Groq Deadline Extraction Failed: {e}")
            # Fall through to Tier 2
    
    # --- TIER 2: LOCAL OLLAMA ---
    local_content = _call_local_llm(prompt)
    if local_content:
        try:
            data = json.loads(_clean_json_string(local_content))
            if isinstance(data, dict):
                for val in data.values():
                    if isinstance(val, list): return val
            if isinstance(data, list): return data
        except Exception:
            logger.warning("❌ Local LLM JSON Parse Failed.")

    # --- TIER 3: FALLBACK TO REGEX ---
    # Handled by caller if this returns empty
    return []

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

    # 1. Extract (Hybrid Strategy)
    raw_deadlines = _extract_dates_with_llm(full_text)
    
    # 2. Fallback to Regex if AI failed completely
    if not raw_deadlines:
        log.info("deadline_service.switching_to_regex")
        raw_deadlines = _extract_dates_with_regex(full_text[:5000])

    if not raw_deadlines: return

    unique_events = {}
    now_date = datetime.now().date() 

    for item in raw_deadlines:
        date_text = item.get("date_text", "")
        if not date_text: continue

        parsed_date = dateparser.parse(date_text, languages=['sq', 'en'])
        if not parsed_date: continue
        
        # PHOENIX FIX: Filter out past dates
        if parsed_date.date() < now_date:
            continue

        iso_date = parsed_date.date().isoformat()
        
        title = item.get('title', "Afat Ligjor")
        if len(title) > 50: title = title[:47] + "..."

        if iso_date in unique_events:
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

    if unique_events:
        db.calendar_events.insert_many(list(unique_events.values()))
        log.info("deadline_service.success", count=len(unique_events))