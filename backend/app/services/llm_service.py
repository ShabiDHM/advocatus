# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - INGESTION INTELLIGENCE V5.3 (KOSOVO CONTEXT HARDENING)
# 1. SAFETY: Reinforced "Kosovo Jurisdiction" in all system prompts to prevent dialect/legal drift.
# 2. CONSISTENCY: Enforced standard Albanian language output for all analysis tasks.
# 3. LOGIC: Preserved the "Debate Judge" logic which is performing well.

import os
import json
import logging
import httpx
import re
from typing import List, Dict, Any, Optional
from openai import OpenAI 
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
            "extra_headers": {"HTTP-Referer": "https://juristi.tech", "X-Title": "Juristi AI Analysis"}
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

# --- UNIVERSAL EVIDENCE ENGINE (V5.3) ---

def generate_summary(text: str) -> str:
    truncated_text = text[:20000] 
    system_prompt = (
        "Ti je Analist Gjyqësor për Republikën e Kosovës. "
        "Detyra jote është të krijosh një përmbledhje të qartë dhe koncize të dokumentit. "
        "RREGULL: Përdor gjuhë standarde shqipe (dialekti i Kosovës ku aplikohet terminologjia ligjore). "
        "Fokuso te: "
        "1. KUSH janë palët? "
        "2. CILI është konflikti thelbësor? "
        "3. KUR ka ndodhur ngjarja? "
        "4. STATUSI aktual procedural?"
    )
    user_prompt = f"DOKUMENTI:\n{truncated_text}"
    
    res = _call_deepseek(system_prompt, user_prompt)
    if res: return res
    res = _call_groq(system_prompt, user_prompt)
    if res: return res
    return _call_local_llm(f"{system_prompt}\n\n{user_prompt}") or "Përmbledhja e padisponueshme."

def extract_findings_from_text(text: str) -> List[Dict[str, Any]]:
    """
    Extracts universal legal building blocks from text.
    """
    truncated_text = text[:25000]
    
    # PHOENIX V5.3 UPGRADE: Added explicit "Kosovo Legal Context" instruction
    system_prompt = """
    Ti je Motor i Nxjerrjes së Provave për Sistemin e Drejtësisë në Kosovë.
    
    DETYRA: Identifiko elementet kyçe ligjore.
    
    KATEGORITË E PROVAVE:
    - EVENT (Ngjarje)
    - EVIDENCE (Provë materiale/dokumentare)
    - CLAIM (Pretendim i një pale)
    - CONTRADICTION (Mospërputhje mes palëve)
    - QUANTITY (Shuma parash, sipërfaqe toke)
    - DEADLINE (Afate ligjore/procedurale)
    
    DETYRIM: Përgjigju vetëm në JSON valid. Të paktën 5 gjetje nëse ekzistojnë.
    
    SHEMBUJ TË KUALITETIT TË LARTË (KOSOVË):
    - Për "CLAIM": {"finding_text": "Paditësi kërkon kompensim dëmi.", "category": "CLAIM"}
    - Për "DEADLINE": {"finding_text": "Afati për ankesë është 15 ditë sipas Ligjit për Procedurën Kontestimore.", "category": "DEADLINE"}

    FORMATI JSON:
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

    content = _call_deepseek(system_prompt, user_prompt, json_mode=True)
    if content: return _parse_json_safely(content).get("findings", [])
    
    content = _call_groq(system_prompt, user_prompt, json_mode=True)
    if content: return _parse_json_safely(content).get("findings", [])
    
    content = _call_local_llm(f"{system_prompt}\n\n{user_prompt}", json_mode=True)
    if content: return _parse_json_safely(content).get("findings", [])
    
    return []

def extract_graph_data(text: str) -> Dict[str, List[Dict]]:
    truncated_text = text[:15000]
    system_prompt = """
    Ti je Inxhinier i Grafit Ligjor për Rastet e Kosovës.
    Detyra: Krijo hartën e marrëdhënieve mes entiteteve (Palë, Gjykatës, Provave).
    MARRËDHËNIET: ACCUSES, OWES, CLAIMS, WITNESSED, OCCURRED_ON, CONTRADICTS.
    FORMATI JSON: {"entities": [], "relations": []}
    """
    user_prompt = f"TEKSTI:\n{truncated_text}"
    content = _call_deepseek(system_prompt, user_prompt, json_mode=True)
    if content: return _parse_json_safely(content)
    content = _call_groq(system_prompt, user_prompt, json_mode=True)
    if content: return _parse_json_safely(content)
    return {"entities": [], "relations": []}

def analyze_case_contradictions(text: str) -> Dict[str, Any]:
    """
    High-Level Strategy Analysis (Debate Judge).
    """
    truncated_text = text[:25000]
    
    system_prompt = """
    Ti je Gjyqtar i Debatit Ligjor në Gjykatën e Prishtinës.
    DETYRA: Analizo përplasjen ligjore në këtë dosje.
    
    PROCESI KOGNITIV:
    1. Identifiko Paditësin dhe pretendimin kryesor.
    2. Identifiko të Paditurin dhe mbrojtjen kryesore.
    3. Gjej kontradiktat direkte (Ku nuk pajtohen?).
    4. Gjej provat mbështetëse për secilin.
    5. Çfarë mungon për të marrë vendim?
    
    OUTPUT JSON:
    {
        "summary_analysis": "Përmbledhje strategjike e rastit.",
        "conflicting_parties": [
            {"party_name": "Paditësi", "core_claim": "..."},
            {"party_name": "I Padituri", "core_claim": "..."}
        ],
        "contradictions": ["..."],
        "key_evidence": ["..."],
        "missing_info": ["..."]
    }
    """
    user_prompt = f"DOSJA:\n{truncated_text}"

    content = _call_deepseek(system_prompt, user_prompt, json_mode=True)
    if content: return _parse_json_safely(content)
    
    content = _call_groq(system_prompt, user_prompt, json_mode=True)
    if content: return _parse_json_safely(content)

    return {}

def generate_socratic_response(socratic_context: List[Dict], question: str) -> Dict:
    return {"answer": "Logic moved to R-A-G Service.", "sources": []}

def extract_deadlines_from_text(text: str) -> List[Dict[str, Any]]:
    return []