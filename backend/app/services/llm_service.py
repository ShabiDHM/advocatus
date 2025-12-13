# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - INTELLIGENCE V11.0 (LANGUAGE: ALBANIAN STRICT)
# 1. FIX: Enforced "OUTPUT LANGUAGE: ALBANIAN" in all System Prompts.
# 2. LOGIC: Keeps JSON keys in English (for code safety) but Values are Albanian.

import os
import json
import logging
import httpx
import re
from typing import List, Dict, Any, Optional
from openai import OpenAI 

logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat"
OLLAMA_URL = os.environ.get("LOCAL_LLM_URL", "http://local-llm:11434/api/generate")
LOCAL_MODEL_NAME = "llama3"

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
    """
    CRITICAL FUNCTION:
    Modifies the text BEFORE the AI sees it to prevent 'Proposed Judgment' hallucinations.
    """
    if not text: return ""
    
    # 1. OCR Corrections
    replacements = {
        "Paditésja": "Paditësja", "paditésja": "paditësja",
        "Paditési": "Paditësi", "paditési": "paditësi",
        "Gjykatés": "Gjykatës", "gjykatés": "gjykatës"
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)

    # 2. DETECT DOCUMENT TYPE
    header_section = text[:1000].lower()
    is_lawsuit = "padi" in header_section or "paditës" in header_section
    
    clean_text = text

    # 3. THE "TRAP" REMOVER
    pattern = r"(?i)(propozoj|propozim)([\s\S]{0,1500}?)(aktgjykim)" 
    def replacer(match):
        return f"{match.group(1)}{match.group(2)}DRAFT-PROPOZIM (KËRKESË E PALËS)"
    clean_text = re.sub(pattern, replacer, clean_text)
    
    # 4. AGGRESSIVE REWRITING
    if is_lawsuit or "DRAFT-PROPOZIM" in clean_text:
        clean_text = clean_text.replace("Gjykata ka vendosur", "Paditësi KËRKON që Gjykata të vendosë")
        clean_text = clean_text.replace("Gjykata vendos", "Paditësi KËRKON që Gjykata të vendosë")
        clean_text = clean_text.replace("vërtetohet se", "pretendohet se")
        clean_text = re.sub(r"(?i)gjykata\s+ka\s+vendosur\s+q[ëe]", "Paditësi kërkon që", clean_text)

    return clean_text

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

def _call_deepseek(system_prompt: str, user_prompt: str, json_mode: bool = False) -> Optional[str]:
    client = get_deepseek_client()
    if not client: return None
    try:
        kwargs = {
            "model": OPENROUTER_MODEL,
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
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
        payload = {
            "model": LOCAL_MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.0, "num_ctx": 4096},
            "format": "json" if json_mode else None
        }
        with httpx.Client(timeout=45.0) as client:
            response = client.post(OLLAMA_URL, json=payload)
            return response.json().get("response", "")
    except Exception: return ""

# --- STANDARD ANALYSIS ---

def generate_summary(text: str) -> str:
    clean_text = sterilize_legal_text(text[:20000])
    # FORCE ALBANIAN
    system_prompt = "Ti je Analist Ligjor. Krijo një përmbledhje të shkurtër faktike. GJUHA: SHQIP."
    user_prompt = f"DOKUMENTI (Përgjigju vetëm SHQIP):\n{clean_text}"
    res = _call_local_llm(f"{system_prompt}\n\n{user_prompt}")
    if not res or len(res) < 50: res = _call_deepseek(system_prompt, user_prompt)
    return res or "N/A"

def extract_findings_from_text(text: str) -> List[Dict[str, Any]]:
    clean_text = sterilize_legal_text(text[:25000])
    system_prompt = """
    Ti je Motor i Nxjerrjes së Provave.
    DETYRA: Identifiko faktet dhe kërkesat.
    GJUHA: Të gjitha vlerat 'finding_text' dhe 'source_text' DUHET TË JENË NË SHQIP.
    
    FORMATI JSON: {"findings": [{"finding_text": "...", "source_text": "...", "category": "KËRKESË", "page_number": 1}]}
    """
    user_prompt = f"ANALIZO KËTË DOKUMENT (Përgjigju SHQIP):\n{clean_text}"
    content = _call_deepseek(system_prompt, user_prompt, json_mode=True)
    if not content: content = _call_local_llm(f"{system_prompt}\n\n{user_prompt}", json_mode=True)
    if content:
        data = _parse_json_safely(content)
        return data.get("findings", []) if isinstance(data, dict) else []
    return []

