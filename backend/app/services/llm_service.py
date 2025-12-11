# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - INTELLIGENCE V8.1 (LOGIC FIX)
# 1. LOGIC: Strict distinction between "Request" (Padi) and "Decision" (Aktgjykim).
# 2. ACCURACY: Explicit rule against hallucinating numbers or future dates.
# 3. ARCHITECTURE: Keeps existing Local/DeepSeek fallback strategy.

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

# Local LLM (Ollama)
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
    return text

def _parse_json_safely(content: str) -> Dict[str, Any]:
    content = repair_albanian_text(content)
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # Try to find JSON block if wrapped in markdown
        match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
        if match:
            try: return json.loads(match.group(1))
            except: pass
        # Try raw bracket finding
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
            "temperature": 0.0, # ZERO CREATIVITY = HIGHEST ACCURACY
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
        "KUJDES: Nëse dokumenti është 'Padi', çdo gjë që kërkohet është 'Pretendim', jo 'Vendim'."
    )
    user_prompt = f"DOKUMENTI:\n{truncated_text}"
    
    res = _call_local_llm(f"{system_prompt}\n\n{user_prompt}")
    if not res or len(res) < 50:
        res = _call_deepseek(system_prompt, user_prompt)
        
    return repair_albanian_text(res or "Përmbledhja e padisponueshme.")

def extract_findings_from_text(text: str) -> List[Dict[str, Any]]:
    """
    Extracts structured findings (facts, claims, decisions) from legal text.
    """
    truncated_text = text[:25000]
    
    # PHOENIX V8.1: STRICT LOGIC PROMPT
    system_prompt = """
    Ti je Motor i Nxjerrjes së Provave (Evidence Engine) për Kosovën.
    
    RREGULLAT STRIKTE TË LOGJIKËS (KRITIKE):
    1. **DALLIMI "KËRKESË" vs "VENDIM":**
       - Nëse dokumenti është **PADI** (Lawsuit), çdo gjë e shkruar nën "AKTGJYKIM" ose "PETITIUM" është vetëm **KËRKESË** e paditësit. 
       - **KUJDES:** MOS thuaj "Gjykata ka vendosur". Thuaj "Paditësi kërkon që Gjykata të vendosë".
       - Vetëm nëse dokumenti është vërtet "Aktgjykim" (i nënshkruar nga Gjyqtari), atëherë përdor termin "Gjykata ka vendosur".

    2. **SAKTËSIA NUMERIKE:**
       - Kopjo shumat e parave (Euro) SAKTËSISHT siç janë në tekst. Mos bëj llogaritje.
       - Nëse shkruan 200 ose 250, mos shkruaj numra të tjerë (si 280).
    
    3. **DATAT:**
       - Cito vetëm datat që shihen në tekst. Mos parashiko të ardhmen.

    FORMATI JSON (STRIKT):
    {
      "findings": [
        {
          "finding_text": "Përshkrimi i saktë (psh: Paditësja kërkon rritjen e alimentacionit...)",
          "source_text": "Cito fjalinë ekzakte nga teksti",
          "category": "CLAIM" (për Padi) ose "DECISION" (për Aktgjykim),
          "page_number": 1
        }
      ]
    }
    """
    user_prompt = f"ANALIZO KËTË DOKUMENT:\n{truncated_text}"

    # Priority: DeepSeek (Smarter) -> Local (Fallback)
    content = _call_deepseek(system_prompt, user_prompt, json_mode=True)
    if not content:
        content = _call_local_llm(f"{system_prompt}\n\n{user_prompt}", json_mode=True)
    
    if content:
        data = _parse_json_safely(content)
        # Handle various return formats
        if "findings" in data: return data["findings"]
        if isinstance(data, list): return data
    
    return []

def extract_graph_data(text: str) -> Dict[str, List[Dict]]:
    truncated_text = text[:15000]
    system_prompt = """
    Ti je Inxhinier i Grafit Ligjor. Krijo hartën e marrëdhënieve.
    FORMATI JSON: {"entities": [{"id": "...", "name": "...", "group": "..."}], "relations": [{"source": "...", "target": "...", "label": "..."}]}
    """
    user_prompt = f"TEKSTI:\n{truncated_text}"
    content = _call_local_llm(f"{system_prompt}\n\n{user_prompt}", json_mode=True)
    if not content:
        content = _call_deepseek(system_prompt, user_prompt, json_mode=True)
    if content: return _parse_json_safely(content)
    return {"entities": [], "relations": []}

def analyze_case_contradictions(text: str) -> Dict[str, Any]:
    truncated_text = text[:25000]
    
    # PHOENIX V8.1: AUDIT MODE
    system_prompt = """
    Ti je Gjyqtar i Debatit Ligjor (Audit Mode).
    
    DETYRA: Analizo rastin për kontradikta dhe rreziqe.
    
    RREGULLI I ARTË:
    - Mos ngatërro 'Kërkesën e Paditësit' me 'Vendimin e Gjykatës'. 
    - Nëse është PADI, thuaj qartë: "Kjo është vetëm kërkesë, ende nuk ka vendim."
    
    FORMATI JSON (STRIKT):
    {
        "summary_analysis": "...",
        "conflicting_parties": [{"party_name": "...", "core_claim": "..."}],
        "contradictions": ["..."],
        "key_evidence": ["Aktgjykimi i vjetër C.nr.73/2010", "Raportet mjekësore"],
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