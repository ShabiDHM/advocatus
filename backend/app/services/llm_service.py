# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - CORE INTELLIGENCE V54.0 (TOTAL FORMALISM)
# 1. FIX: Total purge of English labels (Issue, Gap, etc.).
# 2. FIX: Mandated formal citation strings for Kosovo Judiciary.
# 3. FIX: Integrated Legal Methodology (IRAC) for all output fields.
# 4. STATUS: Unabridged replacement.

import os
import json
import logging
import httpx
import re
import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime, timezone
from openai import OpenAI, AsyncOpenAI

from .text_sterilization_service import sterilize_text_for_llm

logger = logging.getLogger(__name__)

# --- EXPORT LIST (VERIFIED: 18 FUNCTIONS) ---
__all__ = [
    "analyze_financial_portfolio", "analyze_case_integrity", "generate_adversarial_simulation",
    "build_case_chronology", "translate_for_client", "detect_contradictions",
    "extract_deadlines", "perform_litigation_cross_examination", "generate_summary",
    "extract_graph_data", "get_embedding", "forensic_interrogation",
    "categorize_document_text", "sterilize_legal_text", "extract_expense_details_from_text",
    "query_global_rag_for_claims", "process_large_document_async", "stream_text_async"
]

# --- CONFIGURATION ---
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") 
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat" 
EMBEDDING_MODEL = "text-embedding-3-small" 

def get_async_deepseek_client(): return AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url=OPENROUTER_BASE_URL) if DEEPSEEK_API_KEY else None
def get_deepseek_client(): return OpenAI(api_key=DEEPSEEK_API_KEY, base_url=OPENROUTER_BASE_URL) if DEEPSEEK_API_KEY else None
def get_openai_client(): return OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

def _parse_json_safely(content: Optional[str]) -> Dict[str, Any]:
    if not content: return {}
    try: return json.loads(content)
    except:
        match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
        if match:
            try: return json.loads(match.group(1))
            except: pass
        return {"raw_response": content, "error": "JSON_PARSE_FAILED"}

