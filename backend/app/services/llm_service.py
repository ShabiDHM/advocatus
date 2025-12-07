# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - CLEANUP
# 1. REMOVED: 'generate_text' (AI Scan feature deprecated).
# 2. STATUS: Reverted to core analysis functions only.

import os
import json
import logging
import httpx
import re
from typing import List, Dict, Any, Optional
from openai import OpenAI # For DeepSeek/OpenRouter
from groq import Groq

logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat"

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL_NAME = "llama-3.3-70b-versatile" 

OLLAMA_URL = os.environ.get("LOCAL_LLM_URL", "http://local-llm:11434/api/generate")
LOCAL_MODEL_NAME = "llama3"

# --- CLIENT INITIALIZATION ---
_deepseek_client: Optional[OpenAI] = None
_groq_client: Optional[Groq] = None

def get_deepseek_client() -> Optional[OpenAI]:
    global _deepseek_client
    if _deepseek_client: return _deepseek_client
    if DEEPSEEK_API_KEY:
        try:
            _deepseek_client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=OPENROUTER_BASE_URL)
            return _deepseek_client
        except Exception as e:
            logger.error(f"DeepSeek Init Failed: {e}")
    return None

def get_groq_client() -> Optional[Groq]:
    global _groq_client
    if _groq_client: return _groq_client
    if GROQ_API_KEY:
        try:
            _groq_client = Groq(api_key=GROQ_API_KEY)
            return _groq_client
        except Exception as e:
            logger.error(f"Groq Init Failed: {e}")
    return None

# --- HELPER: ROBUST JSON PARSER ---
def _parse_json_safely(content: str) -> Dict[str, Any]:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
        if match:
            try: return json.loads(match.group(1))
            except: pass
        start, end = content.find('{'), content.rfind('}')
        if start != -1 and end != -1:
            try: return json.loads(content[start:end+1])
            except: pass
        return {}

# --- EXECUTION ENGINES ---

def _call_deepseek(system_prompt: str, user_prompt: str, json_mode: bool = False) -> Optional[str]:
    client = get_deepseek_client()
    if not client: return None
    try:
        kwargs = {
            "model": OPENROUTER_MODEL,
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            "temperature": 0.1,
            "extra_headers": {"HTTP-Referer": "https://juristi.tech", "X-Title": "Juristi AI"}
        }
        if json_mode: kwargs["response_format"] = {"type": "json_object"}
        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message.content
    except Exception as e:
        logger.warning(f"⚠️ DeepSeek Call Failed: {e}")
        return None

def _call_groq(system_prompt: str, user_prompt: str, json_mode: bool = False) -> Optional[str]:
    client = get_groq_client()
    if not client: return None
    try:
        kwargs = {
            "model": GROQ_MODEL_NAME,
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            "temperature": 0.1,
        }
        if json_mode: kwargs["response_format"] = {"type": "json_object"}
        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message.content
    except Exception as e:
        logger.warning(f"⚠️ Groq Call Failed: {e}")
        return None

def _call_local_llm(prompt: str, json_mode: bool = False) -> str:
    logger.info(f"🔄 Switching to LOCAL LLM ({LOCAL_MODEL_NAME})...")
    try:
        payload = {
            "model": LOCAL_MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_ctx": 4096},
            "format": "json" if json_mode else None
        }
        with httpx.Client(timeout=60.0) as client:
            response = client.post(OLLAMA_URL, json=payload)
            return response.json().get("response", "")
    except Exception:
        return ""

# --- CORE SERVICES ---

def generate_summary(text: str) -> str:
    truncated_text = text[:15000]
    system_prompt = "You are a professional legal assistant. Summarize this document in 1 paragraph (Albanian)."
    user_prompt = f"DOCUMENT:\n{truncated_text}"
    
    res = _call_deepseek(system_prompt, user_prompt)
    if res: return res
    res = _call_groq(system_prompt, user_prompt)
    if res: return res
    return _call_local_llm(f"{system_prompt}\n\n{user_prompt}") or "Përmbledhja e padisponueshme."

def extract_findings_from_text(text: str) -> List[Dict[str, Any]]:
    truncated_text = text[:15000]
    system_prompt = "Extract key legal findings (Dates, Amounts, Obligations). Return JSON: {\"findings\": [{\"finding_text\": \"...\", \"source_text\": \"...\"}]}"
    user_prompt = f"TEXT:\n{truncated_text}"

    content = _call_deepseek(system_prompt, user_prompt, json_mode=True)
    if content: return _parse_json_safely(content).get("findings", [])
    
    content = _call_groq(system_prompt, user_prompt, json_mode=True)
    if content: return _parse_json_safely(content).get("findings", [])
    
    content = _call_local_llm(f"{system_prompt}\n\n{user_prompt}", json_mode=True)
    if content: return _parse_json_safely(content).get("findings", [])
    return []

def extract_graph_data(text: str) -> Dict[str, List[Dict]]:
    truncated_text = text[:10000]
    system_prompt = "Extract entities and relationships. Return JSON: {\"entities\": [], \"relations\": []}"
    user_prompt = f"TEXT:\n{truncated_text}"
    
    content = _call_deepseek(system_prompt, user_prompt, json_mode=True)
    if content: return _parse_json_safely(content)
    
    content = _call_groq(system_prompt, user_prompt, json_mode=True)
    if content: return _parse_json_safely(content)
    return {"entities": [], "relations": []}

def generate_socratic_response(socratic_context: List[Dict], question: str) -> Dict:
    return {"answer": "Logic moved to RAG Service.", "sources": []}

def extract_deadlines_from_text(text: str) -> List[Dict[str, Any]]:
    return []