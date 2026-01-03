# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - CORE INTELLIGENCE V25.0 (STRICT RAG & HALLUCINATION FIX)
# 1. FIX: Strengthened 'STRICT_FORENSIC_RULES' to prevent Civil/Criminal mix-ups.
# 2. ADDED: 'get_rag_chat_response' method for general chat (likely used by chat_service).
# 3. LOGIC: Enforces strict separation of Global (Law) vs Case (Fact) knowledge.

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

# --- THE FORENSIC CONSTITUTION (UPDATED & HARDENED) ---
STRICT_FORENSIC_RULES = """
RREGULLAT E AUDITIMIT DHE LIGJIT (STRICT LIABILITY):

1. HIERARKIA E BURIMEVE:
   - GLOBAL KNOWLEDGE BASE = LIGJI. (Kjo përfshin Ligjin për Procedurën Kontestimore, Kodin Penal, etj).
   - CASE KNOWLEDGE BASE = FAKTET. (Vetëm çfarë është në dokumentet e ngarkuara).
   
2. NDALIM ABSOLUT I HALUCINACIONEVE:
   - MOS shpik ligje.
   - MOS ngatërro Procedurën Civile (Padi, Aktgjykim) me Procedurën Penale (Aktakuzë, Mbrojtje e Ligjshmërisë).
   - Nëse pyetja është për "Padi", përgjigju VETËM bazuar në Ligjin për Procedurën Kontestimore (LPK).
   - Nëse nuk e di përgjigjen bazuar në burimet e dhëna, thuaj: "Nuk kam informacion të mjaftueshëm në bazën e njohurive."

3. RREGULLI I HESHTJES: 
   - Nëse një fakt nuk ekziston në dosje, thuaj "NUK KA TË DHËNA". Mos supozo.

4. GJUHA DHE JURIDIKSIONI:
   - Përdor vetëm terminologjinë zyrtare të Republikës së Kosovës.
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
        # Inject the Constitution
        full_system_prompt = f"{STRICT_FORENSIC_RULES}\n\n{system_prompt}"
        
        kwargs = {
            "model": OPENROUTER_MODEL,
            "messages": [{"role": "system", "content": full_system_prompt}, {"role": "user", "content": user_prompt}],
            "temperature": 0.0, # Zero temp for maximum determinism
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

# --- STANDARD CHAT (Restored & Hardened) ---
def get_rag_chat_response(query: str, context: str, history: List[Dict[str, str]]) -> str:
    """
    Standard Chat function used by ChatService.
    Uses RAG context (Local + Global) to answer user questions.
    """
    clean_context = sterilize_legal_text(context[:15000])
    
    # Format history for context (last 3 messages)
    history_str = ""
    for msg in history[-3:]:
        role = "Përdoruesi" if msg['role'] == 'user' else "AI"
        history_str += f"{role}: {msg['content']}\n"

    system_prompt = """
    Ti je "Juristi AI", asistenti ligjor më i saktë në Kosovë.
    
    DETYRA:
    Përgjigju pyetjes së përdoruesit duke përdorur VETËM kontekstin e dhënë më poshtë.
    
    UDHËZIME TË VEÇANTA:
    1. Konteksti përmban "Global Knowledge" (Ligjet) dhe "Case Knowledge" (Dokumentet).
    2. Identifiko qartë nëse pyetja është për Procedurë Civile (Padi) apo Penale. MOS I PËRZI.
    3. Nëse konteksti nuk e përmban përgjigjen, thuaj: "Nuk e gjej këtë informacion në dokumentet ose ligjet e ngarkuara."
    4. Cito burimin (psh: "Sipas Nenit X..." ose "Sipas Padisë...").
    """
    
    user_prompt = f"""
    KONTEKSTI (LIGJI DHE DOSJA):
    {clean_context}
    
    HISTORIKU I BISEDËS:
    {history_str}
    
    PYETJA AKTUALE:
    {query}
    """
    
    res = _call_deepseek(system_prompt, user_prompt)
    if not res:
        res = _call_local_llm(f"{system_prompt}\n\n{user_prompt}")
        
    return res or "Sistemi është duke u përditësuar. Ju lutem provoni përsëri."

# --- FEATURE METHODS ---

def generate_summary(text: str) -> str:
    clean_text = sterilize_legal_text(text[:20000])
    system_prompt = "Ti je Analist Ligjor Forensik. Krijo një përmbledhje të shkurtër, objektive."
    user_prompt = f"DOKUMENTI:\n{clean_text}"
    res = _call_local_llm(f"{system_prompt}\n\n{user_prompt}")
    if not res or len(res) < 50: res = _call_deepseek(system_prompt, user_prompt)
    return res or "Nuk u gjenerua përmbledhje."

def analyze_case_integrity(text: str) -> Dict[str, Any]:
    clean_text = sterilize_legal_text(text[:30000])
    system_prompt = """
    Ti je "Gjykatës Suprem & Detektiv Hetues".
    DETYRA: Analizo tekstin. Identifiko palët, datat dhe kontradiktat.
    FORMATI JSON (Strict): { "document_type": "", "active_parties": [], "silent_parties": [], "summary_analysis": "", "judicial_observation": "", "red_flags": [], "chronology": [], "contradictions": [], "key_evidence": [], "missing_info": [] }
    """
    user_prompt = f"DOSJA:\n{clean_text}"
    content = _call_deepseek(system_prompt, user_prompt, json_mode=True)
    if not content: content = _call_local_llm(f"{system_prompt}\n\n{user_prompt}", json_mode=True)
    return _parse_json_safely(content) if content else {}

def perform_litigation_cross_examination(target_text: str, context_summaries: List[str]) -> Dict[str, Any]:
    clean_target = sterilize_legal_text(target_text[:25000])
    formatted_context = "\n".join([f"- {s}" for s in context_summaries if s])
    system_prompt = """
    Ti je "Phoenix Litigation Engine".
    DETYRA: Kryqëzo dokumentin e ri [TARGET] me historikun e dosjes.
    FORMATI JSON (Strict): { "summary_analysis": "", "judicial_observation": "", "red_flags": [], "chronology": [], "conflicting_parties": [], "contradictions": [], "suggested_questions": [], "discovery_targets": [] }
    """
    user_prompt = f"CONTEXT:\n{formatted_context}\n\nTARGET:\n{clean_target}"
    content = _call_deepseek(system_prompt, user_prompt, json_mode=True)
    if not content: content = _call_local_llm(f"{system_prompt}\n\n{user_prompt}", json_mode=True)
    return _parse_json_safely(content) if content else {}

def perform_dual_source_analysis(query: str, case_context: str, global_context: str) -> Dict[str, Any]:
    """
    This is for specialized RAG queries requiring structured JSON output.
    """
    clean_case = sterilize_legal_text(case_context[:20000])
    clean_global = sterilize_legal_text(global_context[:10000])
    
    system_prompt = """
    Ti je "Phoenix Legal Architect".
    DETYRA: Përgjigju pyetjes duke aplikuar LIGJIN (Global) mbi FAKTET (Case).
    MOS shpik ligje. Nëse është Çështje Civile, referohu vetëm LPK/LMD.
    
    FORMATI JSON (Strict):
    {
        "direct_answer": "Përgjigja.",
        "legal_basis": ["Nenet nga Global KB."],
        "factual_basis": ["Faktet nga Case KB."],
        "missing_facts": ["Çfarë mungon?"],
        "strategy": "Sugjerim."
    }
    """
    user_prompt = f"PYETJA: {query}\n\n[LIGJI - GLOBAL]:\n{clean_global}\n\n[FAKTET - CASE]:\n{clean_case}"
    content = _call_deepseek(system_prompt, user_prompt, json_mode=True)
    if not content: content = _call_local_llm(f"{system_prompt}\n\n{user_prompt}", json_mode=True)
    return _parse_json_safely(content) if content else {}

def analyze_financial_summary(data_context: str) -> str:
    system_prompt = """
    Ti je "Phoenix Financial Forensic Analyst".
    DETYRA: Analizo statistikat financiare. Identifiko anomali.
    FORMATI: Raport narrativ profesional në Shqip.
    """
    user_prompt = f"STATISTIKAT:\n{data_context}"
    res = _call_deepseek(system_prompt, user_prompt)
    if not res: res = _call_local_llm(f"{system_prompt}\n\n{user_prompt}")
    return res or "Analiza dështoi."

def analyze_deposition_transcript(transcript_text: str) -> Dict[str, Any]:
    clean_text = sterilize_legal_text(transcript_text[:30000])
    system_prompt = """
    Ti je "Phoenix Forensic Psychologist".
    DETYRA: Analizo transkriptin për kontradikta dhe gjuhë psikolinguistike.
    FORMATI JSON (Strict): { "witness_name": "", "credibility_score": 0, "summary": "", "inconsistencies": [], "emotional_segments": [], "suggested_questions": [], "processed_at": "" }
    """
    user_prompt = f"TRANSKRIPTI:\n{clean_text}"
    content = _call_deepseek(system_prompt, user_prompt, json_mode=True)
    if not content: content = _call_local_llm(f"{system_prompt}\n\n{user_prompt}", json_mode=True)
    return _parse_json_safely(content) if content else {}

# Placeholders to prevent import errors if used elsewhere
def extract_graph_data(text: str) -> Dict[str, List[Dict]]: return {"entities": [], "relations": []}
def generate_socratic_response(socratic_context: List[Dict], question: str) -> Dict: return {}
def extract_deadlines_from_text(text: str) -> List[Dict[str, Any]]: return []