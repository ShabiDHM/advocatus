# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - INTELLIGENCE V12.0 (STRICT EVIDENCE)
# 1. UPGRADE: "Silent Party Protocol" - No documents from Defendant = No Claims.
# 2. UPGRADE: "Pinpoint Citations" - Demands (Dokumenti X, Faqja Y) for every fact.
# 3. SAFETY: Temperature 0.0 (Deterministic).

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
    if not text: return ""
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
    system_prompt = "Ti je Analist Ligjor. Krijo një përmbledhje të shkurtër faktike."
    user_prompt = f"DOKUMENTI:\n{clean_text}"
    res = _call_local_llm(f"{system_prompt}\n\n{user_prompt}")
    if not res or len(res) < 50: res = _call_deepseek(system_prompt, user_prompt)
    return res or "N/A"

def extract_findings_from_text(text: str) -> List[Dict[str, Any]]:
    clean_text = sterilize_legal_text(text[:25000])
    system_prompt = """
    Ti je Motor i Nxjerrjes së Provave.
    DETYRA: Identifiko faktet dhe kërkesat.
    FORMATI JSON: {"findings": [{"finding_text": "...", "source_text": "...", "category": "KËRKESË", "page_number": 1}]}
    """
    user_prompt = f"ANALIZO KËTË DOKUMENT:\n{clean_text}"
    content = _call_deepseek(system_prompt, user_prompt, json_mode=True)
    if not content: content = _call_local_llm(f"{system_prompt}\n\n{user_prompt}", json_mode=True)
    if content:
        data = _parse_json_safely(content)
        return data.get("findings", []) if isinstance(data, dict) else []
    return []

def analyze_case_contradictions(text: str) -> Dict[str, Any]:
    """
    GENERAL CASE ANALYSIS (For the Main Button)
    """
    clean_text = sterilize_legal_text(text[:25000])
    system_prompt = """
    Ti je 'The Auditor' - Gjyqtar Suprem Hetues.
    
    DETYRA: Analizo dosjen dhe ndërto profilin e konfliktit.
    
    RREGULLAT E HEKURTA (ZERO HALUCINACIONE):
    1. **MOS SHPIK MBROJTJE:** Nëse i Padituri nuk ka dorëzuar dokument (Përgjigje në Padi), pozicioni i tij ËSHTË: "Nuk ka deklaruar ende qëndrim zyrtar."
    2. **CITIMI I DETYRUESHËM:** Çdo fakt duhet të ketë: (Burimi: [Emri i Dok]).
    3. **ANALIZA E PROVAVE:** Nëse paditësi thotë "S'ka paguar", por nuk ka prova bankare, shënoje si "Pretendim i paprovuar".
    
    FORMATI JSON:
    {
        "document_type": "Përmbledhje Dosjeje",
        "summary_analysis": "Përshkrim i saktë i statusit të rastit (kush ka folur, kush jo).",
        "conflicting_parties": [
            {"party_name": "Emri (Paditësi)", "core_claim": "Kërkon X (Ref: Padi, fq.1)"},
            {"party_name": "Emri (I Padituri)", "core_claim": "Nuk ka deklaruar ende (Mungon dokumenti mbrojtës)."} 
        ],
        "contradictions": [
            "Paditësi pretendon X në (Padi, fq.2), por mungon prova Y që kërkohet me ligj."
        ],
        "key_evidence": [
            "Fatura X (Data 01.01.2023)."
        ],
        "missing_info": [
            "Mungon Përgjigja në Padi nga i padituri."
        ]
    }
    """
    user_prompt = f"DOSJA:\n{clean_text}"
    content = _call_deepseek(system_prompt, user_prompt, json_mode=True)
    if not content: content = _call_local_llm(f"{system_prompt}\n\n{user_prompt}", json_mode=True)
    return _parse_json_safely(content) if content else {}

def perform_litigation_cross_examination(target_text: str, context_summaries: List[str]) -> Dict[str, Any]:
    """
    DOCUMENT-SPECIFIC ANALYSIS (For the Swords Button / Auto-Pilot)
    """
    clean_target = sterilize_legal_text(target_text[:25000])
    formatted_context = "\n".join([f"- {s}" for s in context_summaries if s])
    
    system_prompt = """
    Ti je "Phoenix" - Avokat Mbrojtës Agresiv.
    
    DETYRA: Sulmo besueshmërinë e këtij dokumenti (Target).
    
    RREGULLAT E SAKTËSISË:
    1. **CITO ÇDO GJË:** "Pretendimi X (Target, rreshti 10) kundërshtohet nga Dokumenti Y (Context)."
    2. **HESHTJA NUK ËSHTË POHIM:** Nëse pala tjetër nuk ka folur, thuaj "Mungon deklarata kundërshtuese".
    3. **SPECIFIKIMI I PROVËS:** Kur thua "Mungojnë prova", thuaj saktësisht CILA provë duhet të ishte aty (psh. Fatura, Raporti Mjekësor).

    FORMATI JSON (Strict):
    {
        "summary_analysis": "Analizë kritike e dokumentit me citime.",
        "contradictions": [
            "Target thotë 'S'ka pagesa' (fq. 2), por Context ka 'Faturë 200€' (Dokumenti: Banka)."
        ],
        "suggested_questions": [
            "Z. Dëshmitar, në faqen 2 pretendoni X. Ku është raporti mjekësor që e vërteton këtë?"
        ],
        "discovery_targets": [
            "Kërkohet: Raporti i Qendrës Sociale për të vërtetuar pretendimin në paragrafin 3."
        ],
        "key_evidence": [],
         "conflicting_parties": []
    }
    """
    
    user_prompt = f"""
    [FAKTET E DOSJES (CONTEXT)]
    {formatted_context}
    
    [DOKUMENTI QË PO SULMOHET (TARGET)]
    {clean_target}
    """

    content = _call_deepseek(system_prompt, user_prompt, json_mode=True)
    if not content: content = _call_local_llm(f"{system_prompt}\n\n{user_prompt}", json_mode=True)
    if content: return _parse_json_safely(content)
    
    return { "summary_analysis": "Analiza dështoi.", "contradictions": [], "suggested_questions": [], "discovery_targets": [] }

def extract_graph_data(text: str) -> Dict[str, List[Dict]]:
    return {"entities": [], "relations": []}
def generate_socratic_response(socratic_context: List[Dict], question: str) -> Dict:
    return {}
def extract_deadlines_from_text(text: str) -> List[Dict[str, Any]]:
    return []