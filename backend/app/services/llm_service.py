# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - INTELLIGENCE V8.0 (CITATION ENGINE)
# 1. CITATION LOGIC: Prompts now strictly demand "page_ref" (Faqja X) based on text markers.
# 2. ACCURACY: Retained Financial Audit logic (200 vs 250 Euro).
# 3. REPAIR: Retained 'Paditësja' fix.

import os
import json
import logging
import httpx
import re
from typing import List, Dict, Any, Optional
from openai import OpenAI 

logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat"

# Local LLM (Ollama) - The "Eco" Engine
OLLAMA_URL = os.environ.get("LOCAL_LLM_URL", "http://local-llm:11434/api/generate")
LOCAL_MODEL_NAME = "llama3"

# --- CLIENT INITIALIZATION ---
_deepseek_client: Optional[OpenAI] = None

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

# --- HELPER: ALBANIAN TEXT REPAIR ---
def repair_albanian_text(text: str) -> str:
    if not text: return ""
    replacements = {
        "Paditésja": "Paditësja", "paditésja": "paditësja",
        "Paditési": "Paditësi", "paditési": "paditësi",
        "Përshéndetje": "Përshëndetje", "përshéndetje": "përshëndetje",
        "çështje": "çështje", "Çështje": "Çështje"
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)
    text = re.sub(r'ésja\b', 'ësja', text)
    text = re.sub(r'ésit\b', 'ësit', text)
    text = re.sub(r'éses\b', 'ëses', text)
    return text

def _parse_json_safely(content: str) -> Dict[str, Any]:
    content = repair_albanian_text(content)
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
            "temperature": 0.0, 
            "extra_headers": {"HTTP-Referer": "https://juristi.tech", "X-Title": "Juristi AI Analysis"}
        }
        if json_mode: kwargs["response_format"] = {"type": "json_object"}
        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message.content
    except Exception as e:
        logger.warning(f"⚠️ DeepSeek Call Failed: {e}")
        return None

def _call_local_llm(prompt: str, json_mode: bool = False) -> str:
    try:
        payload = {
            "model": LOCAL_MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.0, "num_ctx": 4096},
            "format": "json" if json_mode else None
        }
        with httpx.Client(timeout=45.0) as client:
            response = client.post(OLLAMA_URL, json=payload)
            return response.json().get("response", "")
    except Exception:
        return ""

# --- STRATEGIC TASKS ---

def generate_summary(text: str) -> str:
    truncated_text = text[:20000] 
    system_prompt = (
        "Ti je Analist Gjyqësor për Republikën e Kosovës. "
        "Detyra: Krijoni një përmbledhje faktike. "
        "CITIMI: Nëse teksti përmban markera si '[[FAQJA X]]', referoju atyre kur përmend fakte kritike."
    )
    user_prompt = f"DOKUMENTI:\n{truncated_text}"
    
    res = _call_local_llm(f"{system_prompt}\n\n{user_prompt}")
    if not res or len(res) < 50:
        res = _call_deepseek(system_prompt, user_prompt)
        
    return repair_albanian_text(res or "Përmbledhja e padisponueshme.")

def extract_findings_from_text(text: str) -> List[Dict[str, Any]]:
    truncated_text = text[:25000]
    
    # PHOENIX V8.0: ADDED 'page_ref' REQUIREMENT
    system_prompt = """
    Ti je Motor i Nxjerrjes së Provave (Evidence Engine).
    
    DETYRA: Gjej elementet kyçe dhe TREGO KU GJENDEN.
    
    INSTRUKSIONE PËR CITIM:
    1. Shiko tekstin për markera faqesh (psh. "--- [FAQJA 2] ---").
    2. Për çdo gjetje, identifiko numrin e faqes më të afërt lart.
    3. Nëse nuk ka numër faqeje, shkruaj "N/A".
    
    FORMATI JSON (STRIKT):
    {
      "findings": [
        {
          "finding_text": "Paditësja kërkon 250 Euro.",
          "source_text": "Kërkojmë që shuma... të rritet në 250 euro.",
          "category": "CLAIM",
          "page_ref": "Faqja 3" 
        }
      ]
    }
    """
    user_prompt = f"DOSJA:\n{truncated_text}"

    content = _call_deepseek(system_prompt, user_prompt, json_mode=True)
    if not content:
        content = _call_local_llm(f"{system_prompt}\n\n{user_prompt}", json_mode=True)
    
    if content:
        data = _parse_json_safely(content)
        return data.get("findings", [])
    return []

def extract_graph_data(text: str) -> Dict[str, List[Dict]]:
    truncated_text = text[:15000]
    system_prompt = """
    Ti je Inxhinier i Grafit Ligjor. Krijo hartën e marrëdhënieve.
    FORMATI JSON STRIKT:
    {"entities": [{"id": "...", "name": "...", "group": "..."}], "relations": [{"source": "...", "target": "...", "label": "..."}]}
    """
    user_prompt = f"TEKSTI:\n{truncated_text}"
    content = _call_local_llm(f"{system_prompt}\n\n{user_prompt}", json_mode=True)
    if not content:
        content = _call_deepseek(system_prompt, user_prompt, json_mode=True)
    if content: return _parse_json_safely(content)
    return {"entities": [], "relations": []}

def analyze_case_contradictions(text: str) -> Dict[str, Any]:
    truncated_text = text[:25000]
    
    # PHOENIX V8.0: AUDIT + CITATION
    system_prompt = """
    Ti je Gjyqtar i Debatit Ligjor.
    
    DETYRA: Analizo rastin dhe CITO BURIMET.
    
    UDHËZIME:
    1. Identifiko saktë shumat (200 vs 250 Euro).
    2. Për çdo 'Provë Kyçe', trego në kllapa se ku gjendet (psh. [Faqja 2]).
    
    FORMATI JSON (STRIKT):
    {
        "summary_analysis": "...",
        "conflicting_parties": [{"party_name": "...", "core_claim": "..."}],
        "contradictions": ["..."],
        "key_evidence": ["Aktgjykimi i vjetër (Faqja 2)", "Raportet mjekësore (Faqja 3)"],
        "missing_info": ["..."]
    }
    """
    user_prompt = f"DOSJA:\n{truncated_text}"

    content = _call_deepseek(system_prompt, user_prompt, json_mode=True)
    if not content:
        content = _call_local_llm(f"{system_prompt}\n\n{user_prompt}", json_mode=True)

    if content: return _parse_json_safely(content)
    return {}

def generate_socratic_response(socratic_context: List[Dict], question: str) -> Dict:
    return {"answer": "Logic moved to R-A-G Service.", "sources": []}

def extract_deadlines_from_text(text: str) -> List[Dict[str, Any]]:
    return []