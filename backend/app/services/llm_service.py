# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - CORE INTELLIGENCE V33.0 (EXPENSE AI)
# 1. FEATURE: Added 'extract_expense_details_from_text' for AI Receipt Analysis.
# 2. PROMPT: Added 'PROMPT_EXPENSE_EXTRACTOR' to structure raw OCR text into JSON.
# 3. STATUS: Completes the backend logic for the "Scan-to-Data" expense pipeline.

import os
import json
import logging
import httpx
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from openai import OpenAI 

from .text_sterilization_service import sterilize_text_for_llm

logger = logging.getLogger(__name__)

__all__ = [
    "analyze_financial_portfolio",
    "analyze_case_integrity",
    "generate_adversarial_simulation",
    "build_case_chronology",
    "translate_for_client",
    "detect_contradictions",
    "extract_deadlines",
    "perform_litigation_cross_examination",
    "generate_summary",
    "extract_graph_data",
    "get_embedding",
    "forensic_interrogation",
    "categorize_document_text",
    "sterilize_legal_text",
    "extract_expense_details_from_text" # PHOENIX: New Export
]

# --- CONFIGURATION ---
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") 
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat" 
EMBEDDING_MODEL = "text-embedding-3-small" 

OLLAMA_URL = os.environ.get("LOCAL_LLM_URL", "http://host.docker.internal:11434/api/generate")
OLLAMA_EMBED_URL = os.environ.get("LOCAL_LLM_EMBED_URL", "http://host.docker.internal:11434/api/embeddings")
LOCAL_MODEL_NAME = "llama3"
LOCAL_EMBED_MODEL = "nomic-embed-text"

_deepseek_client: Optional[OpenAI] = None
_openai_client: Optional[OpenAI] = None

# --- CONTEXTS ---
STRICT_CONTEXT = """
CONTEXT: Republika e Kosovës.
LAWS: Kushtetuta, LPK (Procedura Kontestimore), LFK (Familja), KPRK (Penale).
GLOBAL: UNCRC (Fëmijët), KEDNJ (Të Drejtat e Njeriut).
"""

# --- PROMPTS ---
PROMPT_SENIOR_LITIGATOR = f"""
Ti je "Avokat i Lartë" (Senior Partner).
{STRICT_CONTEXT}
DETYRA: Analizo çështjen, gjej bazën ligjore dhe strategjinë.

RREGULLAT E ANALIZËS:
1. ÇËSHTJET (ISSUES): Gjej problemet reale juridike.
2. BAZA LIGJORE (STRUKTURË STRIKTE):
   - Për çdo ligj, TI DUHET TË PËRDORËSH SAKTËSISHT këtë format me linja të reja (\\n):
   
   [Emri i Ligjit, Neni](doc://Emri i Ligjit, Neni):\\nPërmbajtja: [Përmbledhja e nenit]\\nRelevanca: [Si lidhet ky nen me faktet e rastit]
   
   - CITIMET E THJESHTA (pa Përmbajtje/Relevancë) JANË TË NDALUARA.
   - OBLIGATIVE: Cito STANDARDET GLOBALE (UNCRC, KEDNJ) me të njëjtin format.

3. STRATEGJIA: Sugjero hapa konkretë.

FORMATI I PËRGJIGJES (JSON STRICT):
{{
  "summary": "Përmbledhje e rastit...",
  "key_issues": ["Çështja 1...", "Çështja 2..."],
  "legal_basis": [
     "[Ligji për Familjen, Neni 331](doc://Ligji për Familjen, Neni 331):\\nPërmbajtja: Lejon ndryshimin e aktgjykimit nëse rrethanat kanë ndryshuar.\\nRelevanca: Rritja e pagës së palës tjetër përbën një rrethanë të re për rritjen e alimentacionit.",
     "[UNCRC, Neni 3](doc://UNCRC, Neni 3):\\nPërmbajtja: Thekson se interesi më i mirë i fëmijës është parësor.\\nRelevanca: Nevojat e fëmijës për një jetesë më të mirë tejkalojnë pretendimin e prindit për të mos paguar më shumë."
  ],
  "strategic_analysis": "Analizë e detajuar...",
  "weaknesses": ["Dobësia 1...", "Dobësia 2..."],
  "action_plan": ["Hapi 1...", "Hapi 2..."],
  "risk_level": "HIGH / MEDIUM / LOW"
}}
"""

