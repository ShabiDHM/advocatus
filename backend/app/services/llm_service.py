# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - CORE INTELLIGENCE V28.6 (STRUCTURED CITATIONS)
# 1. CITATIONS: Enforced strict '[Law](doc://...)' format with Content/Relevance sections.
# 2. LOGIC: Maintained 'Smart JSON' and 'Anti-Parrot' logic.

import os
import json
import logging
import httpx
import re
from typing import List, Dict, Any, Optional
from openai import OpenAI 

from .text_sterilization_service import sterilize_text_for_llm

logger = logging.getLogger(__name__)

__all__ = [
    "analyze_financial_portfolio",
    "analyze_case_integrity",
    "generate_summary",
    "extract_graph_data"
]

# --- CONFIGURATION ---
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat" 
OLLAMA_URL = os.environ.get("LOCAL_LLM_URL", "http://host.docker.internal:11434/api/generate")
LOCAL_MODEL_NAME = "llama3"

_deepseek_client: Optional[OpenAI] = None

# --- CONTEXTS ---
STRICT_CONTEXT = """
CONTEXT: Republika e Kosovës.
LOCAL LAWS: Kushtetuta, Kodi Penal (KPRK), Ligji i Procedurës Kontestimore (LPK), Ligji për Familjen, Ligji i Punës.
GLOBAL STANDARDS: Konventa Evropiane për të Drejtat e Njeriut (KEDNJ), Konventa e OKB për të Drejtat e Fëmijës (UNCRC), Praktika e Gjykatës së Strasburgut (GJEDNJ).
TAX: TVSH Standarde 18%, TVSH e Zvogëluar 8%, Tatimi në Fitim 10%.
CURRENCY: EUR (€).
"""

PROMPT_FORENSIC_ACCOUNTANT = f"""
Ti je "Ekspert Financiar Forensik" (Forensic Accountant) me përvojë 20 vjeçare në auditim në Kosovë.
{STRICT_CONTEXT}

DETYRA JOTE:
Analizo të dhënat financiare (JSON) dhe gjej anomali, rreziqe fiskale dhe trende.

RREGULLAT E ANALIZËS:
1. ANOMALI: Rritje e shpenzimeve >20%, fatura pa përshkrim, shpenzime luksi.
2. TATIMET: Verifiko TVSH (18%) dhe rreziqet e mos-deklarimit.
3. OUTPUT: Kthe përgjigjen VETËM në formatin JSON të mëposhtëm.

FORMATI I PËRGJIGJES (JSON STRICT):
{{
  "executive_summary": "Një paragraf përmbledhës për gjendjen financiare...",
  "anomalies": [
     {{
       "date": "YYYY-MM-DD",
       "amount": 100.00,
       "description": "Përshkrimi i transaksionit",
       "risk_level": "HIGH / MEDIUM / LOW",
       "explanation": "Pse është e dyshimtë?"
     }}
  ],
  "trends": [
     {{
       "category": "Të Hyrat / Shpenzimet",
       "trend": "UP / DOWN / STABLE",
       "percentage": "+10%",
       "comment": "Analiza e trendit"
     }}
  ],
  "recommendations": [
     "Rekomandim 1...",
     "Rekomandim 2..."
  ]
}}
"""

