# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - INTELLIGENCE V14.1 (SWITCHER COMPATIBILITY)
# 1. FIX: Added 'chronology' extraction to Cross-Examination (Document Mode).
# 2. RESULT: Timeline now appears even when analyzing a single document.

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
    if not text: return ""
    text = sterilize_text_for_llm(text, redact_names=False)

    replacements = {
        "Paditésja": "Paditësja", "paditésja": "paditësja",
        "Paditési": "Paditësi", "paditési": "paditësi",
        "Gjykatés": "Gjykatës", "gjykatés": "gjykatës"
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)

    header_section = text[:1000].lower()
    is_lawsuit = "padi" in header_section or "paditës" in header_section
    clean_text = text
    pattern = r"(?i)(propozoj|propozim)([\s\S]{0,1500}?)(aktgjykim)" 
    def replacer(match): return f"{match.group(1)}{match.group(2)}DRAFT-PROPOZIM (KËRKESË E PALËS)"
    clean_text = re.sub(pattern, replacer, clean_text)
    
    if is_lawsuit or "DRAFT-PROPOZIM" in clean_text:
        clean_text = clean_text.replace("Gjykata ka vendosur", "Paditësi KËRKON që Gjykata të vendosë")
        clean_text = clean_text.replace("Gjykata vendos", "Paditësi KËRKON që Gjykata të vendosë")
        clean_text = clean_text.replace("vërtetohet se", "pretendohet se")
        clean_text = re.sub(r"(?i)gjykata\s+ka\s+vendosur\s+q[ëe]", "Paditësi kërkon që", clean_text)

    return clean_text

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
    clean_text = sterilize_legal_text(text[:20000])
    system_prompt = "Ti je Analist Ligjor. Krijo një përmbledhje të shkurtër faktike duke theksuar Datat Kryesore."
    user_prompt = f"DOKUMENTI:\n{clean_text}"
    res = _call_local_llm(f"{system_prompt}\n\n{user_prompt}")
    if not res or len(res) < 50: res = _call_deepseek(system_prompt, user_prompt)
    return res or "N/A"

def extract_findings_from_text(text: str) -> List[Dict[str, Any]]:
    clean_text = sterilize_legal_text(text[:25000])
    system_prompt = """
    Ti je "Forensic Document Examiner".
    DETYRA: Skano dokumentin dhe nxirr fakte, shifra, emra, data (DD/MM/YYYY).
    FORMATI JSON: 
    {"findings": [{"finding_text": "Fakti...", "source_text": "Origjinali...", "category": "PROVË", "page_number": 1}]}
    """
    user_prompt = f"DOKUMENTI:\n{clean_text}"
    content = _call_deepseek(system_prompt, user_prompt, json_mode=True)
    if not content: content = _call_local_llm(f"{system_prompt}\n\n{user_prompt}", json_mode=True)
    if content:
        data = _parse_json_safely(content)
        return data.get("findings", []) if isinstance(data, dict) else []
    return []

def analyze_case_contradictions(text: str) -> Dict[str, Any]:
    clean_text = sterilize_legal_text(text[:25000])
    system_prompt = """
    Ti je 'The Auditor'.
    DETYRA: Analizo dosjen dhe krijo Timeline.
    FORMATI JSON:
    {
        "document_type": "Përmbledhje Dosjeje",
        "summary_analysis": "Analiza...",
        "chronology": [{"date": "DD/MM/YYYY", "event": "Ngjarja...", "source_doc": "Dokumenti A"}],
        "conflicting_parties": [{"party_name": "Emri", "core_claim": "Pretendimi"}],
        "contradictions": ["Kontradikta..."],
        "key_evidence": [],
        "missing_info": []
    }
    """
    user_prompt = f"DOSJA:\n{clean_text}"
    content = _call_deepseek(system_prompt, user_prompt, json_mode=True)
    if not content: content = _call_local_llm(f"{system_prompt}\n\n{user_prompt}", json_mode=True)
    return _parse_json_safely(content) if content else {}

# PHOENIX FIX: Added Chronology to Cross-Examination
def perform_litigation_cross_examination(target_text: str, context_summaries: List[str]) -> Dict[str, Any]:
    clean_target = sterilize_legal_text(target_text[:25000])
    formatted_context = "\n".join([f"- {s}" for s in context_summaries if s])
    
    system_prompt = """
    Ti je "Phoenix" - Avokat Mbrojtës.
    
    DETYRA: Kryqëzo dokumentin [TARGET] me [DOSJEN].
    
    UDHËZIME SHTESË PËR KRONOLOGJINË:
    1. Nxirr "Kronologjinë e Dokumentit" - Datat që përmenden vetëm në këtë dokument specifik.
    2. Kjo ndihmon të shohim se ku futet ky dokument në kohë.

    FORMATI JSON (Strict):
    {
        "summary_analysis": "Analizë e besueshmërisë dhe konsistencës kohore.",
        "chronology": [
            {"date": "DD/MM/YYYY", "event": "Data e lëshimit/ngjarjes në dokument.", "source_doc": "Target Document"}
        ],
        "conflicting_parties": [
            {"party_name": "Emri", "core_claim": "Deklarata në këtë dokument."}
        ],
        "contradictions": [
            "KONTRADIKTË KOHORE: Target thotë 'Maj 2023', Dosja provon 'Qershor 2023'."
        ],
        "suggested_questions": [
            "Z. [Mbiemri], pse data e përmendur këtu nuk përputhet me faturën e datës X?"
        ],
        "discovery_targets": [],
        "key_evidence": []
    }
    """
    user_prompt = f"[CONTEXT] (Fakte nga Dosja):\n{formatted_context}\n\n[TARGET] (Dokumenti i Ri):\n{clean_target}"
    content = _call_deepseek(system_prompt, user_prompt, json_mode=True)
    if not content: content = _call_local_llm(f"{system_prompt}\n\n{user_prompt}", json_mode=True)
    return _parse_json_safely(content) if content else {}

def synthesize_and_deduplicate_findings(raw_findings: List[str]) -> List[Dict[str, Any]]:
    joined_findings = "\n".join(raw_findings[:100]) 
    system_prompt = """
    Ti je "Arkivi Qendror". GRUPO dhe SHKRIJ faktet.
    FORMATI JSON: {"synthesized_findings": [{"finding_text": "...", "source_documents": ["..."], "category": "..."}]}
    """
    user_prompt = f"FAKTET BRUTO:\n{joined_findings}"
    content = _call_deepseek(system_prompt, user_prompt, json_mode=True)
    if not content: content = _call_local_llm(f"{system_prompt}\n\n{user_prompt}", json_mode=True)
    if content:
        data = _parse_json_safely(content)
        return data.get("synthesized_findings", [])
    return []

def extract_graph_data(text: str) -> Dict[str, List[Dict]]: return {"entities": [], "relations": []}
def generate_socratic_response(socratic_context: List[Dict], question: str) -> Dict: return {}
def extract_deadlines_from_text(text: str) -> List[Dict[str, Any]]: return []