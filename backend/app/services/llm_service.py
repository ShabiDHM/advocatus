# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - INGESTION INTELLIGENCE V3
# 1. UPGRADE: 'extract_graph_data' now hunts for Conflict & Money (Litigation Graph).
# 2. UPGRADE: 'extract_findings_from_text' performs Forensic auditing on Dates & Amounts.
# 3. GOAL: Feed high-quality data to the Chatbot & Graph.

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

# --- CORE SERVICES (UPGRADED) ---

def generate_summary(text: str) -> str:
    truncated_text = text[:20000] # Increased context window
    system_prompt = (
        "Ti je 'Juristi AI', një asistent ligjor elitar. "
        "Detyra: Krijo një përmbledhje ekzekutive të këtij dokumenti në gjuhën Shqipe. "
        "Fokusi: Identifiko Palët, Objektin e Marrëveshjes/Konfliktit, dhe Datat Kryesore. "
        "Stili: Profesional, konciz, dhe i qartë."
    )
    user_prompt = f"DOKUMENTI:\n{truncated_text}"
    
    res = _call_deepseek(system_prompt, user_prompt)
    if res: return res
    res = _call_groq(system_prompt, user_prompt)
    if res: return res
    return _call_local_llm(f"{system_prompt}\n\n{user_prompt}") or "Përmbledhja e padisponueshme."

def extract_findings_from_text(text: str) -> List[Dict[str, Any]]:
    """
    Forensic Extraction: Hunts for Dates, Money, Obligations, and Anomalies.
    """
    truncated_text = text[:20000]
    
    system_prompt = """
    Ti je Auditor Ligjor Forenzik. Analizo tekstin për Gjetje Kritike (Facts).
    
    KATEGORITË E KËRKIMIT:
    1. 📅 AFATET & KRONOLOGJIA: Identifiko çdo datë. A ka data që bien ndesh (psh. afati para nënshkrimit)? Shënoji si rreziqe.
    2. 💰 DETYRIMET FINANCIARE: Shuma, Këste, Penalitete, Afate pagese.
    3. ⚖️ DETYRIMET LIGJORE: Çfarë duhet të bëjë secila palë? (Dorëzimi i çelësave, Raportet, etj).
    
    FORMATI JSON (STRIKT):
    {
      "findings": [
        {
          "finding_text": "Përshkrimi i qartë i faktit (psh. 'Çelësat duhet të dorëzohen më 1 Dhjetor 2025')",
          "source_text": "Cito tekstin origjinal nga dokumenti për saktësi",
          "category": "DATE" | "MONEY" | "OBLIGATION" | "RISK"
        }
      ]
    }
    """
    user_prompt = f"TEKSTI PËR ANALIZË:\n{truncated_text}"

    # Try DeepSeek first (Best logic)
    content = _call_deepseek(system_prompt, user_prompt, json_mode=True)
    if content: return _parse_json_safely(content).get("findings", [])
    
    # Fallback to Groq
    content = _call_groq(system_prompt, user_prompt, json_mode=True)
    if content: return _parse_json_safely(content).get("findings", [])
    
    # Fallback to Local
    content = _call_local_llm(f"{system_prompt}\n\n{user_prompt}", json_mode=True)
    if content: return _parse_json_safely(content).get("findings", [])
    
    return []

def extract_graph_data(text: str) -> Dict[str, List[Dict]]:
    """
    Litigation Graph Extraction: Builds the 'Conflict Map'.
    """
    truncated_text = text[:15000]
    
    system_prompt = """
    Ti je Inxhinier i Grafit Ligjor. Detyra jote është të nxjerrësh Entitetet dhe Marrëdhëniet për një bazë të dhënash Neo4j.
    
    ENTITETET (Nodes):
    - Person (Emra njerëzish)
    - Organization (Kompania, Institucione)
    - Money (Shuma specifike psh. '2500 EUR')
    - Date (Data specifike)
    - Claim (Pretendime, psh. 'Mospagim qiraje', 'Shkelje afati')
    
    MARRËDHËNIET (Edges - Subject -> Relation -> Object):
    - Transaksione: PAID, OWES, AGREED_TO_PAY
    - Ligjore: SIGNED, REPRESENTS, SUED
    - Konflikt: ACCUSES, CONTRADICTS, VIOLATED
    - Kohore: DUE_ON, SIGNED_ON
    
    SHEMBULL LOGJIK:
    Nëse teksti thotë "Artani akuzon Besnikun për vonesë", krijo:
    Person(Artan) --ACCUSES--> Person(Besnik)
    
    FORMATI JSON (STRIKT):
    {
      "entities": [{"name": "Emri", "type": "Person | Organization | Money | Date | Claim"}],
      "relations": [{"subject": "Emri1", "relation": "UPPERCASE_VERB", "object": "Emri2"}]
    }
    """
    user_prompt = f"TEKSTI:\n{truncated_text}"
    
    content = _call_deepseek(system_prompt, user_prompt, json_mode=True)
    if content: return _parse_json_safely(content)
    
    content = _call_groq(system_prompt, user_prompt, json_mode=True)
    if content: return _parse_json_safely(content)
    
    return {"entities": [], "relations": []}

def generate_socratic_response(socratic_context: List[Dict], question: str) -> Dict:
    return {"answer": "Logic moved to RAG Service.", "sources": []}

def extract_deadlines_from_text(text: str) -> List[Dict[str, Any]]:
    # Can be expanded later for specific calendar events
    return []