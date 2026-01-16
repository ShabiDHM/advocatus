# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - CORE INTELLIGENCE V28.0 (GRAPH-AWARE)
# 1. PERSONA UPGRADE: 'SeniorLitigator' now explicitly handles 'GRAPH INTELLIGENCE' input.
# 2. FINANCIAL BRAIN: 'ForensicAccountant' retains strict VAT/Tax logic.
# 3. INTEGRATION: Ready to receive fused data (Text + Relations).

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

# --- THE KOSOVO CONTEXT (CONSTITUTION) ---
STRICT_CONTEXT = """
CONTEXT: Republika e Kosovës.
LAWS: Kushtetuta, Kodi Penal (KPRK), Ligji i Procedurës Kontestimore (LPK), Ligji për Familjen, Ligji i Punës.
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

# --- PERSONA 2: THE SENIOR LITIGATOR (GRAPH AWARE) ---
PROMPT_SENIOR_LITIGATOR = f"""
Ti je "Avokat i Lartë" (Senior Partner) në Prishtinë. Specializim: E Drejta Civile & Tregtare.
{STRICT_CONTEXT}

INPUT FORMAT:
Ti do të marrësh dy lloje të dhënash në input:
1. === GRAPH INTELLIGENCE ===: Lidhje të fshehta, konflikte interesi dhe rrjedha parash të gjetura nga baza e të dhënave (Neo4j).
2. === CASE DOCUMENTS ===: Teksti i dokumenteve (Dëshmitë, Paditë, Kontratat).

DETYRA JOTE:
Analizo çështjen duke kombinuar FAKTET (Dokumentet) me LIDHJET E FSHEHTA (Graph).
Përdor metodën IRAC (Issue, Rule, Analysis, Conclusion).

RREGULLAT E ANALIZËS:
1.INTEGRO GRAPH-IN: Nëse Graph Intelligence tregon një "Conflict of Interest" ose "Hidden Money Flow", përdore këtë për të sulmuar besueshmërinë e palës tjetër.
2. GJUETIA E AFATEVE: Identifiko çdo afat ligjor (psh. "Afati për ankesë është 15 ditë sipas LPK").
3. DOBËSITË E KUNDËRSHTARIT: Gjej pika të dobëta në argumentin e palës tjetër.
4. STRATEGJIA: Sugjero 3 hapa konkretë proceduralë bazuar në ligjet e Kosovës.

FORMATI I PËRGJIGJES (JSON STRICT):
{{
  "summary": "Përmbledhje profesionale ekzekutive e rastit, duke përfshirë gjetjet nga Graph...",
  "key_issues": ["Çështja 1: Konflikti i interesit...", "Çështja 2: Vlefshmëria e kontratës..."],
  "legal_basis": ["Neni X i Ligjit për Procedurën Kontestimore", "Neni Y i Ligjit për Familjen"],
  "strategic_analysis": "Analizë e thellë që lidh dokumentet me rrjetin e lidhjeve...",
  "weaknesses": ["Mungesë dëshmitarësh...", "Konflikt interesi i pazbuluar te pala tjetër..."],
  "action_plan": ["Hapi 1: Dërgo Kundërshtim...", "Hapi 2: Kërko përjashtimin e gjyqtarit (nëse ka konflikt)..."],
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
        # Try to extract JSON blob from markdown code blocks
        match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
        if match:
            try: return json.loads(match.group(1))
            except: pass
        # Try to find first { and last }
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
    """
    Called by FinanceService.
    Generates a Forensic Markdown Report.
    """
    # 0.2 Temp allows slightly creative analysis but strict math
    result = _call_deepseek(PROMPT_FORENSIC_ACCOUNTANT, financial_data_json, json_mode=False, temperature=0.2)
    return result or "Analiza financiare dështoi të gjenerohej për momentin."

def analyze_case_integrity(text: str) -> Dict[str, Any]:
    """
    Called by AnalysisService.
    Generates a Legal Strategic JSON.
    NOTE: 'text' input here now contains both GRAPH INTELLIGENCE and DOCUMENTS.
    """
    clean_text = sterilize_text_for_llm(text[:35000], redact_names=False)
    content = _call_deepseek(PROMPT_SENIOR_LITIGATOR, clean_text, json_mode=True, temperature=0.1)
    
    # Fallback to Local LLM if API fails
    if not content:
        content = _call_local_llm(PROMPT_SENIOR_LITIGATOR, clean_text, json_mode=True)
        
    return _parse_json_safely(content) if content else {}

# Legacy Support
def generate_summary(text: str) -> str:
    clean = sterilize_text_for_llm(text[:15000])
    return _call_deepseek("Përmblidh këtë dokument shkurtimisht në shqip.", clean) or "S'ka përmbledhje."

def extract_graph_data(text: str) -> Dict[str, Any]:
    # Placeholder for graph extraction logic (ingestion phase)
    return {"entities": [], "relations": []}