PROMPT_SENIOR_LITIGATOR = f"""
Ti je "Avokat i Lartë" (Senior Partner) në Prishtinë. Specializim: E Drejta Civile & Tregtare.
{STRICT_CONTEXT}

INPUT FORMAT:
1. === GRAPH INTELLIGENCE ===: Lidhje të fshehta.
2. === CASE DOCUMENTS ===: Teksti i dokumenteve.

DETYRA JOTE:
Analizo çështjen duke u bazuar VETËM në FAKTET e ofruara.
MOS PËRDOR SHEMBUJ GJENERIKË.

RREGULLAT E ANALIZËS:
1. ÇËSHTJET (ISSUES): Gjej problemet reale juridike.
2. BAZA LIGJORE (STRUKTURË STRIKTE):
   - Për çdo ligj, përdor SAKTËSISHT këtë format (përfshirë kllapat dhe linjat e reja):
   
   Format:
   [Emri i Ligjit, Neni](doc://Emri i Ligjit, Neni):
   Përmbajtja: [Çfarë thotë neni shkurt]
   Relevanca: [Si lidhet specifikisht me faktet e këtij rasti]

   - OBLIGATIVE: Cito STANDARDET GLOBALE (UNCRC, KEDNJ) nëse ka implikime të të drejtave të njeriut.

3. STRATEGJIA: Sugjero hapa konkretë.

FORMATI I PËRGJIGJES (JSON STRICT):
{{
  "summary": "Përmbledhje e rastit...",
  "key_issues": ["Çështja 1...", "Çështja 2..."],
  "legal_basis": [
     "[Ligji për Familjen, Neni 331](doc://Ligji për Familjen, Neni 331):\\nPërmbajtja: Ndryshimi i rrethanave kërkon ndryshim aktgjykimi.\\nRelevanca: Rroga e babait është rritur, prandaj kërkohet rritja e alimentacionit.",
     "[UNCRC, Neni 3](doc://UNCRC, Neni 3):\\nPërmbajtja: Interesi më i mirë i fëmijës është parësor.\\nRelevanca: Mirëqenia e fëmijës prevalon mbi interesat financiare të prindit."
  ],
  "strategic_analysis": "Analizë e detajuar...",
  "weaknesses": ["Dobësia 1...", "Dobësia 2..."],
  "action_plan": ["Hapi 1...", "Hapi 2..."],
  "risk_level": "HIGH / MEDIUM / LOW"
}}
"""

def get_deepseek_client() -> Optional[OpenAI]:
    global _deepseek_client
    if not _deepseek_client and DEEPSEEK_API_KEY:
        try: _deepseek_client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=OPENROUTER_BASE_URL)
        except Exception as e: logger.error(f"DeepSeek Init Failed: {e}")
    return _deepseek_client

def _parse_json_safely(content: str) -> Dict[str, Any]:
    try: return json.loads(content)
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

def _call_deepseek(system_prompt: str, user_prompt: str, json_mode: bool = False, temperature: float = 0.25) -> Optional[str]:
    client = get_deepseek_client()
    if not client: return None
    try:
        kwargs = {
            "model": OPENROUTER_MODEL, 
            "messages": [
                {"role": "system", "content": system_prompt}, 
                {"role": "user", "content": user_prompt}
            ], 
            "temperature": temperature,
            "extra_headers": {"HTTP-Referer": "https://juristi.tech", "X-Title": "Juristi AI"}
        }
        if json_mode: kwargs["response_format"] = {"type": "json_object"}
        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message.content
    except Exception as e:
        logger.warning(f"⚠️ DeepSeek Call Failed: {e}")
        return None

def _call_local_llm(system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
    try:
        full_prompt = f"{system_prompt}\n\nUSER INPUT:\n{user_prompt}"
        payload = {
            "model": LOCAL_MODEL_NAME, 
            "prompt": full_prompt, 
            "stream": False, 
            "options": {"temperature": 0.2, "num_ctx": 4096}, 
            "format": "json" if json_mode else None
        }
        with httpx.Client(timeout=60.0) as client:
            response = client.post(OLLAMA_URL, json=payload)
            return response.json().get("response", "")
    except Exception as e:
        logger.warning(f"⚠️ Local LLM call failed: {e}")
        return ""

def analyze_financial_portfolio(financial_data_json: str) -> Dict[str, Any]:
    content = _call_deepseek(PROMPT_FORENSIC_ACCOUNTANT, financial_data_json, json_mode=True, temperature=0.2)
    if not content:
        content = _call_local_llm(PROMPT_FORENSIC_ACCOUNTANT, financial_data_json, json_mode=True)
    return _parse_json_safely(content) if content else {}

def analyze_case_integrity(text: str) -> Dict[str, Any]:
    clean_text = sterilize_text_for_llm(text[:35000], redact_names=False)
    content = _call_deepseek(PROMPT_SENIOR_LITIGATOR, clean_text, json_mode=True, temperature=0.25)
    if not content:
        content = _call_local_llm(PROMPT_SENIOR_LITIGATOR, clean_text, json_mode=True)
    return _parse_json_safely(content) if content else {}

def generate_summary(text: str) -> str:
    clean = sterilize_text_for_llm(text[:15000])
    return _call_deepseek("Përmblidh këtë dokument shkurtimisht në shqip.", clean) or "S'ka përmbledhje."

def extract_graph_data(text: str) -> Dict[str, Any]:
    return {"entities": [], "relations": []}