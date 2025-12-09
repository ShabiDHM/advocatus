# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - INGESTION INTELLIGENCE V4 (KOSOVO EXCLUSIVE)
# 1. JURISDICTION: All prompts strictly enforce "Republic of Kosovo" context.
# 2. FILTERING: Instructs LLM to ignore/flag foreign legal concepts (e.g. Albania).
# 3. UPGRADE: 'extract_graph_data' hunts for Conflict & Money (Litigation Graph).
# 4. UPGRADE: 'extract_findings_from_text' performs Forensic auditing on Dates & Amounts.

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
            "temperature": 0.0, # ZERO Temperature for strict adherence to facts/rules
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
    truncated_text = text[:20000] 
    # PHOENIX: Kosovo-Specific System Prompt
    system_prompt = (
        "Ti je 'Juristi AI', ekspert për dokumentacionin ligjor në Republikën e Kosovës. "
        "Detyra: Krijo një përmbledhje ekzekutive. "
        "Fokusi: Identifiko Palët, Objektin, dhe Datat. "
        "RREGULL: Nëse përmenden ligje apo qytete të Shqipërisë (psh Tiranë), shënoje qartë si 'Juridiksion i Huaj' në përmbledhje."
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
    Strictly restricted to logical fact-checking.
    """
    truncated_text = text[:20000]
    
    system_prompt = """
    Ti je Auditor Ligjor Forenzik për Kosovën.
    
    DETYRA: Gjej fakte kritike në tekst (Datat, Paratë, Detyrimet).
    
    RREGULLA:
    1. VALIDIMI: Injoro ligjet e huaja (Shqipëri), por nxirr faktet (shumat, datat).
    2. DATAT: Nëse data është "228 Dhjetor", shënoje si 'DATE' por shto '(GABIM LOGJIK)' në tekst.
    
    FORMATI JSON (STRIKT):
    {
      "findings": [
        {
          "finding_text": "Përshkrimi i qartë i faktit",
          "source_text": "Citat i saktë",
          "category": "DATE" | "MONEY" | "OBLIGATION" | "RISK"
        }
      ]
    }
    """
    user_prompt = f"TEKSTI PËR ANALIZË:\n{truncated_text}"

    content = _call_deepseek(system_prompt, user_prompt, json_mode=True)
    if content: return _parse_json_safely(content).get("findings", [])
    
    content = _call_groq(system_prompt, user_prompt, json_mode=True)
    if content: return _parse_json_safely(content).get("findings", [])
    
    content = _call_local_llm(f"{system_prompt}\n\n{user_prompt}", json_mode=True)
    if content: return _parse_json_safely(content).get("findings", [])
    
    return []

def extract_graph_data(text: str) -> Dict[str, List[Dict]]:
    """
    Litigation Graph Extraction: Builds the 'Conflict Map'.
    """
    truncated_text = text[:15000]
    
    system_prompt = """
    Ti je Inxhinier i Grafit Ligjor (Kosovo Context).
    
    ENTITETET (Nodes):
    - Person (Emra)
    - Organization (Kompania)
    - Money (Shuma)
    - Date (Data)
    - Claim (Pretendime)
    
    MARRËDHËNIET:
    - PAID, OWES, SIGNED, ACCUSES, CONTRADICTS
    
    RREGULL:
    - Mos krijo nodes për ligje të Shqipërisë.
    
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
    return []