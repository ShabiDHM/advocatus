# FILE: backend/app/services/analysis_service.py
# PHOENIX PROTOCOL - HYBRID INTELLIGENCE (CLOUD + LOCAL FALLBACK)
# 1. TIER 1: Tries Groq (Cloud) for maximum precision.
# 2. TIER 2: Falls back to 'local-llm' (Ollama) if Groq is Rate Limited (429).
# 3. TIER 3: Returns Static Analysis if both fail (No Crashes).

import os
import json
import structlog
import httpx 
from typing import List, Dict, Any, Optional
from pymongo.database import Database
from bson import ObjectId
from groq import Groq

logger = structlog.get_logger(__name__)

# Configuration
LOCAL_LLM_URL = os.environ.get("LOCAL_LLM_URL", "http://local-llm:11434/api/chat")
LOCAL_MODEL_NAME = os.environ.get("LOCAL_MODEL_NAME", "llama3") # or 'mistral'

def _get_case_context(db: Database, case_id: str) -> str:
    try:
        documents = list(db.documents.find({"case_id": ObjectId(case_id)}))
        context_buffer = []
        
        for doc in documents:
            doc_id = str(doc["_id"])
            name = doc.get("file_name", "Unknown")
            summary = doc.get("summary", "No summary available.")
            
            findings = list(db.findings.find({"document_id": ObjectId(doc_id)}))
            findings_text = "\n".join([f"- {f.get('finding_text')}" for f in findings])
            
            deadlines = list(db.calendar_events.find({"document_id": doc_id}))
            deadlines_text = "\n".join([f"- {d.get('start_date')}: {d.get('title')}" for d in deadlines])

            doc_context = f"""
            === DOKUMENTI: {name} ===
            PËRMBLEDHJE: {summary}
            
            GJETJET KYÇE:
            {findings_text}
            
            AFATET/DATAT:
            {deadlines_text}
            ===========================
            """
            context_buffer.append(doc_context)
            
        return "\n\n".join(context_buffer)
    except Exception as e:
        logger.error("analysis.context_build_failed", error=str(e))
        return ""

def _generate_static_fallback(error_msg: str) -> Dict[str, Any]:
    """Tier 3: Returns a safe structure so the UI does not crash."""
    return {
        "summary_analysis": f"⚠️ Analiza e thellë AI nuk është e disponueshme për momentin (Kufizim Teknik: {error_msg}). Megjithatë, dokumentet tuaja janë të sigurta dhe të indeksuara.",
        "contradictions": ["Nuk u identifikuan automatikisht."],
        "risks": ["Ju lutemi rishikoni gjetjet manuale në panelin e dokumenteve."],
        "missing_info": ["Kontrolloni manualisht dosjen për elemente që mungojnë."]
    }

def _call_local_llm(system_prompt: str, user_prompt: str) -> Optional[Dict[str, Any]]:
    """Tier 2: Calls the internal Docker 'local-llm' service."""
    logger.info("🔄 Switching to LOCAL LLM (Ollama)...")
    try:
        payload = {
            "model": LOCAL_MODEL_NAME,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False,
            "format": "json" # Ollama supports native JSON enforcement
        }
        
        # Use sync call (or async if wrapped) - using httpx sync for simplicity here
        with httpx.Client(timeout=60.0) as client:
            response = client.post(LOCAL_LLM_URL, json=payload)
            response.raise_for_status()
            data = response.json()
            
            content = data.get("message", {}).get("content", "")
            return json.loads(content)
            
    except Exception as e:
        logger.error("analysis.local_llm_failed", error=str(e))
        return None

def cross_examine_case(db: Database, case_id: str) -> Dict[str, Any]:
    log = logger.bind(case_id=case_id)
    
    # 1. Prepare Context
    case_context = _get_case_context(db, case_id)
    if not case_context:
        return {"error": "Nuk ka mjaftueshëm të dhëna për analizë. Ngarkoni dokumente fillimisht."}

    # 2. Define Prompts
    system_prompt = """
    Ti je një Avokat i Lartë ("Senior Litigator").
    Analizo dosjen dhe përgjigju VETËM në format JSON:
    {
      "contradictions": ["list of strings"],
      "risks": ["list of strings"],
      "missing_info": ["list of strings"],
      "summary_analysis": "Përmbledhje e shkurtër"
    }
    Përgjigju në GJUHËN SHQIPE.
    """
    
    user_prompt = f"Analizo këtë dosje:\n{case_context[:20000]}"

    # --- TIER 1: GROQ (CLOUD) ---
    api_key = os.environ.get("GROQ_API_KEY")
    if api_key:
        try:
            client = Groq(api_key=api_key)
            completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model="llama-3.3-70b-versatile",
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            content = completion.choices[0].message.content
            if content:
                log.info("analysis.success_tier_1_groq")
                return json.loads(content)

        except Exception as e:
            error_str = str(e).lower()
            log.warning("analysis.groq_failed", error=error_str)
            
            # If it's NOT a rate limit (e.g. invalid key), maybe we shouldn't fallback?
            # But for robustness, we ALWAYS fallback if Tier 1 fails.
            pass
    else:
        log.warning("analysis.no_groq_key_configured")

    # --- TIER 2: LOCAL LLM (OLLAMA) ---
    local_result = _call_local_llm(system_prompt, user_prompt)
    if local_result:
        log.info("analysis.success_tier_2_local")
        # Mark as local generated
        local_result["summary_analysis"] = "[Generated by Local AI] " + local_result.get("summary_analysis", "")
        return local_result

    # --- TIER 3: STATIC FALLBACK (SAFETY NET) ---
    log.warning("analysis.all_tiers_failed_using_fallback")
    return _generate_static_fallback("Cloud & Local AI Unavailable")