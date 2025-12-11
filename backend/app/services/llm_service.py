# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - MASTER INTELLIGENCE V6.1 (FULL PROMPTS + ECO-MODE)
# 1. ARCHITECTURE: Groq removed. DeepSeek (Cloud) + Ollama (Local).
# 2. ECO-MODE: Summaries/Graphs use Local LLM first to save costs.
# 3. QUALITY: Findings/Analysis use DeepSeek first with FULL, UNTRUNCATED PROMPTS.
# 4. REPAIR: 'Paditësja' encoding fix active.

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
    """Fixes common encoding hallucinations."""
    if not text: return ""
    replacements = {
        "Paditésja": "Paditësja", "paditésja": "paditësja",
        "Përshéndetje": "Përshëndetje", "përshéndetje": "përshëndetje",
        "çështje": "çështje", "Çështje": "Çështje"
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)
    text = re.sub(r'ésja\b', 'ësja', text)
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
    """Cloud Engine: High Intelligence, Costs Money."""
    client = get_deepseek_client()
    if not client: return None
    try:
        kwargs = {
            "model": OPENROUTER_MODEL,
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            "temperature": 0.1, 
            "extra_headers": {"HTTP-Referer": "https://juristi.tech", "X-Title": "Juristi AI Analysis"}
        }
        if json_mode: kwargs["response_format"] = {"type": "json_object"}
        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message.content
    except Exception as e:
        logger.warning(f"⚠️ DeepSeek Call Failed: {e}")
        return None

def _call_local_llm(prompt: str, json_mode: bool = False) -> str:
    """Local Engine: Medium Intelligence, FREE (Eco-Mode)."""
    try:
        payload = {
            "model": LOCAL_MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_ctx": 4096},
            "format": "json" if json_mode else None
        }
        with httpx.Client(timeout=45.0) as client:
            response = client.post(OLLAMA_URL, json=payload)
            return response.json().get("response", "")
    except Exception:
        return ""

# --- STRATEGIC TASKS ---

def generate_summary(text: str) -> str:
    """
    ECO-MODE: ON
    Strategy: Try Local LLM first. If it fails, pay for DeepSeek.
    """
    truncated_text = text[:20000] 
    system_prompt = (
        "Ti je Analist Gjyqësor për Republikën e Kosovës. "
        "Detyra: Krijoni një përmbledhje të qartë dhe koncize të dokumentit. "
        "RREGULL: Përdor 'ë' dhe 'ç' saktë. Shembull: 'Paditësja' (jo Paditesja/Paditésja). "
        "Fokuso te: KUSH (Palët), ÇFARË (Konflikti), KUR (Datat), STATUSI."
    )
    user_prompt = f"DOKUMENTI:\n{truncated_text}"
    
    # 1. Try Local (Free)
    res = _call_local_llm(f"{system_prompt}\n\n{user_prompt}")
    
    # 2. If Local failed or returned garbage, use Cloud (Paid)
    if not res or len(res) < 50:
        res = _call_deepseek(system_prompt, user_prompt)
        
    return repair_albanian_text(res or "Përmbledhja e padisponueshme.")

def extract_graph_data(text: str) -> Dict[str, List[Dict]]:
    """
    ECO-MODE: ON
    Strategy: Try Local LLM first.
    """
    truncated_text = text[:15000]
    # Full prompt required even for Local LLM
    system_prompt = """
    Ti je Inxhinier i Grafit Ligjor për Rastet e Kosovës.
    Detyra: Krijo hartën e marrëdhënieve mes entiteteve.
    RELACIONET: ACCUSES, OWES, CLAIMS, WITNESSED, OCCURRED_ON, CONTRADICTS.
    FORMATI JSON STRIKT:
    {"entities": [{"id": "...", "name": "...", "group": "PERSON/EVENT"}], "relations": [{"source": "...", "target": "...", "label": "..."}]}
    """
    user_prompt = f"TEKSTI:\n{truncated_text}"
    
    # 1. Try Local
    content = _call_local_llm(f"{system_prompt}\n\n{user_prompt}", json_mode=True)
    
    # 2. Fallback to Cloud
    if not content:
        content = _call_deepseek(system_prompt, user_prompt, json_mode=True)

    if content: return _parse_json_safely(content)
    return {"entities": [], "relations": []}

def extract_findings_from_text(text: str) -> List[Dict[str, Any]]:
    """
    ECO-MODE: OFF (Quality Priority)
    Strategy: Complex JSON requires DeepSeek first.
    """
    truncated_text = text[:25000]
    
    # FULL PROMPT RESTORED
    system_prompt = """
    Ti je Motor i Nxjerrjes së Provave për Sistemin e Drejtësisë në Kosovë.
    DETYRA: Identifiko elementet kyçe ligjore dhe ktheji në format JSON.
    
    KATEGORITË E PROVAVE:
    - EVENT (Ngjarje)
    - EVIDENCE (Provë materiale/dokumentare)
    - CLAIM (Pretendim i një pale)
    - CONTRADICTION (Mospërputhje mes palëve)
    - QUANTITY (Shuma parash, sipërfaqe toke)
    - DEADLINE (Afate ligjore/procedurale)
    
    RREGULL GJUHËSOR: Korrigjo gabimet e encoding (psh. shkruaj 'Paditësja').
    DETYRIM: Të paktën 5 gjetje nëse ekzistojnë.
    
    FORMATI JSON (STRIKT):
    {
      "findings": [
        {
          "finding_text": "...",
          "source_text": "...",
          "category": "..."
        }
      ]
    }
    """
    user_prompt = f"DOSJA:\n{truncated_text}"

    # 1. Try Cloud (High Intelligence)
    content = _call_deepseek(system_prompt, user_prompt, json_mode=True)
    
    # 2. Fallback to Local
    if not content:
        content = _call_local_llm(f"{system_prompt}\n\n{user_prompt}", json_mode=True)
    
    if content:
        data = _parse_json_safely(content)
        return data.get("findings", [])
    return []

def analyze_case_contradictions(text: str) -> Dict[str, Any]:
    """
    ECO-MODE: OFF (Quality Priority)
    Strategy: Complex Reasoning (Debate Judge) requires DeepSeek.
    """
    truncated_text = text[:25000]
    
    # FULL PROMPT RESTORED (DEBATE JUDGE V5.6)
    system_prompt = """
    Ti je Gjyqtar i Debatit Ligjor në Gjykatën e Prishtinës.
    DETYRA: Analizo përplasjen ligjore në këtë dosje dhe kthe përgjigjen në JSON.
    
    PROCESI KOGNITIV:
    1. Identifiko Paditësin dhe pretendimin kryesor.
    2. Identifiko të Paditurin dhe mbrojtjen kryesore.
    3. Gjej kontradiktat direkte (Ku nuk pajtohen?).
    4. Gjej provat mbështetëse për secilin.
    5. Çfarë mungon për të marrë vendim?
    
    FORMATI JSON (STRIKT):
    {
        "summary_analysis": "Përmbledhje strategjike e rastit dhe konfliktit kryesor.",
        "conflicting_parties": [
            {"party_name": "Paditësi", "core_claim": "Pretendimi kryesor..."},
            {"party_name": "I Padituri", "core_claim": "Mbrojtja kryesore..."}
        ],
        "contradictions": ["Listë e mospërputhjeve konkrete."],
        "key_evidence": ["Listë e provave të përmendura."],
        "missing_info": ["Çfarë informacioni duhet siguruar shtesë?"]
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