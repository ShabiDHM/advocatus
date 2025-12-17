# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - INTELLIGENCE V14.2 (FORENSIC AUDITOR)
# 1. NEW: Strict "Silent Party" Logic (Anti-Hallucination).
# 2. NEW: Mandatory Citation Protocol ([Burimi: ..., Fq. ...]).
# 3. MOD: "analyze_case_contradictions" upgraded to "analyze_case_integrity".

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

# --- THE FORENSIC CONSTITUTION ---
# This prompt is injected into every major analysis call to prevent hallucinations.
STRICT_FORENSIC_RULES = """
RREGULLAT E AUDITIMIT (STRICT LIABILITY):
1. ZERO HALUCINACIONE: Nëse fakti nuk ekziston në tekst, shkruaj "NUK KA TË DHËNA". Mos hamendëso asgjë.
2. RREGULLI I HESHTJES (THE SILENT PARTY RULE): 
   - Mos krijo "simetri artificiale". 
   - Nëse kemi vetëm Padinë, I Padituri "NUK KA PARAQITUR PËRGJIGJE". Mos shpik mbrojtje për të.
3. CITIM I DETYRUESHËM:
   - Çdo pretendim faktik duhet të ketë referencën: [Fq. X].
   - Përdor shënuesit "--- [FAQJA X] ---" nga teksti për të gjetur numrin.
4. JURIDIKSIONI: Republika e Kosovës.
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
    
    # Basic sterilization (PII redaction logic from service)
    text = sterilize_text_for_llm(text, redact_names=False)

    # Standardize Pagination Markers if they vary
    text = re.sub(r'--- \[Page (\d+)\] ---', r'--- [FAQJA \1] ---', text)

    replacements = {
        "Paditésja": "Paditësja", "paditésja": "paditësja",
        "Paditési": "Paditësi", "paditési": "paditësi",
        "Gjykatés": "Gjykatës", "gjykatés": "gjykatës"
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)

    # Identify context to prevent misinterpreting a Draft as a Judgement
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
            "temperature": 0.0,  # Zero temperature for maximum determinism
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
        # Inject Constitution for Local LLM too
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

def extract_findings_from_text(text: str) -> List[Dict[str, Any]]:
    clean_text = sterilize_legal_text(text[:25000])
    system_prompt = """
    Ti je "Forensic Document Examiner".
    DETYRA: Skano dokumentin dhe nxirr fakte (Datat, Shumat, Emrat).
    
    RREGULL: Çdo 'finding_text' duhet të përfundojë me [Fq. X] nëse shënuesi ekziston.
    
    FORMATI JSON: 
    {"findings": [{"finding_text": "Më datë 12.01.2023 u nënshkrua kontrata [Fq. 2]", "category": "PROVË", "page_number": 2}]}
    """
    user_prompt = f"DOKUMENTI:\n{clean_text}"
    content = _call_deepseek(system_prompt, user_prompt, json_mode=True)
    if not content: content = _call_local_llm(f"{system_prompt}\n\n{user_prompt}", json_mode=True)
    if content:
        data = _parse_json_safely(content)
        return data.get("findings", []) if isinstance(data, dict) else []
    return []

def analyze_case_integrity(text: str) -> Dict[str, Any]:
    """
    FORMERLY: analyze_case_contradictions
    UPGRADED: Handles 'Silent Party Rule' and enforces strict citation.
    """
    clean_text = sterilize_legal_text(text[:25000])
    system_prompt = """
    Ti je "Auditori Ligjor Suprem".
    
    DETYRA 1: Identifiko cilat palë kanë folur.
    - Nëse kemi vetëm dokumente nga Paditësi -> I Padituri është 'PASIV/HESHTUR'.
    
    DETYRA 2: Krijo Kronologjinë e Verifikuar.
    - Çdo datë duhet të ketë burimin [Fq. X].
    
    FORMATI JSON (Strict):
    {
        "document_type": "Përcakto llojin (Padi, Përgjigje në Padi, Aktgjykim, etj)",
        "active_parties": ["Lista e palëve që kanë dorëzuar dokumente"],
        "silent_parties": ["Lista e palëve që NUK kanë dokumente në tekst"],
        "summary_analysis": "Përmbledhje e statusit procedural.",
        "chronology": [{"date": "DD/MM/YYYY", "event": "Ngjarja...", "source_doc": "Fq. X"}],
        "contradictions": [
            "Vetëm nëse të dy palët kanë deklaruar fakte të kundërta. Nëse një palë hesht, shkruaj: 'Nuk ka kontradikta - Mungon deklarimi i palës së kundërt'."
        ],
        "key_evidence": [],
        "missing_info": ["Cilat dokumente procedurale mungojnë (psh: Përgjigja në Padi)?"]
    }
    """
    user_prompt = f"DOSJA E PLOTË (TEXT):\n{clean_text}"
    content = _call_deepseek(system_prompt, user_prompt, json_mode=True)
    if not content: content = _call_local_llm(f"{system_prompt}\n\n{user_prompt}", json_mode=True)
    return _parse_json_safely(content) if content else {}

# --- INTELLIGENCE MODULES (PHOENIX ENGINE) ---

def perform_litigation_cross_examination(target_text: str, context_summaries: List[str]) -> Dict[str, Any]:
    clean_target = sterilize_legal_text(target_text[:25000])
    formatted_context = "\n".join([f"- {s}" for s in context_summaries if s])
    
    system_prompt = """
    Ti je "Phoenix Litigation Engine" - Sistemi i Auditimit.
    
    DETYRA: Kryqëzo dokumentin e ri [TARGET] me historikun [CONTEXT].
    
    RREGULLI I SIMETRISË:
    - Verifiko nëse ky dokument është Përgjigje ndaj Padisë.
    - Nëse Target është Padi dhe Context është bosh -> "Fillimi i Çështjes".
    
    FORMATI JSON (Strict):
    {
        "summary_analysis": "Analizë koherencës. A përputhet ky dokument me provat e mëparshme?",
        "chronology": [
            {"date": "DD/MM/YYYY", "event": "Ngjarja brenda dokumentit", "source_doc": "Target Doc [Fq. X]"}
        ],
        "conflicting_parties": [
            {"party_name": "Emri", "core_claim": "Çfarë pretendon specifikisht në këtë dokument?"}
        ],
        "contradictions": [
            "Identifiko mospërputhje faktuale strikte (psh: Data ndryshe, Shuma ndryshe)."
        ],
        "suggested_questions": [
            "Pyetje për të qartësuar paqartësitë ose mungesat në këtë dokument."
        ],
        "discovery_targets": ["Çfarë dokumenti tjetër duhet kërkuar bazuar në këtë tekst?"],
        "key_evidence": []
    }
    """
    user_prompt = f"[CONTEXT - DOSJA EKZISTUESE]:\n{formatted_context}\n\n[TARGET - DOKUMENTI I RI]:\n{clean_target}"
    content = _call_deepseek(system_prompt, user_prompt, json_mode=True)
    if not content: content = _call_local_llm(f"{system_prompt}\n\n{user_prompt}", json_mode=True)
    return _parse_json_safely(content) if content else {}

def synthesize_and_deduplicate_findings(raw_findings: List[str]) -> List[Dict[str, Any]]:
    joined_findings = "\n".join(raw_findings[:100]) 
    system_prompt = """
    Ti je "Arkivi Qendror". 
    DETYRA: Grupo dhe shkri faktet e ngjashme.
    RREGULL: Ruaj referencat [Fq. X]. Nëse ka shumë referenca për një fakt, bashkoj ato (psh: [Fq. 2, Fq. 5]).
    FORMATI JSON: {"synthesized_findings": [{"finding_text": "...", "source_documents": ["..."], "category": "..."}]}
    """
    user_prompt = f"FAKTET BRUTO:\n{joined_findings}"
    content = _call_deepseek(system_prompt, user_prompt, json_mode=True)
    if not content: content = _call_local_llm(f"{system_prompt}\n\n{user_prompt}", json_mode=True)
    if content:
        data = _parse_json_safely(content)
        return data.get("synthesized_findings", [])
    return []

# Placeholder stubs for interface compatibility
def extract_graph_data(text: str) -> Dict[str, List[Dict]]: return {"entities": [], "relations": []}
def generate_socratic_response(socratic_context: List[Dict], question: str) -> Dict: return {}
def extract_deadlines_from_text(text: str) -> List[Dict[str, Any]]: return []