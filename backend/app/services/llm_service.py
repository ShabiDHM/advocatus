# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - CORE INTELLIGENCE V24.0 (DEPOSITION ANALYST)
# 1. ADDED: analyze_deposition_transcript method.
# 2. PROMPT: specialized 'Forensic Psychologist' persona.

import os
import json
import logging
import httpx
import re
from typing import List, Dict, Any, Optional
from openai import OpenAI 

from .text_sterilization_service import sterilize_text_for_llm

logger = logging.getLogger(__name__)

# ... (Configuration and Base Methods remain unchanged: get_deepseek_client, _call_deepseek, etc.)
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat"
OLLAMA_URL = os.environ.get("LOCAL_LLM_URL", "http://local-llm:11434/api/generate")
LOCAL_MODEL_NAME = "llama3"

_deepseek_client: Optional[OpenAI] = None

STRICT_FORENSIC_RULES = """
RREGULLAT E AUDITIMIT (STRICT LIABILITY):
1. HIERARKIA E BURIMEVE: GLOBAL KB (LIGJI), CASE KB (FAKTET).
2. ZERO HALUCINACIONE.
3. RREGULLI I HESHTJES.
4. CITIM I DETYRUESHËM.
5. GJUHA: Shqipe Standarde.
6. JURIDIKSIONI: Kosovë.
"""

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

def sterilize_legal_text(text: str) -> str:
    if not text: return ""
    text = sterilize_text_for_llm(text, redact_names=False)
    text = re.sub(r'--- \[Page (\d+)\] ---', r'--- [FAQJA \1] ---', text)
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
        kwargs = {
            "model": OPENROUTER_MODEL,
            "messages": [{"role": "system", "content": full_system_prompt}, {"role": "user", "content": user_prompt}],
            "temperature": 0.0,
            "extra_headers": {"HTTP-Referer": "https://juristi.tech", "X-Title": "Juristi AI"}
        }
        if json_mode: kwargs["response_format"] = {"type": "json_object"}
        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message.content
    except Exception as e:
        logger.warning(f"⚠️ DeepSeek Call Failed: {e}")
        return None

def _call_local_llm(prompt: str, json_mode: bool = False) -> str:
    try:
        full_prompt = f"{STRICT_FORENSIC_RULES}\n\n{prompt}"
        payload = {
            "model": LOCAL_MODEL_NAME,
            "prompt": full_prompt,
            "stream": False,
            "options": {"temperature": 0.0, "num_ctx": 4096},
            "format": "json" if json_mode else None
        }
        with httpx.Client(timeout=45.0) as client:
            response = client.post(OLLAMA_URL, json=payload)
            return response.json().get("response", "")
    except Exception: return ""

# --- EXISTING METHODS (Summary, Integrity, Cross-Exam, Dual-Source, Financial) ---
def generate_summary(text: str) -> str:
    # ... (Keep existing implementation)
    return "Summary Placeholder" # Abbreviated for this response

def analyze_case_integrity(text: str) -> Dict[str, Any]:
    # ... (Keep existing implementation)
    return {}

def perform_litigation_cross_examination(target_text: str, context_summaries: List[str]) -> Dict[str, Any]:
    # ... (Keep existing implementation)
    return {}

def perform_dual_source_analysis(query: str, case_context: str, global_context: str) -> Dict[str, Any]:
    # ... (Keep existing implementation)
    return {}

def analyze_financial_summary(data_context: str) -> str:
    # ... (Keep existing implementation)
    return ""

# --- NEW: DEPOSITION ANALYST ---
def analyze_deposition_transcript(transcript_text: str) -> Dict[str, Any]:
    """
    Analyzes a witness transcript for psycholinguistic markers and contradictions.
    """
    clean_text = sterilize_legal_text(transcript_text[:30000])
    
    system_prompt = """
    Ti je "Phoenix Forensic Psychologist" dhe "Ekspert i Kryqëzimit (Cross-Examination)".
    
    DETYRA:
    Analizo transkriptin e dëshmisë/intervistës. Kërko për:
    1. Kontradikta logjike ose ndryshime në histori.
    2. Tregues psikolinguistikë të mashtrimit (hezitim, distancim, gjuhë tepër emocionale).
    3. Pika të dobëta ku avokati duhet të sulmojë.
    
    FORMATI JSON (Strict):
    {
        "witness_name": "Emri i Dëshmitarit (nëse gjendet)",
        "credibility_score": 75, (0-100, ku 100 është plotësisht i besueshëm),
        "summary": "Përmbledhje e dëshmisë dhe sjelljes.",
        "inconsistencies": [
            {
                "statement": "Tha se ishte në shtëpi.",
                "contradiction": "Më vonë tha se doli për cigare.",
                "source_ref": "Faqja 2",
                "severity": "HIGH"
            }
        ],
        "emotional_segments": [
            {
                "segment": "Nuk e di... ndoshta... s'më kujtohet saktë.",
                "emotion": "HESITATION", (ANGER, FEAR, CONFUSION, DECEPTION_INDICATOR),
                "analysis": "Përdorimi i fjalëve evazive sugjeron fshehje të informacionit."
            }
        ],
        "suggested_questions": [
            {
                "question": "Z. Dëshmitar, a mund të shpjegoni pse telefonata juaj u regjistrua në Pejë kur thatë se ishit në Prishtinë?",
                "rationale": "Përballje direkte me provën teknike.",
                "strategy": "TRAP" (TRAP, CLARIFY, PRESSURE, DISCREDIT)
            }
        ],
        "processed_at": "timestamp"
    }
    """
    
    user_prompt = f"TRANSKRIPTI PËR ANALIZË:\n{clean_text}"
    
    content = _call_deepseek(system_prompt, user_prompt, json_mode=True)
    if not content:
        content = _call_local_llm(f"{system_prompt}\n\n{user_prompt}", json_mode=True)
        
    return _parse_json_safely(content) if content else {}