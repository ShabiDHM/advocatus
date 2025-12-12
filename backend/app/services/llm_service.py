# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - INTELLIGENCE V9.0 (LEGAL STERILIZATION MODE)
# 1. NEW: 'sterilize_legal_text' function. explicitly renames "Proposed Judgment" to "Plaintiff Request".
# 2. LOGIC: Mechanically prevents the AI from seeing "Gjykata vendos" in a proposal section.
# 3. SAFETY: Enforces JSON strictness for findings.

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
        "Paditési": "Paditësi", "paditési": "paditësi"
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)

    # 2. THE "TRAP" REMOVER
    # Detects: PROPOZIM ... (some text) ... AKTGJYKIM
    # This pattern means it's a REQUEST, not a RULING.
    
    # Regex explanation:
    # (?i) -> Case insensitive
    # (propozoj|propozim) -> Trigger words
    # [\s\S]{0,500}? -> Scans next 500 chars (non-greedy)
    # (aktgjykim) -> The dangerous word
    
    pattern = r"(?i)(propozoj|propozim)([\s\S]{0,500}?)(aktgjykim)"
    
    def replacer(match):
        # Keep the 'Propozim', keep the middle text, but CHANGE 'Aktgjykim'
        return f"{match.group(1)}{match.group(2)}DRAFT-PROPOZIM (KËRKESË E PALËS)"

    # Apply sterilization
    clean_text = re.sub(pattern, replacer, text)
    
    # Also explicitly label the "Decided" verb in proposals
    # Common phrase: "Gjykata... të vendosë" or "Gjykata ka vendosur" (in draft)
    if "DRAFT-PROPOZIM" in clean_text:
        clean_text = clean_text.replace("Gjykata ka vendosur", "Paditësi kërkon që Gjykata të vendosë")
        clean_text = clean_text.replace("Gjykata vendos", "Paditësi propozon që Gjykata të vendosë")

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
    user_prompt = f"DOKUMENTI:\n{clean_text}"
    
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
    - Nëse teksti thotë "DRAFT-PROPOZIM" ose "Paditësi kërkon", kjo është KËRKESË (Request), JO FAKT (Fact).
    - Kategorizo: "KËRKESË" për çdo gjë që palët duan, "VENDIM" vetëm nëse është Vulë Gjykate.
    
    FORMATI JSON:
    {
      "findings": [
        {
          "finding_text": "Paditësi kërkon kontakt çdo të mërkurë.",
          "source_text": "Propozojmë kontakt... çdo të mërkurë.",
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
    Ti je Gjyqtar i Debatit Ligjor (Audit Mode).
    
    DETYRA:
    Analizo dokumentin. Dallo qartë midis PRETENDIMIT dhe VENDIMIT.
    
    RREGULL:
    - Teksti përmban shënime si "DRAFT-PROPOZIM". Kjo tregon se është kërkesë e palës, jo vendim.
    - Nëse gjen kontradikta (p.sh. Palët thonë gjëra të ndryshme), shënoji.
    
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