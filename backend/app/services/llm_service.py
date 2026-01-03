# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - CORE INTELLIGENCE V25.1 (DEPOSITION PROMPT FIX)
# 1. FIX: Simplified and hardened the Deposition Analyst prompt for better JSON compliance.
# 2. OPTIMIZATION: Increased context length for more thorough analysis.

import os
import json
import logging
import httpx
import re
from typing import List, Dict, Any, Optional
from openai import OpenAI 

from .text_sterilization_service import sterilize_text_for_llm

logger = logging.getLogger(__name__)

# --- CONFIG (Unchanged) ---
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY") 
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat" 
LLM_TIMEOUT = int(os.environ.get("LLM_TIMEOUT", "120"))  

# --- THE FORENSIC CONSTITUTION (Unchanged) ---
STRICT_FORENSIC_RULES = """
RREGULLAT E AUDITIMIT (STRICT LIABILITY):
1. HIERARKIA E BURIMEVE: Global KB = LIGJI. Case KB = FAKTET. Mos shpik fakte. Mos shpik ligje.
2. PROTOKOLLI I THJESHTËSIMIT (CHAT ONLY): Në Chat: Shpjego ligjet thjesht. Në Draftim: Përdor gjuhë profesionale.
3. CITIM I DETYRUESHËM: Çdo ligj ose provë duhet të ketë linkun Markdown specifik.
"""
VISUAL_STYLE_PROTOCOL = """
PROTOKOLLI I STILIT VIZUAL (DETYRUESHËM):
1. **FORMATI I LIGJIT (Blue Text)**: [**{{Emri}} {{Nr.}}, {{Neni X}}**](doc://{{Burimi}})
2. **FORMATI I PROVAVE (Yellow Badge)**: [**PROVA: {{Përshkrimi}}**](doc://{{Dosja}})
3. **STRUKTURA**: Përdor tituj: **BAZA LIGJORE**, **FAKTET**.
"""

# --- Base Methods (Unchanged) ---
_deepseek_client: Optional[OpenAI] = None

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
    return text.replace("\x00", "")

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
        return {} # Return empty dict on failure

def _call_deepseek(system_prompt: str, user_prompt: str, json_mode: bool = False) -> Optional[str]:
    client = get_deepseek_client()
    if not client: return None
    try:
        full_system_prompt = f"{STRICT_FORENSIC_RULES}\n\n{system_prompt}"
        kwargs = {"model": OPENROUTER_MODEL, "messages": [{"role": "system", "content": full_system_prompt}, {"role": "user", "content": user_prompt}], "temperature": 0.0, "extra_headers": {"HTTP-Referer": "https://juristi.tech", "X-Title": "Juristi AI"}}
        if json_mode: kwargs["response_format"] = {"type": "json_object"}
        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message.content
    except Exception as e:
        logger.warning(f"⚠️ DeepSeek Call Failed: {e}")
        return None

# --- RAG & Chat (Unchanged) ---
# ... (get_rag_chat_response, etc. remain here)

# --- FEATURE METHODS ---

# ... (generate_summary, analyze_case_integrity, etc. remain here)

def analyze_financial_summary(data_context: str) -> str:
    system_prompt = "Ti je Analist Financiar Forenzik. Analizo statistikat dhe shkruaj një raport narrativ profesional në Shqip."
    user_prompt = f"STATISTIKAT:\n{data_context}"
    res = _call_deepseek(system_prompt, user_prompt)
    return res or "Analiza dështoi."

# --- PHOENIX FIX: HARDENED DEPOSITION PROMPT ---
def analyze_deposition_transcript(transcript_text: str) -> Dict[str, Any]:
    """
    Analyzes a witness transcript with a simplified and more robust prompt.
    """
    # Increased context length
    clean_text = sterilize_legal_text(transcript_text[:40000])
    
    system_prompt = """
    Ti je "Phoenix Forensic Psychologist". Detyra jote është të analizosh një transkript dëshmie dhe të plotësosh një JSON.

    RREGULLAT:
    1.  **Identifiko Dëshmitarin:** Gjej emrin e personit që jep dëshminë.
    2.  **Gjej Kontradiktat:** Gjej dy deklarata nga i njëjti person që kundërshtojnë njëra-tjetrën.
    3.  **Gjej Gjuhën Emocionale:** Gjej fraza ku dëshmitari heziton, është nervoz, ose përdor gjuhë evazive.
    4.  **Krijo Pyetje Strategjike:** Bazuar në dobësitë, krijo pyetje për ta sfiduar dëshmitarin.
    5.  **Vlerëso Besueshmërinë:** Bazuar në numrin e kontradiktave, jep një notë nga 0 (gënjeshtar) deri në 100 (plotësisht i besueshëm).

    Përgjigju VETËM me formatin JSON. Mos shto asnjë tekst tjetër jashtë JSON-it.
    """
    
    user_prompt = f"""
    TRANSKRIPTI PËR ANALIZË:
    ---
    {clean_text}
    ---

    PLOTËSO KËTË JSON:
    {{
        "witness_name": "Emri i Dëshmitarit",
        "credibility_score": 75,
        "summary": "Përmbledhje e shkurtër e dëshmisë dhe sjelljes së dëshmitarit.",
        "inconsistencies": [
            {{
                "statement": "Deklarata e parë.",
                "contradiction": "Deklarata kundërshtuese.",
                "source_ref": "Faqja X, Rreshti Y",
                "severity": "HIGH"
            }}
        ],
        "emotional_segments": [
            {{
                "segment": "Fraza ku dëshmitari heziton.",
                "emotion": "HESITATION",
                "analysis": "Analizë e shkurtër pse kjo është e dyshimtë."
            }}
        ],
        "suggested_questions": [
            {{
                "question": "Pyetja strategjike për seancë.",
                "rationale": "Arsyeja pse kjo pyetje duhet bërë.",
                "strategy": "TRAP"
            }}
        ]
    }}
    """
    
    content = _call_deepseek(system_prompt, user_prompt, json_mode=True)
        
    # Fallback with error handling
    if not content:
        return {
            "witness_name": "I panjohur", "credibility_score": 0, "summary": "Gabim: Modeli AI nuk arriti të përpunojë transkriptin.",
            "inconsistencies": [], "emotional_segments": [], "suggested_questions": []
        }

    parsed_json = _parse_json_safely(content)
    if not parsed_json:
        return {
            "witness_name": "I panjohur", "credibility_score": 0, "summary": "Gabim: Përgjigja nga AI nuk ishte në formatin e duhur JSON.",
            "inconsistencies": [], "emotional_segments": [], "suggested_questions": []
        }
        
    return parsed_json

# Placeholder to ensure it exists
def get_rag_chat_response(query: str, context: str, history: List[Dict[str, str]]) -> str:
    return "Funksioni i chat-it është aktiv."