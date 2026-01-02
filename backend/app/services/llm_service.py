# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - CORE INTELLIGENCE V23.1 (DUAL KNOWLEDGE SEPARATION)
# 1. ARCHITECTURE: Explicit separation of 'Global Knowledge' (Law) vs 'Case Knowledge' (Facts).
# 2. LOGIC: New 'perform_dual_source_analysis' function for RAG workflows.
# 3. SAFETY: Strict hierarchy enforced in the Constitution.

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
# This must match the rules in albanian_rag_service.py exactly.
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
    """
    Cleans text but PRESERVES Pagination markers for citations.
    """
    if not text: return ""
    
    # Basic sterilization (PII redaction logic)
    text = sterilize_text_for_llm(text, redact_names=False)

    # Standardize Pagination Markers
    text = re.sub(r'--- \[Page (\d+)\] ---', r'--- [FAQJA \1] ---', text)

    replacements = {
        "Paditésja": "Paditësja", "paditésja": "paditësja",
        "Paditési": "Paditësi", "paditési": "paditësi",
        "Gjykatés": "Gjykatës", "gjykatés": "gjykatës"
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)

    # Context Awareness: Flag Drafts
    clean_text = text
    pattern = r"(?i)(propozoj|propozim)([\s\S]{0,1500}?)(aktgjykim)" 
    def replacer(match): return f"{match.group(1)}{match.group(2)}DRAFT-PROPOZIM (KËRKESË E PALËS - JO VENDIM)"
    clean_text = re.sub(pattern, replacer, clean_text)
    
    return clean_text

def _parse_json_safely(content: str) -> Dict[str, Any]:
    try: return json.loads(content)
    except json.JSONDecodeError:
        # Fallback: Extract JSON block from Markdown ```json ... ```
        match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
        if match:
            try: return json.loads(match.group(1))
            except: pass
        # Fallback: Find outer braces
        start, end = content.find('{'), content.rfind('}')
        if start != -1 and end != -1:
            try: return json.loads(content[start:end+1])
            except: pass
        return {}

