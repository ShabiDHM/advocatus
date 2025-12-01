# FILE: backend/app/services/deadline_service.py
# PHOENIX PROTOCOL - DEADLINE ENGINE V4.1
# 1. ENGINE: DeepSeek V3 (OpenRouter) for relative date calculation.
# 2. LOGIC: Smart filtering of past dates.
# 3. SAFETY: Regex Fallback for robustness.

import os
import json
import structlog
import dateparser
import re
import httpx
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from bson import ObjectId
from pymongo.database import Database
from openai import OpenAI # PHOENIX FIX: Standard client

logger = structlog.get_logger(__name__)

# --- CONFIGURATION ---
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY") 
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat" 

LOCAL_LLM_URL = os.environ.get("LOCAL_LLM_URL", "http://local-llm:11434/api/chat")
LOCAL_MODEL_NAME = "llama3"

def _clean_json_string(json_str: str) -> str:
    cleaned = re.sub(r'^```json\s*', '', json_str, flags=re.MULTILINE)
    cleaned = re.sub(r'^```\s*', '', cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r'```\s*$', '', cleaned, flags=re.MULTILINE)
    return cleaned.strip()

def _extract_dates_with_regex(text: str) -> List[Dict[str, str]]:
    matches = []
    # Regex capturing date AND surrounding context
    date_pattern = r'(.{0,30})\b(\d{1,2})\s+(Janar|Shkurt|Mars|Prill|Maj|Qershor|Korrik|Gusht|Shtator|Tetor|Nëntor|Dhjetor|January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b(.{0,30})'
    
    found = re.findall(date_pattern, text, re.IGNORECASE)
    for pre, day, month, year, post in found:
        date_str = f"{day} {month} {year}"
        matches.append({
            "title": "Afat i Gjetur (Regex)",
            "date_text": date_str,
            "description": f"Konteksti: ...{pre.strip()} {date_str} {post.strip()}..."
        })
    return matches

def _call_local_llm(prompt: str) -> str:
    try:
        payload = {
            "model": LOCAL_MODEL_NAME,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "format": "json"
        }
        with httpx.Client(timeout=45.0) as client:
            response = client.post(LOCAL_LLM_URL, json=payload)
            data = response.json()
            return data.get("message", {}).get("content", "")
    except Exception as e:
        logger.warning(f"⚠️ Local LLM Failed: {e}")
        return ""

def _extract_dates_with_llm(full_text: str) -> List[Dict[str, str]]:
    # Truncate text to avoid massive token usage on huge docs
    truncated_text = full_text[:20000] 
    
    current_date = datetime.now().strftime("%d %B %Y")
    
    system_prompt = f"""
    Ti je një Asistent Ligjor i përpiktë (Legal Clerk).
    DATA E SOTME: {current_date}.
    
    DETYRA:
    Identifiko çdo AFAT, DATË SEANCE, ose DATË SKADENCE në tekst.
    
    RREGULLAT:
    1. Nëse data është relative (p.sh., "15 ditë nga sot"), llogarite atë duke u bazuar tek DATA E SOTME.
    2. Injoro datat historike (të kaluara) përveç nëse janë relevante për kontekstin.
    3. Përshkruaj qartë se për çfarë është afati.

    FORMATI JSON STRIKT:
    [
      {{
        "title": "Titull i shkurtër (p.sh. Seancë Gjyqësore)",
        "date_text": "DD/MM/YYYY",
        "description": "Detaje shtesë nga teksti..."
      }}
    ]
    """

    # --- TIER 1: OPENROUTER / DEEPSEEK ---
    if DEEPSEEK_API_KEY:
        try:
            client = OpenAI(
                api_key=DEEPSEEK_API_KEY,
                base_url=OPENROUTER_BASE_URL
            )
            
            response = client.chat.completions.create(
                model=OPENROUTER_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"TEKSTI I DOKUMENTIT:\n{truncated_text}"}
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
                extra_headers={
                    "HTTP-Referer": "https://juristi.tech", 
                    "X-Title": "Juristi AI Deadlines"
                }
            )
            
            content = response.choices[0].message.content or ""
            data = json.loads(_clean_json_string(content))
            
            # Normalize structure
            if isinstance(data, dict):
                # Sometimes LLM wraps it in {"deadlines": [...]}
                for val in data.values():
                    if isinstance(val, list): return val
                return []
            
            return data if isinstance(data, list) else []

        except Exception as e:
            logger.warning(f"⚠️ DeepSeek Extraction Failed: {e}")
            # Fall through to Tier 2

    # --- TIER 2: LOCAL OLLAMA ---
    local_prompt = f"{system_prompt}\n\nTEKSTI:\n{truncated_text}"
    local_content = _call_local_llm(local_prompt)
    if local_content:
        try:
            data = json.loads(_clean_json_string(local_content))
            if isinstance(data, dict):
                for val in data.values():
                    if isinstance(val, list): return val
            if isinstance(data, list): return data
        except Exception:
            pass

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
    
    # 2. Fallback to Regex if AI found nothing
    if not raw_deadlines:
        log.info("deadline_service.switching_to_regex")
        raw_deadlines = _extract_dates_with_regex(full_text[:5000])

    if not raw_deadlines: return

    unique_events = {}
    
    # PHOENIX FIX: Filter past dates
    now_date = datetime.now().date() 

    for item in raw_deadlines:
        date_text = item.get("date_text", "")
        if not date_text: continue

        parsed_date = dateparser.parse(date_text, languages=['sq', 'en'])
        if not parsed_date: continue
        
        # Only future/today events
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
                "created_at": datetime.now(timezone.utc),
                "location": "",
                "attendees": []
            }

    if unique_events:
        db.calendar_events.insert_many(list(unique_events.values()))
        log.info("deadline_service.success", count=len(unique_events))