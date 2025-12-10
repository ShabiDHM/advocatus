# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - INGESTION INTELLIGENCE V5.0 (UNIVERSAL EVIDENCE ENGINE)
# 1. CORE UPGRADE: Prompts are now Case-Type Agnostic (Criminal, Civil, Family, etc.).
# 2. ABSTRACTION: AI now hunts for universal legal concepts: 'Events', 'Actors', 'Claims', 'Evidence'.
# 3. FUTURE-PROOF: This file should NOT require changes for new case types.

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

# --- UNIVERSAL EVIDENCE ENGINE ---

def generate_summary(text: str) -> str:
    truncated_text = text[:20000] 
    system_prompt = (
        "Ti je Analist Gjyqësor për Republikën e Kosovës. "
        "Detyra jote është të krijosh një përmbledhje të qartë dhe koncize të çdo lloj dokumenti ligjor. "
        "Fokuso te: "
        "1. KUSH janë palët kryesore? "
        "2. CILI është konflikti thelbësor? "
        "3. KUR ka ndodhur ngjarja kryesore? "
        "4. CILI është hapi i radhës procedural (nëse përmendet)?"
    )
    user_prompt = f"DOKUMENTI:\n{truncated_text}"
    
    res = _call_deepseek(system_prompt, user_prompt)
    if res: return res
    res = _call_groq(system_prompt, user_prompt)
    if res: return res
    return _call_local_llm(f"{system_prompt}\n\n{user_prompt}") or "Përmbledhja e padisponueshme."

def extract_findings_from_text(text: str) -> List[Dict[str, Any]]:
    """
    Extracts universal legal building blocks from text, regardless of case type.
    """
    truncated_text = text[:25000]
    
    system_prompt = """
    Ti je një motor për nxjerrjen e provave (Evidence Extraction Engine) për sistemin ligjor të Kosovës.
    
    DETYRA: Shndërro tekstin e papërpunuar në një listë të strukturuar të PROVAVE.
    
    KATEGORITË E PROVAVE (Gjej sa më shumë të mundesh):
    
    - EVENT: Një ngjarje specifike që ka ndodhur (psh. 'Lidhja e kontratës', 'Kërcënimi me armë').
    - EVIDENCE: Një provë materiale e përmendur (psh. 'Fletë-pranimi', 'Raporti i Auditimit', 'Dëshmitari Luan Kelmendi').
    - CLAIM: Një akuzë ose pretendim nga njëra palë kundër tjetrës (psh. 'Teuta pretendon se Iliri ka fshehur pasuri').
    - CONTRADICTION: Një pikë ku deklaratat e palëve bien ndesh direkt (psh. 'Njëri thotë ishte në zyrë, tjetri thotë ishte në Tiranë').
    - QUANTITY: Çdo sasi e matshme (psh. '12,500 Euro', '50,000 Euro', '1000 Euro alimentacion').
    - DEADLINE: Çdo datë që përfaqëson një afat, seancë, ose detyrim të ardhshëm (psh. '18 Dhjetor 2025').
    
    FORMATI JSON (STRIKT):
    {
      "findings": [
        {
          "finding_text": "Përshkrimi i qartë i provës/faktit",
          "source_text": "Citat i saktë nga dokumenti",
          "category": "EVENT | EVIDENCE | CLAIM | CONTRADICTION | QUANTITY | DEADLINE"
        }
      ]
    }
    """
    user_prompt = f"TEKSTI I DOSJES:\n{truncated_text}"

    content = _call_deepseek(system_prompt, user_prompt, json_mode=True)
    if content: return _parse_json_safely(content).get("findings", [])
    
    content = _call_groq(system_prompt, user_prompt, json_mode=True)
    if content: return _parse_json_safely(content).get("findings", [])
    
    content = _call_local_llm(f"{system_prompt}\n\n{user_prompt}", json_mode=True)
    if content: return _parse_json_safely(content).get("findings", [])
    
    return []

def extract_graph_data(text: str) -> Dict[str, List[Dict]]:
    """
    Maps the universal relationships between entities.
    """
    truncated_text = text[:15000]
    
    system_prompt = """
    Ti je Inxhinier i Grafit Ligjor. Detyra: Krijo hartën e marrëdhënieve.
    
    MARRËDHËNIET (Universale):
    - [Person/Organization] ACCUSES [Person/Organization]
    - [Person] OWES [Quantity]
    - [Person] CLAIMS [Object/Asset]
    - [Person] WITNESSED [Event]
    - [Event] OCCURRED_ON [Date]
    - [Claim] CONTRADICTS [Claim]
    
    FORMATI JSON:
    {
      "entities": [{"name": "Emri", "type": "Person | Organization | Quantity | Event | Claim"}],
      "relations": [{"subject": "Emri1", "relation": "UPPERCASE_VERB", "object": "Emri2"}]
    }
    """
    user_prompt = f"TEKSTI:\n{truncated_text}"
    
    content = _call_deepseek(system_prompt, user_prompt, json_mode=True)
    if content: return _parse_json_safely(content)
    
    content = _call_groq(system_prompt, user_prompt, json_mode=True)
    if content: return _parse_json_safely(content)
    
    return {"entities": [], "relations": []}

def analyze_case_contradictions(text: str) -> Dict[str, Any]:
    """
    High-Level Strategy Analysis for the 'Analizo Rastin' Modal.
    """
    truncated_text = text[:25000]
    
    system_prompt = """
    Ti je Strateg Ligjor Virtual.
    
    DETYRA: Analizo dosjen për pikat e forta, pikat e dobëta dhe kontradiktat.
    
    OUTPUT JSON:
    {
        "summary_analysis": "Përmbledhje strategjike e konfliktit dhe çfarë e bën atë të komplikuar.",
        "contradictions": ["Lista e detajuar e pikave ku versionet e palëve përplasen."],
        "key_evidence": ["Cilat janë provat më të rëndësishme të përmendura (dëshmitarë, dokumente)? Pse janë të rëndësishme?"],
        "missing_info": ["Çfarë provash kritike mungojnë që një avokat duhet t'i kërkojë menjëherë?"]
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
    # This is handled by deadline_service.py now, keep empty to avoid confusion
    return []