def analyze_case_contradictions(text: str) -> Dict[str, Any]:
    # This is the whole-case analysis
    clean_text = sterilize_legal_text(text[:25000])
    system_prompt = """
    Ti je Gjyqtar i Debatit Ligjor.
    DETYRA: Analizo dokumentin për kontradikta.
    GJUHA E PËRGJIGJES: SHQIP (Strictly Albanian).
    
    FORMATI JSON: {
        "document_type": "...",
        "summary_analysis": "Analizë në SHQIP...",
        "conflicting_parties": [{"party_name": "...", "core_claim": "..."}],
        "contradictions": ["..."],
        "key_evidence": ["..."],
        "missing_info": ["..."]
    }
    """
    user_prompt = f"DOSJA:\n{clean_text}"
    content = _call_deepseek(system_prompt, user_prompt, json_mode=True)
    if not content: content = _call_local_llm(f"{system_prompt}\n\n{user_prompt}", json_mode=True)
    return _parse_json_safely(content) if content else {}

# --- PHOENIX LITIGATION ENGINE (PHASE 1 & 2) ---

def perform_litigation_cross_examination(target_text: str, context_summaries: List[str]) -> Dict[str, Any]:
    """
    Compares ONE document (Target) against ALL other summaries (Context).
    Generates: Contradictions, Questions, Discovery Targets.
    LANGUAGE: FORCED ALBANIAN.
    """
    # 1. Sterilize
    clean_target = sterilize_legal_text(target_text[:25000])
    
    # 2. Format Context
    formatted_context = "\n".join([f"- {s}" for s in context_summaries if s])
    
    system_prompt = """
    Ti je 'Phoenix' - Një Avokat Strategjik Mbrojtës (Litigator) për tregun e Kosovës.
    
    DETYRA:
    Kryqëzo 'DËSHMINË E RE' (Target) me 'FAKTET E DOSJES' (Context).
    
    RREGULL I PANIGOCIUESHËM GJUHËSOR:
    DËSHMO DHE SHKRUAJ VETËM NË GJUHËN SHQIPE. Mos përdor anglisht.
    Edhe nëse dokumentet janë anglisht, përgjigja duhet të jetë SHQIP.

    OBJEKTIVAT:
    1. Gjej çdo kontradiktë midis Targetit dhe Kontekstit.
    2. Gjej pretendime në Target që nuk mbështeten nga Konteksti.
    3. Përpilo Pyetje Strategjike për të sulmuar dëshmitarin/palën.
    4. Sugjero Dokumente (Discovery) që duhen kërkuar.

    FORMATI STRIKT JSON (Çelësat Anglisht, Vlerat SHQIP):
    {
        "summary_analysis": "Një paragraf i fuqishëm mbi besueshmërinë e këtij dokumenti (SHQIP).",
        "contradictions": [
            "Dokumenti thotë X, por Faktet thonë Y (SHQIP)."
        ],
        "suggested_questions": [
            "Z. Dëshmitar, ju deklaruat X, por banka tregon Y. Si e shpjegoni? (SHQIP)"
        ],
        "discovery_targets": [
            "Kërkohen pasqyrat bankare të vitit 2023... (SHQIP)"
        ],
        "key_evidence": [
            "Fakti i pranuar në paragrafin 3 (SHQIP)."
        ],
         "conflicting_parties": [
             {"party_name": "Emri", "core_claim": "Pretendimi (SHQIP)"}
         ]
    }
    """
    
    user_prompt = f"""
    [FAKTET E VENDOSURA (CONTEXT)]
    {formatted_context}
    
    [DËSHMIA E RE PËR T'U HETUAR (TARGET)]
    {clean_target}
    """

    content = _call_deepseek(system_prompt, user_prompt, json_mode=True)
    
    # Fallback to local
    if not content: 
        content = _call_local_llm(f"{system_prompt}\n\n{user_prompt}", json_mode=True)

    if content:
        return _parse_json_safely(content)
    
    return {
        "summary_analysis": "Analiza dështoi.",
        "contradictions": [],
        "suggested_questions": [],
        "discovery_targets": []
    }

def extract_graph_data(text: str) -> Dict[str, List[Dict]]:
    return {"entities": [], "relations": []}
def generate_socratic_response(socratic_context: List[Dict], question: str) -> Dict:
    return {}
def extract_deadlines_from_text(text: str) -> List[Dict[str, Any]]:
    return []