PROMPT_FORENSIC_INTERROGATOR = """
Ti je "Forensic Financial Agent" (Agjent Financiar Ligjor).
DETYRA: Përgjigju pyetjes së avokatit duke u bazuar VETËM në rreshtat e transaksioneve të ofruara.

RREGULLAT E GJUHËS:
1. Përgjigju VETËM NË GJUHËN SHQIPE.
2. Përdor terminologji ligjore/financiare të përshtatshme për Kosovën.

RREGULLAT E ANALIZËS:
1. Përdor Referenca: Çdo fakt duhet të ketë referencë (psh: "Rreshti 54, 10 Maj").
2. Ji Agresiv: Nëse gjen shpenzime luksi (bixhoz, hotele, online), theksoji ato si "Mospërputhje me të ardhurat".
3. Llogarit Totale: Nëse kërkohet, mblidh shumat.

FORMATI I PËRGJIGJES (Markdown):
- **Përgjigje Direkte**: Përgjigja direkte në Shqip.
- **Provat**: Lista e transaksioneve (Data | Përshkrimi | Shuma).
- **Implikimi Strategjik**: Si mund të përdoret kjo në gjykatë kundër palës tjetër.

CONTEXT (TRANSACTIONS FOUND):
{context}
"""

PROMPT_FORENSIC_ACCOUNTANT = f"""
Ti je "Ekspert Financiar Forensik".
DETYRA: Analizo të dhënat financiare JSON për anomali.
GJUHA: SHQIP.
FORMATI JSON: {{ "executive_summary": "...", "anomalies": [], "trends": [], "recommendations": [] }}
"""

PROMPT_ADVERSARIAL = f"""
Ti je "Avokati i Palës Kundërshtare".
DETYRA: Gjej dobësitë në argumentet e paraqitura dhe krijo një kundër-strategji.
GJUHA: SHQIP.
FORMATI JSON: {{ "opponent_strategy": "...", "weakness_attacks": [], "counter_claims": [], "predicted_outcome": "..." }}
"""

PROMPT_CHRONOLOGY = f"""
Ti je "Arkivist Ligjor".
DETYRA: Krijo një kronologji preçize të ngjarjeve nga teksti.
GJUHA: SHQIP.
FORMATI JSON: {{ "timeline": [ {{ "date": "...", "event": "...", "source": "..." }} ] }}
"""

PROMPT_CONTRADICTION = f"""
Ti je "Detektiv Investigues".
DETYRA: Krahaso DEKLARATAT me PROVAT. Gjej gënjeshtra.
GJUHA: SHQIP.
FORMATI JSON: {{ "contradictions": [ {{ "claim": "...", "evidence": "...", "severity": "HIGH", "impact": "..." }} ] }}
"""

PROMPT_DEADLINE = f"""
Ti je "Zyrtar i Afateve".
DETYRA: Identifiko afatet e ankesës (15 ditë për Aktgjykim, 7 për Aktvendim).
GJUHA: SHQIP.
FORMATI JSON: {{ "is_judgment": bool, "document_type": "...", "deadline_date": "YYYY-MM-DD", "action_required": "..." }}
"""

PROMPT_CROSS_EXAMINE = f"""
Ti je "Ekspert i Kryqëzimit të Fakteve".
DETYRA: Analizo DOKUMENTIN TARGET në kontekst të DOKUMENTEVE TË TJERA.
GJUHA: SHQIP.
FORMATI JSON: {{ "consistency_check": "...", "contradictions": [], "corroborations": [], "strategic_value": "HIGH/MEDIUM/LOW" }}
"""

PROMPT_TRANSLATOR = """
Ti je "Ndërmjetësues". 
DETYRA: Përkthe tekstin ligjor në gjuhë të thjeshtë për klientin.
GJUHA: SHQIP.
"""

