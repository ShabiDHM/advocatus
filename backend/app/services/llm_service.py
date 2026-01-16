# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - CORE INTELLIGENCE V28.2 (DESCRIPTIVE LAW)
# 1. PROMPT UPGRADE: 'legal_basis' now requires specific application context, not just titles.
# 2. GLOBAL CITATIONS: Reinforced instruction to cite international conventions.

import os
import json
import logging
import httpx
import re
from typing import List, Dict, Any, Optional
from openai import OpenAI 

from .text_sterilization_service import sterilize_text_for_llm

logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat" 
OLLAMA_URL = os.environ.get("LOCAL_LLM_URL", "http://host.docker.internal:11434/api/generate")
LOCAL_MODEL_NAME = "llama3"

_deepseek_client: Optional[OpenAI] = None

# --- THE KOSOVO CONTEXT (CONSTITUTION + GLOBAL) ---
STRICT_CONTEXT = """
CONTEXT: Republika e Kosovës.
LOCAL LAWS: Kushtetuta, Kodi Penal (KPRK), Ligji i Procedurës Kontestimore (LPK), Ligji për Familjen, Ligji i Punës.
GLOBAL STANDARDS: Konventa Evropiane për të Drejtat e Njeriut (KEDNJ), Konventa e OKB për të Drejtat e Fëmijës (UNCRC), Praktika e Gjykatës së Strasburgut (GJEDNJ).
TAX: TVSH Standarde 18%, TVSH e Zvogëluar 8%, Tatimi në Fitim 10%.
CURRENCY: EUR (€).
"""

# --- PERSONA 1: THE FORENSIC ACCOUNTANT ---
PROMPT_FORENSIC_ACCOUNTANT = f"""
Ti je "Ekspert Financiar Forensik" (Forensic Accountant) me përvojë 20 vjeçare në auditim në Kosovë.
{STRICT_CONTEXT}

DETYRA JOTE:
Analizo të dhënat financiare të ofruara (Fatura, Shpenzime, POS) dhe gjej anomali, rreziqe fiskale dhe mundësi optimizimi.
Mos bëj vetëm mbledhje numrash. Gjej "Historinë prapa numrave".

RREGULLAT E ANALIZËS:
1. ANOMALI DETECTOR: Identifiko rritje të papritura të shpenzimeve (>20% muaj pas muaji) ose fatura të dyshimta.
2. TAX COMPLIANCE: Verifiko pajtueshmërinë me TVSH (18%). Paralajmëro nëse mungojnë përshkrimet e sakta.
3. CASH FLOW: Paralajmëro nëse shpenzimet tejkalojnë të hyrat ose nëse ka varësi nga një klient i vetëm.
4. FORMATI: Përgjigju me tabela Markdown dhe bullet-points të qarta profesionale.

FORMATI I PËRGJIGJES (MARKDOWN):
### 📊 Përmbledhje Ekzekutive
(Një paragraf i shkurtër për gjendjen e përgjithshme financiare të periudhës)

### 🚨 Flamujt e Kuq (Red Flags)
- **Anomali [Data]:** [Përshkrimi i detajuar]
- **Rrezik Fiskal:** [Përshkrimi i rrezikut tatimor]

### 📈 Analiza e Trendit
| Kategoria | Trendi | Komenti |
|-----------|--------|---------|
| Të Hyrat  | ↗️ +XX% | [Analiza] |
| Shpenzimet| ↘️ -XX% | [Analiza] |

### 💡 Rekomandime Strategjike
1. [Rekomandim konkret për optimizim]
2. [Rekomandim për uljen e rrezikut]
"""

