# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - INTELLIGENCE V8.2 (ANTI-HALLUCINATION NUCLEAR MODE)
# 1. LOGIC: Explicit "Padi vs Aktgjykim" classifier.
# 2. RULE: If document contains "Paditës" at the top, ignore "Aktgjykim" at the bottom.
# 3. SAFETY: Forces 0.0 temperature for maximum robotic strictness.

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
OLLAMA_URL = os.environ.get("LOCAL_LLM_URL", "http://local-llm:11434/api/generate")
LOCAL_MODEL_NAME = "llama3"

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

def repair_albanian_text(text: str) -> str:
    if not text: return ""
    replacements = {
        "Paditésja": "Paditësja", "paditésja": "paditësja",
        "Paditési": "Paditësi", "paditési": "paditësi"
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)
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

def _call_deepseek(system_prompt: str, user_prompt: str, json_mode: bool = False) -> Optional[str]:
    client = get_deepseek_client()
    if not client: return None
    try:
        kwargs = {
            "model": OPENROUTER_MODEL,
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            "temperature": 0.0, 
            "extra_headers": {"HTTP-Referer": "https://juristi.tech", "X-Title": "Juristi AI"}
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
    except Exception: return ""

def generate_summary(text: str) -> str:
    truncated_text = text[:20000] 
    system_prompt = "Ti je Analist Ligjor. Krijo një përmbledhje të shkurtër faktike."
    user_prompt = f"DOKUMENTI:\n{truncated_text}"
    res = _call_local_llm(f"{system_prompt}\n\n{user_prompt}")
    if not res or len(res) < 50: res = _call_deepseek(system_prompt, user_prompt)
    return repair_albanian_text(res or "N/A")

def extract_findings_from_text(text: str) -> List[Dict[str, Any]]:
    truncated_text = text[:25000]
    
    # --- NUCLEAR OPTION PROMPT ---
    system_prompt = """
    Ti je Motor i Nxjerrjes së Provave.
    
    RREGULLI KRYESOR (SHUMË E RËNDËSISHME):
    1. **Identifiko Llojin e Dokumentit:**
       - Nëse dokumenti ka fjalën "PADI" në fillim -> Ky dokument është KËRKESË.
       - Nëse dokumenti ka "AKTGJYKIM" në fund (pas tekstit "Propozoj"), kjo është vetëm çfarë kërkon paditësi, NUK është vendim i gjykatës.
    
    2. **Logjika e Nxjerrjes:**
       - Nëse është PADI: Çdo fjali si "Gjykata të vendosë..." duhet të regjistrohet si "Paditësi KËRKON...".
       - MOS thuaj "Gjykata ka vendosur" nëse dokumenti është Padi.
    
    FORMATI JSON:
    {
      "findings": [
        {
          "finding_text": "Paditësi kërkon rritjen e alimentacionit në 250 Euro.",
          "source_text": "Kërkojmë që shuma... të rritet në 250 euro.",
          "category": "KËRKESË", 
          "page_number": 1
        }
      ]
    }
    """
    user_prompt = f"ANALIZO KËTË DOKUMENT:\n{truncated_text}"

    content = _call_deepseek(system_prompt, user_prompt, json_mode=True)
    if not content: content = _call_local_llm(f"{system_prompt}\n\n{user_prompt}", json_mode=True)
    
    if content:
        data = _parse_json_safely(content)
        if "findings" in data: return data["findings"]
        if isinstance(data, list): return data
    return []

def extract_graph_data(text: str) -> Dict[str, List[Dict]]:
    return {"entities": [], "relations": []}

def analyze_case_contradictions(text: str) -> Dict[str, Any]:
    truncated_text = text[:25000]
    
    # --- NUCLEAR ANALYST PROMPT ---
    system_prompt = """
    Ti je Gjyqtar i Debatit Ligjor (Audit Mode).
    
    DETYRA KRITIKE:
    1. Lexo fillimin e dokumentit. Nëse shkruan "PADI", atëherë i gjithë dokumenti është njëanshëm (vetëm pretendimet e Paditësit).
    2. **KUJDES:** Në fund të Padisë shpesh shkruhet "AKTGJYKIM" si propozim. MOS E KONSIDERO SI VENDIM.
    3. Kur analizon, thuaj qartë: "Paditësi pretendon..." ose "Paditësi kërkon...". MOS thuaj "Gjykata vendosi".
    
    FORMATI JSON (STRIKT):
    {
        "document_type": "PADI (Kërkesë) apo AKTGJYKIM (Vendim)?",
        "summary_analysis": "Përmbledhje e saktë duke dalluar kërkesën nga vendimi.",
        "conflicting_parties": [{"party_name": "...", "core_claim": "..."}],
        "contradictions": ["..."],
        "key_evidence": ["..."],
        "missing_info": ["..."]
    }
    """
    user_prompt = f"DOSJA:\n{truncated_text}"

    content = _call_deepseek(system_prompt, user_prompt, json_mode=True)
    if not content: content = _call_local_llm(f"{system_prompt}\n\n{user_prompt}", json_mode=True)

    if content: return _parse_json_safely(content)
    return {}

def generate_socratic_response(socratic_context: List[Dict], question: str) -> Dict:
    return {}
def extract_deadlines_from_text(text: str) -> List[Dict[str, Any]]:
    return []