PROMPT_CATEGORIZER = f"""
Ti je "Arkivist Ligjor".
DETYRA: Klasifiko dokumentin në njërën prej këtyre kategorive:
[ "Padi", "Aktgjykim", "Vendim", "Përgjigje në Padi", "Ankesë", "Procesverbal", "Kontratë", "Faturë", "Dëshmi", "Të tjera" ]
GJUHA: SHQIP.
FORMATI JSON: {{ "category": "..." }}
"""

# PHOENIX NEW: EXPENSE EXTRACTION PROMPT
PROMPT_EXPENSE_EXTRACTOR = f"""
Ti je "Kontabilist Ekspert".
DETYRA: Analizo tekstin e skanuar nga një faturë/kupon fiskal dhe nxirr të dhënat e strukturuara.

RREGULLA:
1. Gjej SHUMËN TOTALE (Total/Totali). Injoro nëntotalet ose taksat.
2. Gjej DATËN e faturës. Formatoje si YYYY-MM-DD. Nëse mungon, përdor datën e sotme.
3. Gjej PËRSHKRIMIN (Emrin e Biznesit + artikujt kryesorë).
4. KATEGORIZO shpenzimin (psh: "Ushqim", "Transport", "Zyrë", "Paga", "Të tjera").

GJUHA E DALJES: SHQIP.

FORMATI JSON (STRIKT):
{{
  "category": "...",
  "amount": 0.00,
  "date": "YYYY-MM-DD",
  "description": "..."
}}
"""

def get_deepseek_client() -> Optional[OpenAI]:
    global _deepseek_client
    if not _deepseek_client and DEEPSEEK_API_KEY:
        try: _deepseek_client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=OPENROUTER_BASE_URL)
        except Exception as e: logger.error(f"DeepSeek Init Failed: {e}")
    return _deepseek_client

def get_openai_client() -> Optional[OpenAI]:
    """Specific client for Embeddings if using standard OpenAI models"""
    global _openai_client
    if not _openai_client and OPENAI_API_KEY:
        try: _openai_client = OpenAI(api_key=OPENAI_API_KEY)
        except Exception as e: logger.error(f"OpenAI Init Failed: {e}")
    return _openai_client

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

def _call_llm(system_prompt: str, user_prompt: str, json_mode: bool = False, temp: float = 0.2) -> Optional[str]:
    client = get_deepseek_client()
    if client:
        try:
            kwargs = {
                "model": OPENROUTER_MODEL, 
                "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}], 
                "temperature": temp
            }
            if json_mode: kwargs["response_format"] = {"type": "json_object"}
            res = client.chat.completions.create(**kwargs)
            return res.choices[0].message.content
        except: pass
    
    try:
        with httpx.Client(timeout=60.0) as c:
            res = c.post(OLLAMA_URL, json={
                "model": LOCAL_MODEL_NAME, "prompt": f"{system_prompt}\nUSER: {user_prompt}", 
                "stream": False, "format": "json" if json_mode else None, "options": {"temperature": temp}
            })
            return res.json().get("response", "")
    except: return None

# --- NEW: VECTORIZATION SUPPORT ---

def get_embedding(text: str) -> List[float]:
    """
    Generates a vector embedding for the provided text.
    Prioritizes OpenAI (text-embedding-3-small) for quality, falls back to Ollama.
    """
    clean_text = text.replace("\n", " ")
    
    client = get_openai_client()
    if client:
        try:
            return client.embeddings.create(input=[clean_text], model=EMBEDDING_MODEL).data[0].embedding
        except Exception as e:
            logger.warning(f"OpenAI Embedding failed, falling back: {e}")

    try:
        with httpx.Client(timeout=10.0) as c:
            res = c.post(OLLAMA_EMBED_URL, json={
                "model": LOCAL_EMBED_MODEL,
                "prompt": clean_text
            })
            data = res.json()
            if "embedding" in data: return data["embedding"]
    except Exception:
        pass
        
    logger.error("All embedding methods failed. Returning zero-vector.")
    return [0.0] * 1536 

# --- PUBLIC FUNCTIONS ---

def sterilize_legal_text(text: str) -> str:
    """Wrapper for the core sterilization function."""
    return sterilize_text_for_llm(text)

