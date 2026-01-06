# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - CORE INTELLIGENCE V26.2 (CHRONOLOGY RESTORED)
# 1. FIX: Restored the detailed 'LITIGATION_STRATEGIST_PROMPT' from V25.3 that was accidentally simplified in V26.1.
# 2. FEATURE: Explicitly commands the AI to extract ALL dates for the chronology to prevent empty states.
# 3. STATUS: Full feature set (Financial, Legal, Graph, Calendar, Chronology) active.

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

# --- THE FORENSIC CONSTITUTION ---
STRICT_FORENSIC_RULES = """
RREGULLAT E AUDITIMIT (STRICT LIABILITY):
1. DUALITY OF BRAINS: BAZA E LIGJEVE (LIGJI) dhe BAZA E LËNDËS (FAKTET).
2. STRICT SEPARATION: Mos shpik fakte. Mos shpik ligje.
3. JURISDICTION: Republika e Kosovës.
"""

def get_deepseek_client() -> Optional[OpenAI]:
    global _deepseek_client
    if not _deepseek_client and DEEPSEEK_API_KEY:
        try: _deepseek_client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=OPENROUTER_BASE_URL)
        except Exception as e: logger.error(f"DeepSeek Init Failed: {e}")
    return _deepseek_client

def sterilize_legal_text(text: str) -> str:
    if not text: return ""
    text = sterilize_text_for_llm(text, redact_names=False)
    text = re.sub(r'--- \[Page (\d+)\] ---', r'--- [FAQJA \1] ---', text)
    replacements = {"Paditésja": "Paditësja", "paditésja": "paditësja", "Paditési": "Paditësi", "paditési": "paditësi", "Gjykatés": "Gjykatës", "gjykatés": "gjykatës"}
    for bad, good in replacements.items(): text = text.replace(bad, good)
    return text

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

def _call_deepseek(system_prompt: str, user_prompt: str, json_mode: bool = False) -> Optional[str]:
    client = get_deepseek_client()
    if not client: return None
    try:
        full_system_prompt = f"{system_prompt}\n\n{STRICT_FORENSIC_RULES}"
        kwargs = {"model": OPENROUTER_MODEL, "messages": [{"role": "system", "content": full_system_prompt}, {"role": "user", "content": user_prompt}], "temperature": 0.1, "extra_headers": {"HTTP-Referer": "https://juristi.tech", "X-Title": "Juristi AI"}}
        if json_mode: kwargs["response_format"] = {"type": "json_object"}
        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message.content
    except Exception as e:
        logger.warning(f"⚠️ DeepSeek Call Failed: {e}")
        return None

def _call_local_llm(prompt: str, json_mode: bool = False) -> str:
    try:
        full_prompt = f"{STRICT_FORENSIC_RULES}\n\n{prompt}"
        payload = {"model": LOCAL_MODEL_NAME, "prompt": full_prompt, "stream": False, "options": {"temperature": 0.0, "num_ctx": 4096}, "format": "json" if json_mode else None}
        with httpx.Client(timeout=45.0) as client:
            response = client.post(OLLAMA_URL, json=payload)
            return response.json().get("response", "")
    except Exception as e:
        logger.warning(f"⚠️ Local LLM call failed: {e}")
        return ""

# --- PHOENIX V26.2: THE RESTORED & HARDENED PROMPT ---
LITIGATION_STRATEGIST_PROMPT = """
Ti je "Këshilltar i Lartë Gjyqësor", një ekspert në strategjinë e litigimit në Kosovë. Detyra jote është të analizosh tekstin e dosjes për të gjetur jo vetëm faktet, por edhe dobësitë, pikat e presionit dhe mundësitë taktike.

DETYRA: Analizo tekstin nga 'BAZA E LËNDËS' dhe prodho një raport strategjik.

**URDHËR PËR KRONOLOGJINË (PRIORITET ABSOLUT):**
Ti DUHET të identifikosh çdo datë të përmendur në dokumente (data e padisë, data e ngjarjes, data e martesës, data e faturave, etj.).
- Mos e lër kronologjinë bosh nëse ka data në tekst.
- Formati i datës: DD/MM/YYYY (ose MM/YYYY nëse mungon dita).

FORMATI JSON (STRICT):
{
  "summary_analysis": "Përmbledhje e lartë e situatës faktike dhe pretendimeve kryesore.",
  "chronology": [
    {"date": "DD/MM/YYYY", "event": "Ngjarja kryesore e verifikuar.", "source_doc": "Emri i Dokumentit"}
  ],
  "contradictions": [
    "Identifiko çdo mospërputhje faktike. Shembull: 'Paditësi deklaron X në Padi, por dokumenti Y tregon Z.'"
  ],
  "red_flags": [
    "Identifiko rreziqe procedurale, pretendime pa prova, ose afate të mundshme të humbura."
  ],
  "strategic_summary": "Një vlerësim i përgjithshëm i pikave të forta dhe të dobëta të rastit nga perspektiva jote.",
  "emotional_leverage_points": [
    "Analizo gjuhën për manipulim emocional dhe sugjero kundër-argumente."
  ],
  "financial_leverage_points": [
    "Analizo pretendimet financiare dhe pikat e tyre të dobëta."
  ],
  "suggested_questions": [
    "Formulo 2-3 pyetje strategjike për palën kundërshtare."
  ],
  "discovery_targets": [
    "Listo dokumente specifike që duhet të kërkohen nga pala kundërshtare ('Kërkesa për Prova')."
  ]
}
"""

