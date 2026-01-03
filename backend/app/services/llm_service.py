# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - CORE INTELLIGENCE V23.2 (SPREADSHEET ANALYST)
# 1. ADDED: analyze_financial_summary method.
# 2. STATUS: Integrated with SpreadsheetService.

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

# --- THE FORENSIC CONSTITUTION (MASTER COPY) ---
STRICT_FORENSIC_RULES = """
RREGULLAT E AUDITIMIT (STRICT LIABILITY):

1. HIERARKIA E BURIMEVE (THE SOURCE HIERARCHY):
   - GLOBAL KNOWLEDGE BASE = LIGJI (The Law). Kjo përmban rregullat, nenet dhe precedentët.
   - CASE KNOWLEDGE BASE = FAKTET (The Facts). Kjo përmban vetëm dokumentet që ndodhen në "Document Panel" të dosjes.
   - URDHËR: Ti nuk guxon të shpikësh fakte. Faktet merren VETËM nga CASE KNOWLEDGE BASE.
   - URDHËR: Ti nuk guxon të shpikësh ligje. Ligjet merren VETËM nga GLOBAL KNOWLEDGE BASE.

2. ZERO HALUCINACIONE: Nëse fakti nuk ekziston në "Case Knowledge Base", shkruaj "NUK KA TË DHËNA NË DOSJE".
3. RREGULLI I HESHTJES (THE SILENT PARTY RULE): 
   - Nëse kemi vetëm Padinë, I Padituri "NUK KA PARAQITUR PËRGJIGJE". Mos shpik mbrojtje për të.
4. CITIM I DETYRUESHËM:
   - Çdo pretendim faktik duhet të ketë referencën: [Fq. X] ose [Burimi].
5. GJUHA: Përdor Shqipe Standarde (e, ë, ç).
6. JURIDIKSIONI: Republika e Kosovës.
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
    replacements = {
        "Paditésja": "Paditësja", "paditésja": "paditësja",
        "Paditési": "Paditësi", "paditési": "paditësi",
        "Gjykatés": "Gjykatës", "gjykatés": "gjykatës"
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)
    clean_text = text
    pattern = r"(?i)(propozoj|propozim)([\s\S]{0,1500}?)(aktgjykim)" 
    def replacer(match): return f"{match.group(1)}{match.group(2)}DRAFT-PROPOZIM (KËRKESË E PALËS - JO VENDIM)"
    clean_text = re.sub(pattern, replacer, clean_text)
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

# --- PUBLIC SERVICES ---

def generate_summary(text: str) -> str:
    clean_text = sterilize_legal_text(text[:20000])
    system_prompt = "Ti je Analist Ligjor Forensik. Krijo një përmbledhje të shkurtër, objektive. Përmend statusin procedural (psh: 'Padi e dorëzuar', 'Aktgjykim i plotfuqishëm')."
    user_prompt = f"DOKUMENTI:\n{clean_text}"
    res = _call_local_llm(f"{system_prompt}\n\n{user_prompt}")
    if not res or len(res) < 50: 
        res = _call_deepseek(system_prompt, user_prompt)
    return res or "Nuk u gjenerua përmbledhje."

def analyze_case_integrity(text: str) -> Dict[str, Any]:
    clean_text = sterilize_legal_text(text[:30000])
    system_prompt = """
    Ti je "Gjykatës Suprem & Detektiv Hetues".
    DETYRA: Analizo tekstin rresht për rresht (CASE KNOWLEDGE BASE). Identifiko palët, datat dhe kontradiktat.
    FORMATI JSON (Strict):
    {
        "document_type": "Përcakto llojin",
        "active_parties": ["Lista e palëve"],
        "silent_parties": ["Lista e palëve pa dokumente"],
        "summary_analysis": "Përmbledhje e statusit.",
        "judicial_observation": "Opinion neutral.",
        "red_flags": ["Rreziqe konkrete."],
        "chronology": [{"date": "DD/MM/YYYY", "event": "...", "source_doc": "..."}],
        "contradictions": ["Mospërputhje faktike."],
        "key_evidence": [],
        "missing_info": []
    }
    """
    user_prompt = f"DOSJA E PLOTË (CASE KNOWLEDGE BASE):\n{clean_text}"
    content = _call_deepseek(system_prompt, user_prompt, json_mode=True)
    if not content: content = _call_local_llm(f"{system_prompt}\n\n{user_prompt}", json_mode=True)
    return _parse_json_safely(content) if content else {}

def perform_litigation_cross_examination(target_text: str, context_summaries: List[str]) -> Dict[str, Any]:
    clean_target = sterilize_legal_text(target_text[:25000])
    formatted_context = "\n".join([f"- {s}" for s in context_summaries if s])
    system_prompt = """
    Ti je "Phoenix Litigation Engine".
    DETYRA: Kryqëzo dokumentin e ri [TARGET] me historikun e dosjes [CASE KNOWLEDGE BASE]. Gjej mospërputhje.
    FORMATI JSON (Strict):
    {
        "summary_analysis": "Analizë koherencës.",
        "judicial_observation": "Vlerësim besueshmërie.",
        "red_flags": ["Rreziqe."],
        "chronology": [{"date": "...", "event": "..."}],
        "conflicting_parties": [{"party_name": "...", "core_claim": "..."}],
        "contradictions": ["Fakte kundërthënëse."],
        "suggested_questions": ["Pyetje për seancë."],
        "discovery_targets": ["Dokumente shtesë."]
    }
    """
    user_prompt = f"[CASE KNOWLEDGE BASE]:\n{formatted_context}\n\n[TARGET]:\n{clean_target}"
    content = _call_deepseek(system_prompt, user_prompt, json_mode=True)
    if not content: content = _call_local_llm(f"{system_prompt}\n\n{user_prompt}", json_mode=True)
    return _parse_json_safely(content) if content else {}

def perform_dual_source_analysis(query: str, case_context: str, global_context: str) -> Dict[str, Any]:
    clean_case = sterilize_legal_text(case_context[:20000])
    clean_global = sterilize_legal_text(global_context[:10000])
    system_prompt = """
    Ti je "Phoenix Legal Architect".
    BURIMET: 1. GLOBAL KB (LIGJI). 2. CASE KB (FAKTET).
    DETYRA: Përgjigju pyetjes duke aplikuar LIGJIN mbi FAKTET.
    FORMATI JSON (Strict):
    {
        "direct_answer": "Përgjigja.",
        "legal_basis": ["Nenet."],
        "factual_basis": ["Faktet."],
        "missing_facts": ["Çfarë mungon?"],
        "strategy": "Sugjerim."
    }
    """
    user_prompt = f"PYETJA: {query}\n\n[LIGJI]:\n{clean_global}\n\n[FAKTET]:\n{clean_case}"
    content = _call_deepseek(system_prompt, user_prompt, json_mode=True)
    if not content: content = _call_local_llm(f"{system_prompt}\n\n{user_prompt}", json_mode=True)
    return _parse_json_safely(content) if content else {}

# --- NEW: SPREADSHEET ANALYST ---
def analyze_financial_summary(data_context: str) -> str:
    """
    Generates a narrative report based on statistical data from a spreadsheet.
    """
    system_prompt = """
    Ti je "Phoenix Financial Forensic Analyst".
    
    DETYRA:
    Analizo përmbledhjen statistikore të të dhënave financiare/tabelare.
    Identifiko modele të dyshimta, anomali (vlerat ekstreme), ose trende që duhen hetuar.
    
    FORMATI I PËRGJIGJES (Narrative):
    Shkruaj një raport profesional hetimor (3-4 paragrafë në Gjuhen Shqipe).
    - Fillo me një përmbledhje të strukturës së të dhënave (çfarë përfaqësojnë).
    - Evidencon vlerat e dyshimta (anomalitë) nëse ka.
    - Shpjego shpërndarjen e të dhënave (nëse ka përqendrime te caktuara).
    - Përfundo me një rekomandim për auditim të mëtejshëm.
    """
    
    user_prompt = f"TË DHËNAT STATISTIKORE:\n{data_context}"
    
    res = _call_deepseek(system_prompt, user_prompt)
    if not res:
        res = _call_local_llm(f"{system_prompt}\n\n{user_prompt}")
        
    return res or "Analiza e detajuar dështoi të gjenerohej, por statistikat bazë janë të sakta."

# Placeholders
def extract_graph_data(text: str) -> Dict[str, List[Dict]]: return {"entities": [], "relations": []}
def generate_socratic_response(socratic_context: List[Dict], question: str) -> Dict: return {}
def extract_deadlines_from_text(text: str) -> List[Dict[str, Any]]: return []