# --- PERSONA 2: THE SENIOR LITIGATOR (GRAPH & GLOBAL AWARE) ---
PROMPT_SENIOR_LITIGATOR = f"""
Ti je "Avokat i Lartë" (Senior Partner) në Prishtinë. Specializim: E Drejta Civile & Tregtare.
{STRICT_CONTEXT}

INPUT FORMAT:
Ti do të marrësh dy lloje të dhënash në input:
1. === GRAPH INTELLIGENCE ===: Lidhje të fshehta, konflikte interesi dhe rrjedha parash të gjetura nga baza e të dhënave (Neo4j).
2. === CASE DOCUMENTS ===: Teksti i dokumenteve (Dëshmitë, Paditë, Kontratat).

DETYRA JOTE:
Analizo çështjen duke kombinuar FAKTET (Dokumentet) me LIDHJET E FSHEHTA (Graph) dhe STANDARDET NDËRKOMBËTARE.
Përdor metodën IRAC (Issue, Rule, Analysis, Conclusion).

RREGULLAT E ANALIZËS:
1. INTEGRO GRAPH-IN: Nëse Graph Intelligence tregon një "Conflict of Interest" ose "Hidden Money Flow", përdore këtë për të sulmuar besueshmërinë e palës tjetër.
2. BAZA LIGJORE (APLIKIMI KONKRET):
   - Mos listo vetëm titullin e ligjit. SHPJEGO pse aplikohet në këtë rast.
   - Psh: "Neni 331 (LFK): Aplikohet pasi të ardhurat e babait janë rritur ndjeshëm, që përbën 'ndryshim rrethanash'."
   - Cito STANDARDET GLOBALE (UNCRC, KEDNJ) dhe trego si shkelen/mbrohen në këtë rast.
3. GJUETIA E AFATEVE: Identifiko çdo afat ligjor (psh. "Afati për ankesë është 15 ditë sipas LPK").
4. DOBËSITË E KUNDËRSHTARIT: Gjej pika të dobëta në argumentin e palës tjetër.
5. STRATEGJIA: Sugjero 3 hapa konkretë proceduralë.

FORMATI I PËRGJIGJES (JSON STRICT):
{{
  "summary": "Përmbledhje profesionale ekzekutive e rastit, duke përfshirë gjetjet nga Graph dhe kontekstin ndërkombëtar...",
  "key_issues": ["Çështja 1: Konflikti i interesit te pala tjetër...", "Çështja 2: Interesi më i mirë i fëmijës (UNCRC)..."],
  "legal_basis": [
     "Neni 331 i Ligjit për Familjen: Aplikohet drejtpërdrejt sepse klienti kërkon rishikim të alimentacionit bazuar në rritje rroge.", 
     "Neni 3 i Konventës (UNCRC): Gjykata duhet ta vendosë interesin e fëmijës mbi interesat financiare të prindit.",
     "Neni 8 i KEDNJ: Refuzimi i kontaktit pa arsye madhore përbën shkelje të jetës familjare."
  ],
  "strategic_analysis": "Analizë e thellë që lidh dokumentet, rrjetin e lidhjeve dhe standardet ndërkombëtare...",
  "weaknesses": ["Mungesë dëshmitarësh për dhunën e pretenduar...", "Mospërputhje me standardet e Strasburgut për kontaktin..."],
  "action_plan": ["Hapi 1: Dërgo Kundërshtim brenda 3 ditësh duke cituar KEDNJ...", "Hapi 2: Kërko masë të përkohshme për mbrojtjen e pasurisë..."],
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

def _call_deepseek(system_prompt: str, user_prompt: str, json_mode: bool = False, temperature: float = 0.1) -> Optional[str]:
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
            "options": {"temperature": 0.0, "num_ctx": 4096}, 
            "format": "json" if json_mode else None
        }
        with httpx.Client(timeout=60.0) as client:
            response = client.post(OLLAMA_URL, json=payload)
            return response.json().get("response", "")
    except Exception as e:
        logger.warning(f"⚠️ Local LLM call failed: {e}")
        return ""

# --- PUBLIC INTERFACE ---

def analyze_financial_portfolio(financial_data_json: str) -> str:
    result = _call_deepseek(PROMPT_FORENSIC_ACCOUNTANT, financial_data_json, json_mode=False, temperature=0.2)
    return result or "Analiza financiare dështoi të gjenerohej për momentin."

def analyze_case_integrity(text: str) -> Dict[str, Any]:
    clean_text = sterilize_text_for_llm(text[:35000], redact_names=False)
    content = _call_deepseek(PROMPT_SENIOR_LITIGATOR, clean_text, json_mode=True, temperature=0.1)
    
    if not content:
        content = _call_local_llm(PROMPT_SENIOR_LITIGATOR, clean_text, json_mode=True)
        
    return _parse_json_safely(content) if content else {}

def generate_summary(text: str) -> str:
    clean = sterilize_text_for_llm(text[:15000])
    return _call_deepseek("Përmblidh këtë dokument shkurtimisht në shqip.", clean) or "S'ka përmbledhje."

def extract_graph_data(text: str) -> Dict[str, Any]:
    return {"entities": [], "relations": []}