def _call_llm(system_prompt: str, user_prompt: str, json_mode: bool = False, temp: float = 0.1) -> Optional[str]:
    client = get_deepseek_client()
    if not client: return None
    try:
        kwargs = {"model": OPENROUTER_MODEL, "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}], "temperature": temp}
        if json_mode: kwargs["response_format"] = {"type": "json_object"}
        res = client.chat.completions.create(**kwargs)
        return res.choices[0].message.content
    except Exception as e:
        logger.error(f"LLM Call Failed: {e}")
        return None

# --- KOSOVO JURISDICTION PERSONA: SENIOR PARTNER PRISHTINA ---
KOSOVO_LEGAL_PERSONA = """
ROLI: Ti je Avokat i Lartë (Senior Partner) në Prishtinë, Kosovë.
MISIONI: Ofro analizë juridike të nivelit akademik dhe gjyqësor. 

RREGULLAT E GJUHËS (STRIKTE):
1. NDALOHET përdorimi i fjalëve angleze (psh. MOS përdor "Issue", "Gap", "Summary", "Plan").
2. PËRDOR vetëm: "Çështja", "Mangësia", "Përmbledhja", "Plani i Veprimit".
3. GJUHA: Shqipe Standarde Juridike. Termat: "Kontributi për mbajtje" (Jo alimentacion).

RREGULLAT E CITIMIT:
- "Neni [X] i Ligjit Nr. [Y] për [Emri i Plotë] i Republikës së Kosovës".
- Shembull: "Neni 170 i Ligjit Nr. 2004/32 për Familjen i Kosovës".
"""

def analyze_case_integrity(context: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_PERSONA}
    OBJEKTIVI: Auditimi Juridik i Integritetit të Lëndës.
    
    METODOLOGJIA E ANALIZËS:
    - PËRMBLEDHJA: Shpjego rrjedhën e lëndës pa terma teknikë për klientin.
    - BARRA E PROVËS: Shpjego detyrimin e palëve bazuar në Nenin 7 dhe 319 të Ligjit për Procedurën Kontestimore.
    - MANGËSITË: Identifiko dokumentet specifike që mungojnë (psh. Raporti i QPS, Vërtetimi i ATK, Fleta Poseduese).
    
    STRUKTURA E JSON (MOS NDRYSHO ÇELËSAT):
    {{
        "summary": "Përmbledhja ekzekutive faktike...",
        "key_issues": ["Çështja 1: [Përshkrimi Shqip]", "Çështja 2: [Përshkrimi Shqip]"],
        "burden_of_proof": "Auditimi i detajuar i barrës së provës sipas LPK-së...",
        "legal_basis": [{{ "law": "Ligji Nr. X për Y i Kosovës", "article": "Neni X", "relevance": "Arsyetimi juridik..." }}],
        "strategic_analysis": "Analiza strategjike procedurale dhe materiale...",
        "missing_evidence": ["Mangësia 1: [Dokumenti]", "Mangësia 2: [Dokumenti]"],
        "action_plan": ["Hapi 1: [Veprimi]", "Hapi 2: [Veprimi]"],
        "success_probability": "XX%",
        "risk_level": "I ULËT|I MESËM|I LARTË"
    }}"""
    return _parse_json_safely(_call_llm(system_prompt, context[:50000], True, temp=0.2))

# --- WAR ROOM FUNCTIONS ---

def generate_adversarial_simulation(context: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_PERSONA}
    ROLI: Avokati Kundërshtar. Gjej dobësitë tona (psh. Parashkrimi, Kompetenca, Mungesa e legjitimitetit).
    JSON: {{ 'opponent_strategy': 'Strategjia e palës tjetër...', 'weakness_attacks': ['Pika e sulmit 1', 'Pika e sulmit 2'], 'counter_claims': ['Pretendimet kundërshtuese'] }}"""
    return _parse_json_safely(_call_llm(system_prompt, context[:30000], True, temp=0.4))

def build_case_chronology(text: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_PERSONA}
    DETYRA: Kronologjia e veprimeve me rëndësi juridike. JSON: {{'timeline': [{{'date': 'YYYY-MM-DD', 'event': 'Ngjarja', 'source': 'Dokumenti'}}]}}"""
    return _parse_json_safely(_call_llm(system_prompt, text[:40000], True))

def detect_contradictions(text: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_PERSONA}
    DETYRA: Gjej mospërputhjet në dëshmi. JSON: {{'contradictions': [{{'claim': 'Deklarata', 'evidence': 'Prova', 'severity': 'E LARTË|E MESME|E ULËT', 'impact': 'Efekti Juridik'}}]}}"""
    return _parse_json_safely(_call_llm(system_prompt, text[:30000], True))

# --- UTILITIES & SYSTEM FUNCTIONS ---
def extract_graph_data(t: str): return _parse_json_safely(_call_llm(f"{KOSOVO_LEGAL_PERSONA} Harta Logjike JSON.", t[:30000], True))
def analyze_financial_portfolio(d: str): return _parse_json_safely(_call_llm(f"{KOSOVO_LEGAL_PERSONA} Analiza Financiare JSON.", d, True))
def translate_for_client(t: str): return _call_llm(f"{KOSOVO_LEGAL_PERSONA} Thjeshto për klientin.", t)
def extract_deadlines(t: str): return _parse_json_safely(_call_llm(f"{KOSOVO_LEGAL_PERSONA} Afatet Ligjore JSON.", t[:15000], True))
def perform_litigation_cross_examination(tt: str, cs: List[str]): return _parse_json_safely(_call_llm(f"{KOSOVO_LEGAL_PERSONA} Kryqëzimi i provave.", f"{tt} {cs}", True))
def generate_summary(t: str): return _call_llm(f"{KOSOVO_LEGAL_PERSONA} Përmbledhja e dokumentit.", t[:20000])
def get_embedding(t: str): 
    c = get_openai_client()
    return c.embeddings.create(input=[t.replace("\n"," ")], model=EMBEDDING_MODEL).data[0].embedding if c else [0.0]*1536
def forensic_interrogation(q: str, cr: List[str]): return _call_llm(f"Përgjigju nga konteksti: {cr}", q)
def categorize_document_text(t: str): return _parse_json_safely(_call_llm("Kategorizimi JSON.", t[:5000], True)).get("category", "Të tjera")
def sterilize_legal_text(t: str): return sterilize_text_for_llm(t)
def extract_expense_details_from_text(rt: str):
    res = _parse_json_safely(_call_llm("OCR Shpenzime JSON.", rt[:3000], True))
    return {"category": res.get("category", "Të tjera"), "amount": float(res.get("amount", 0.0)), "date": res.get("date", datetime.now().strftime("%Y-%m-%d")), "description": res.get("merchant", "")}
def query_global_rag_for_claims(rr: str, uq: str): return _parse_json_safely(_call_llm(f"{KOSOVO_LEGAL_PERSONA} Sugjerime Ligjore JSON.", f"{rr} {uq}", True))
async def process_large_document_async(t: str, tt: str = "SUMMARY"): return generate_summary(t)
async def stream_text_async(sp: str, up: str, temp: float = 0.2) -> AsyncGenerator[str, None]:
    c = get_async_deepseek_client()
    if not c: yield "[Gabim: API nuk u gjet]"; return
    s = await c.chat.completions.create(model=OPENROUTER_MODEL, messages=[{"role": "system", "content": f"{KOSOVO_LEGAL_PERSONA}\n{sp}"}, {"role": "user", "content": up}], temperature=temp, stream=True)
    async for ch in s:
        if ch.choices[0].delta.content: yield ch.choices[0].delta.content