def forensic_interrogation(question: str, context_rows: List[str]) -> str:
    context_str = "\n".join(context_rows)
    prompt_filled = PROMPT_FORENSIC_INTERROGATOR.replace("{context}", context_str)
    return _call_llm(prompt_filled, question, False, temp=0.3) or "Sistemi nuk mundi të analizojë të dhënat."

def analyze_financial_portfolio(data: str) -> Dict[str, Any]:
    return _parse_json_safely(_call_llm(PROMPT_FORENSIC_ACCOUNTANT, data, True) or "{}")

def analyze_case_integrity(text: str) -> Dict[str, Any]:
    clean = sterilize_text_for_llm(text[:35000])
    return _parse_json_safely(_call_llm(PROMPT_SENIOR_LITIGATOR, clean, True) or "{}")

def generate_adversarial_simulation(text: str) -> Dict[str, Any]:
    clean = sterilize_text_for_llm(text[:25000])
    return _parse_json_safely(_call_llm(PROMPT_ADVERSARIAL, clean, True, temp=0.4) or "{}")

def build_case_chronology(text: str) -> Dict[str, Any]:
    clean = sterilize_text_for_llm(text[:30000])
    return _parse_json_safely(_call_llm(PROMPT_CHRONOLOGY, clean, True, temp=0.1) or "{}")

def detect_contradictions(text: str) -> Dict[str, Any]:
    clean = sterilize_text_for_llm(text[:30000])
    return _parse_json_safely(_call_llm(PROMPT_CONTRADICTION, clean, True, temp=0.1) or "{}")

def extract_deadlines(text: str) -> Dict[str, Any]:
    clean = sterilize_text_for_llm(text[:5000]) 
    return _parse_json_safely(_call_llm(PROMPT_DEADLINE, clean, True, temp=0.0) or "{}")

def perform_litigation_cross_examination(target_text: str, context_summaries: List[str]) -> Dict[str, Any]:
    clean_target = sterilize_text_for_llm(target_text[:15000])
    context_block = "\n".join(context_summaries)
    prompt = f"TARGET DOCUMENT CONTENT:\n{clean_target}\n\nCONTEXT (OTHER DOCUMENTS):\n{context_block}"
    return _parse_json_safely(_call_llm(PROMPT_CROSS_EXAMINE, prompt, True, temp=0.2) or "{}")

def translate_for_client(legal_text: str) -> str:
    return _call_llm(PROMPT_TRANSLATOR, legal_text, False, temp=0.5) or "Gabim në përkthim."

def generate_summary(text: str) -> str:
    clean = sterilize_text_for_llm(text[:15000])
    return _call_llm("Përmblidh dokumentin.", clean, False) or ""

def extract_graph_data(text: str) -> Dict[str, Any]:
    return {"entities": [], "relations": []}

def categorize_document_text(text: str) -> str:
    clean = sterilize_text_for_llm(text[:4000])
    result = _parse_json_safely(_call_llm(PROMPT_CATEGORIZER, clean, True, temp=0.0) or "{}")
    return result.get("category", "Të tjera")

# PHOENIX NEW: Expense Extractor Logic
def extract_expense_details_from_text(raw_text: str) -> Dict[str, Any]:
    """
    Extracts structured expense data (Category, Amount, Date) from raw receipt text.
    """
    if not raw_text or len(raw_text) < 10:
        return {"category": "", "amount": 0, "date": "", "description": ""}
        
    clean_text = sterilize_text_for_llm(raw_text[:2000]) # Receipts are short
    
    # We pass the current date to context so LLM can infer 'today' if needed
    current_date = datetime.now().strftime("%Y-%m-%d")
    context_prompt = f"DATA E SOTME: {current_date}\n\nTEKSTI I FATURËS:\n{clean_text}"
    
    result = _parse_json_safely(_call_llm(PROMPT_EXPENSE_EXTRACTOR, context_prompt, True, temp=0.1) or "{}")
    
    return {
        "category": result.get("category", "Të tjera"),
        "amount": float(result.get("amount", 0.0)),
        "date": result.get("date", current_date),
        "description": result.get("description", "")
    }