def analyze_case_integrity(text: str) -> Dict[str, Any]:
    clean_text = sterilize_legal_text(text[:40000])
    system_prompt = LITIGATION_STRATEGIST_PROMPT
    user_prompt = f"TEKSTI I PLOTË I DOSJES (BAZA E LËNDËS):\n{clean_text}"
    content = _call_deepseek(system_prompt, user_prompt, json_mode=True)
    return _parse_json_safely(content) if content else {}

def perform_litigation_cross_examination(target_text: str, context_summaries: List[str]) -> Dict[str, Any]:
    clean_target = sterilize_legal_text(target_text[:25000])
    formatted_context = "\n".join([f"- {s}" for s in context_summaries if s])
    system_prompt = LITIGATION_STRATEGIST_PROMPT
    user_prompt = f"KONTEKSTI I DOSJES (PËRMBLEDHJE):\n{formatted_context}\n\nDOKUMENTI I RI PËR KRYQËZIM:\n{clean_target}"
    content = _call_deepseek(system_prompt, user_prompt, json_mode=True)
    return _parse_json_safely(content) if content else {}

def analyze_financial_summary(data_context: str) -> str:
    """
    Generates a consolidated, strategic narrative report from spreadsheet data.
    """
    system_prompt = """
    Ti je "Këshilltar Financiar-Ligjor". Analizo të dhënat statistikore me fokus në implikimet ligjore dhe strategjike.

    FORMATI I PËRGJIGJES (Narrative Profesionale, 3 Seksione):
    1. **PËRMBLEDHJE EKZEKUTIVE:** Përshkrim i shkurtër i të dhënave dhe gjetjeve kryesore.
    2. **ANALIZA E GJETJEVE KYÇE:** Detajo anomalitë dhe implikimet e tyre ligjore.
    3. **PLANI I VEPRIMIT:** Hapa konkretë për avokatin (kërkesa për prova, pyetje strategjike).
    """
    
    user_prompt = f"TË DHËNAT STATISTIKORE:\n{data_context}"
    
    res = _call_deepseek(system_prompt, user_prompt)
    if not res:
        fallback_system_prompt = "Ti je Analist Financiar. Analizo të dhënat dhe shkruaj një raport."
        res = _call_local_llm(f"{fallback_system_prompt}\n\n{user_prompt}")
        
    return res or "Analiza e detajuar financiare dështoi të gjenerohej."

def generate_summary(text: str) -> str:
    clean_text = sterilize_legal_text(text[:20000])
    system_prompt = "Ti je Analist Ligjor Forensik. Krijo një përmbledhje të shkurtër, objektive."
    user_prompt = f"DOKUMENTI:\n{clean_text}"
    res = _call_local_llm(f"{system_prompt}\n\n{user_prompt}")
    if not res or len(res) < 50: res = _call_deepseek(system_prompt, user_prompt)
    return res or "Nuk u gjenerua përmbledhje."

def extract_graph_data(text: str) -> Dict[str, List[Dict]]:
    clean_text = sterilize_legal_text(text[:15000])
    system_prompt = """Ti je "Graph Topology Architect". DETYRA: Ekstrakto entitetet dhe relacionet. FORMATI JSON: {"entities": [...], "relations": [...]}"""
    user_prompt = f"TEKSTI:\n{clean_text}"
    content = _call_deepseek(system_prompt, user_prompt, json_mode=True)
    if not content: content = _call_local_llm(f"{system_prompt}\n\n{user_prompt}", json_mode=True)
    parsed = _parse_json_safely(content) if content else {}
    return {"entities": parsed.get("entities", []), "relations": parsed.get("relations", [])}

def extract_deadlines_from_text(text: str) -> List[Dict[str, Any]]:
    clean_text = sterilize_legal_text(text[:15000])
    system_prompt = """Ti je "Legal Calendar Clerk". DETYRA: Identifiko afatet dhe seancat. FORMATI JSON: [{"title": "...", "date": "YYYY-MM-DD", "description": "..."}]"""
    user_prompt = f"TEKSTI:\n{clean_text}"
    content = _call_deepseek(system_prompt, user_prompt, json_mode=True)
    if not content: content = _call_local_llm(f"{system_prompt}\n\n{user_prompt}", json_mode=True)
    parsed = _parse_json_safely(content) if content else []
    if isinstance(parsed, list): return parsed
    if isinstance(parsed, dict) and "deadlines" in parsed: return parsed["deadlines"]
    return []