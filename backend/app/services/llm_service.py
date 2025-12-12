# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - INTELLIGENCE V9.5 (AGGRESSIVE STERILIZATION)
# 1. LOGIC: Decoupled the "Proposed Judgment" fix from the regex.
# 2. FEATURE: Global "Plaintiff Mode". If document starts with PADI, "Court Decided" becomes "Plaintiff Requests".
# 3. SAFETY: This prevents the AI from ever reading the phrase "Gjykata ka vendosur" in a lawsuit.

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
    
    # 1. OCR Corrections (Standard)
    replacements = {
        "Paditésja": "Paditësja", "paditésja": "paditësja",
        "Paditési": "Paditësi", "paditési": "paditësi",
        "Gjykatés": "Gjykatës", "gjykatés": "gjykatës"
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)

    # 2. DETECT DOCUMENT TYPE (THE "PLAINTIFF MODE" SWITCH)
    # Check the first 1000 chars for indicators that this is a Request/Lawsuit, not a Ruling.
    header_section = text[:1000].lower()
    is_lawsuit = "padi" in header_section or "paditës" in header_section
    
    clean_text = text

    # 3. THE "TRAP" REMOVER (Contextual)
    # Detects: PROPOZIM ... (some text) ... AKTGJYKIM
    # This pattern means it's a REQUEST, not a RULING.
    pattern = r"(?i)(propozoj|propozim)([\s\S]{0,1500}?)(aktgjykim)" # Increased range to 1500 chars
    
    def replacer(match):
        return f"{match.group(1)}{match.group(2)}DRAFT-PROPOZIM (KËRKESË E PALËS)"

    clean_text = re.sub(pattern, replacer, clean_text)
    
    # 4. AGGRESSIVE REWRITING (The "Nuclear" Option)
    # If we know this is a Padi, "Gjykata ka vendosur" is almost certainly the proposed text.
    if is_lawsuit or "DRAFT-PROPOZIM" in clean_text:
        # Replace definitive past tense with requested future tense
        clean_text = clean_text.replace("Gjykata ka vendosur", "Paditësi KËRKON që Gjykata të vendosë")
        clean_text = clean_text.replace("Gjykata vendos", "Paditësi KËRKON që Gjykata të vendosë")
        clean_text = clean_text.replace("vërtetohet se", "pretendohet se")
        
        # Specific fix for your example: "Gjykata ka vendosur që kontakti..."
        # Regex to catch variations like "Gjykata ka vendosur qe" (missing ë)
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

def generate_summary(text: str) -> str:
    # PHOENIX: Sterilize text first
    clean_text = sterilize_legal_text(text[:20000])
    
    system_prompt = "Ti je Analist Ligjor. Krijo një përmbledhje të shkurtër faktike."
    user_prompt = f"DOKUMENTI (Kujdes: Kjo mund të jetë Padi/Kërkesë):\n{clean_text}"
    
    res = _call_local_llm(f"{system_prompt}\n\n{user_prompt}")
    if not res or len(res) < 50: res = _call_deepseek(system_prompt, user_prompt)
    return res or "N/A"

def extract_findings_from_text(text: str) -> List[Dict[str, Any]]:
    # PHOENIX: Sterilize text first (Crucial for Findings)
    clean_text = sterilize_legal_text(text[:25000])
    
    system_prompt = """
    Ti je Motor i Nxjerrjes së Provave.
    
    DETYRA:
    Identifiko faktet dhe kërkesat.
    
    RREGULL I HEKURT:
    1. Nëse teksti thotë "Paditësi KËRKON" (edhe nëse më parë ishte 'Gjykata vendosi'), kjo është KËRKESË.
    2. Kujdes nga 'Proposed Judgment' (Draft-Propozim). Këto nuk janë fakte të vërtetuara.
    3. Kategorizo saktë: "KËRKESË" vs "VENDIM".
    
    FORMATI JSON:
    {
      "findings": [
        {
          "finding_text": "Paditësi kërkon rregullimin e kontaktit.",
          "source_text": "Paditësi KËRKON që Gjykata të vendosë...",
          "category": "KËRKESË", 
          "page_number": 1
        }
      ]
    }
    """
    user_prompt = f"ANALIZO KËTË DOKUMENT:\n{clean_text}"

    content = _call_deepseek(system_prompt, user_prompt, json_mode=True)
    if not content: content = _call_local_llm(f"{system_prompt}\n\n{user_prompt}", json_mode=True)
    
    if content:
        data = _parse_json_safely(content)
        if "findings" in data: return data["findings"]
        if isinstance(data, list): return data
    return []

def extract_graph_data(text: str) -> Dict[str, List[Dict]]:
    return {"entities": [], "relations": []}

def analyze_case_contradictions(text: str) -> Dict[str, Any]:
    # PHOENIX: Sterilize text first
    clean_text = sterilize_legal_text(text[:25000])
    
    system_prompt = """
    Ti je Gjyqtar i Debatit Ligjor.
    
    DETYRA:
    Analizo dokumentin. Dallo qartë midis PRETENDIMIT (Padi) dhe VENDIMIT (Aktgjykim).
    
    KUJDES:
    Teksti është përpunuar. Nëse lexon "Paditësi KËRKON", atëherë nuk ka vendim ende.
    
    FORMATI JSON:
    {
        "document_type": "PADI (Kërkesë) apo AKTGJYKIM (Vendim)?",
        "summary_analysis": "Analizë objektive.",
        "conflicting_parties": [{"party_name": "...", "core_claim": "..."}],
        "contradictions": ["..."],
        "key_evidence": ["..."],
        "missing_info": ["..."]
    }
    """
    user_prompt = f"DOSJA:\n{clean_text}"

    content = _call_deepseek(system_prompt, user_prompt, json_mode=True)
    if not content: content = _call_local_llm(f"{system_prompt}\n\n{user_prompt}", json_mode=True)

    if content: return _parse_json_safely(content)
    return {}

def generate_socratic_response(socratic_context: List[Dict], question: str) -> Dict:
    return {}
def extract_deadlines_from_text(text: str) -> List[Dict[str, Any]]:
    return []