def _call_deepseek(system_prompt: str, user_prompt: str, json_mode: bool = False) -> Optional[str]:
    client = get_deepseek_client()
    if not client: return None
    try:
        # Inject the Constitution into the System Prompt
        full_system_prompt = f"{system_prompt}\n\n{STRICT_FORENSIC_RULES}"
        
        kwargs = {
            "model": OPENROUTER_MODEL,
            "messages": [{"role": "system", "content": full_system_prompt}, {"role": "user", "content": user_prompt}],
            "temperature": 0.0,  # Strict determinism
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
    """
    Performs deep forensic analysis of the document.
    """
    clean_text = sterilize_legal_text(text[:30000]) # Increased context slightly
    
    # PHOENIX UPGRADE: Chain-of-Thought Prompting for JSON
    system_prompt = """
    Ti je "Gjykatës Suprem & Detektiv Hetues".
    
    DETYRA:
    1. Analizo tekstin rresht për rresht (CASE KNOWLEDGE BASE).
    2. Identifiko palët, datat dhe kontradiktat.
    3. Plotëso JSON-in e mëposhtëm me saktësi maksimale.
    
    FORMATI JSON (Strict):
    {
        "document_type": "Përcakto llojin (Padi, Përgjigje në Padi, Aktgjykim, etj)",
        "active_parties": ["Lista e palëve që kanë dorëzuar dokumente"],
        "silent_parties": ["Lista e palëve që NUK kanë dokumente në tekst"],
        "summary_analysis": "Përmbledhje e statusit procedural.",
        
        "judicial_observation": "Opinion gjyqësor neutral. Cila palë ka barrën e provës? A janë provat bindëse?",
        
        "red_flags": [
            "Rreziqe konkrete (psh. 'Tentim për të larguar fëmijën jashtë shtetit').",
            "Mungesa të dyshimta (psh. 'I padituri nuk paraqiti vërtetim papunësie')."
        ],

        "chronology": [{"date": "DD/MM/YYYY", "event": "Ngjarja...", "source_doc": "Fq. X"}],
        "contradictions": ["Mospërputhje faktike midis palëve (nëse ka)."],
        "key_evidence": [],
        "missing_info": ["Cilat dokumente procedurale mungojnë?"]
    }
    """
    user_prompt = f"DOSJA E PLOTË (CASE KNOWLEDGE BASE):\n{clean_text}"
    content = _call_deepseek(system_prompt, user_prompt, json_mode=True)
    if not content: content = _call_local_llm(f"{system_prompt}\n\n{user_prompt}", json_mode=True)
    return _parse_json_safely(content) if content else {}

# --- INTELLIGENCE MODULES ---

def perform_litigation_cross_examination(target_text: str, context_summaries: List[str]) -> Dict[str, Any]:
    clean_target = sterilize_legal_text(target_text[:25000])
    formatted_context = "\n".join([f"- {s}" for s in context_summaries if s])
    
    system_prompt = """
    Ti je "Phoenix Litigation Engine".
    
    DETYRA: Kryqëzo dokumentin e ri [TARGET] me historikun e dosjes [CASE KNOWLEDGE BASE].
    Gjej çdo mospërputhje sado të vogël.
    
    FORMATI JSON (Strict):
    {
        "summary_analysis": "Analizë koherencës.",
        "judicial_observation": "Vlerësim mbi besueshmërinë.",
        "red_flags": ["Rreziqe të reja."],
        "chronology": [{"date": "...", "event": "..."}],
        "conflicting_parties": [{"party_name": "...", "core_claim": "..."}],
        "contradictions": ["Faktet që nuk përputhen."],
        "suggested_questions": ["Pyetje për seancë."],
        "discovery_targets": ["Dokumente shtesë për t'u kërkuar."]
    }
    """
    user_prompt = f"[CASE KNOWLEDGE BASE - DOSJA EKZISTUESE]:\n{formatted_context}\n\n[TARGET - DOKUMENTI I RI]:\n{clean_target}"
    content = _call_deepseek(system_prompt, user_prompt, json_mode=True)
    if not content: content = _call_local_llm(f"{system_prompt}\n\n{user_prompt}", json_mode=True)
    return _parse_json_safely(content) if content else {}

# --- NEW: DUAL SOURCE RAG ANALYSIS ---

def perform_dual_source_analysis(query: str, case_context: str, global_context: str) -> Dict[str, Any]:
    """
    Uses BOTH knowledge bases to answer a complex query.
    1. Case Knowledge Base: The specific facts.
    2. Global Knowledge Base: The laws and precedents.
    """
    clean_case = sterilize_legal_text(case_context[:20000])
    clean_global = sterilize_legal_text(global_context[:10000])
    
    system_prompt = """
    Ti je "Phoenix Legal Architect".
    
    BURIMET E TUA:
    1. GLOBAL KNOWLEDGE BASE = LIGJI (Nenet, Jurisprudenca).
    2. CASE KNOWLEDGE BASE = FAKTET (Dokumentet e dosjes).
    
    DETYRA:
    Përgjigju pyetjes duke aplikuar LIGJIN (Global) mbi FAKTET (Case).
    
    FORMATI JSON (Strict):
    {
        "direct_answer": "Përgjigja përfundimtare.",
        "legal_basis": ["Nenet specifike nga Global KB që u aplikuan."],
        "factual_basis": ["Faktet specifike nga Case KB që mbështesin përgjigjen."],
        "missing_facts": ["Çfarë mungon në dosje për të plotësuar kushtin ligjor?"],
        "strategy": "Hapi i rradhës i sugjeruar."
    }
    """
    
    user_prompt = f"""
    PYETJA: {query}
    
    [BURIMI 1: GLOBAL KNOWLEDGE BASE - LIGJI]:
    {clean_global}
    
    [BURIMI 2: CASE KNOWLEDGE BASE - FAKTET]:
    {clean_case}
    """
    
    content = _call_deepseek(system_prompt, user_prompt, json_mode=True)
    if not content: content = _call_local_llm(f"{system_prompt}\n\n{user_prompt}", json_mode=True)
    return _parse_json_safely(content) if content else {}

# Placeholders
def extract_graph_data(text: str) -> Dict[str, List[Dict]]: return {"entities": [], "relations": []}
def generate_socratic_response(socratic_context: List[Dict], question: str) -> Dict: return {}
def extract_deadlines_from_text(text: str) -> List[Dict[str, Any]]: return []