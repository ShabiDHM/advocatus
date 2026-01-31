# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - CORE INTELLIGENCE V53.0 (LEX SPECIALIS GUARDRAIL)
# 1. FIX: Hard-coded Branch-to-Statute mapping (Family -> LFK, Labor -> LP, etc).
# 2. FIX: Mandated terminology (Kontributi për mbajtje).
# 3. FIX: Contextual Gap Analysis (Forced checking for QPS reports in Family cases).
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

# --- EXPORT LIST ---
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

# --- KOSOVO JURISDICTION PERSONA ---
KOSOVO_LEGAL_PERSONA = """
ROLI: Ti je Avokat i Lartë (Senior Partner) në Prishtinë. 
METODOLOGJIA: Ndiq parimin "Lex Specialis derogat legi generali".

KODI I TERMINOLOGJISË:
- MOS përdor "Alimentacion", PËRDOR "Kontributi për mbajtje".
- MOS përdor "Avokata", PËRDOR "Avokati/ja".

HARTA E LIGJEVE (MANDATORE):
1. FAMILJA (Fëmijët/Divorci): Ligji Nr. 2004/32 për Familjen (LFK). Për ndryshimin e alimentacionit cito Nenet 170-171.
2. PUNA: Ligji Nr. 03/L-212 i Punës.
3. PRONA: Ligji Nr. 03/L-154 për Pronësinë dhe të Drejtat e Tjera Sendore.
4. PROCEDURA: Ligji Nr. 03/L-006 për Procedurën Kontestimore (LPK). Barra e provës bazohet në Nenet 7 dhe 319.
"""

def analyze_case_integrity(context: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_PERSONA}
    OBJEKTIVI: Auditimi Juridik i rastit.
    
    UDHËZIME PËR GAP-ANALIZËN:
    - Për raste familjare: Kontrollo nëse ka Raport nga Qendra për Punë Sociale (QPS) dhe dëshmi të të hyrave (ATK). 
    - MOS sugjero dokumente gjenerike si "Certifikata e martesës" nëse lënda është ndryshim i aktgjykimit.
    
    JSON STRUCTURE:
    {{
        "summary": "Përmbledhje faktike në gjuhë të thjeshtë popullore (max 100 fjalë).",
        "key_issues": ["Issue 1: Faktik", "Issue 2: Procedural"],
        "burden_of_proof": "Auditimi i Barrës së Provës: Referenca strikte në Nenin 319 të LPK-së.",
        "legal_basis": [{{ "law": "Emri i saktë i Ligjit (Nr. X/L-Y)", "article": "Neni X", "relevance": "Shpjegim juridik" }}],
        "strategic_analysis": "Analizë e rreziqeve bazuar në 'Lex Specialis'.",
        "missing_evidence": ["Dëshmitë specifike që mungojnë vërtet (psh. Raporti i QPS, Vërtetimi i ATK)"],
        "action_plan": ["..."],
        "success_probability": "XX%",
        "risk_level": "LOW|MEDIUM|HIGH"
    }}"""
    return _parse_json_safely(_call_llm(system_prompt, context[:50000], True, temp=0.2))

# --- WAR ROOM FUNCTIONS ---

def generate_adversarial_simulation(context: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_PERSONA}
    ROLI: Avokati Kundërshtar. Gjej dobësitë tona (psh. Parashkrimi, Mungesa e legjitimitetit).
    JSON: {{ 'opponent_strategy': '...', 'weakness_attacks': [], 'counter_claims': [] }}"""
    return _parse_json_safely(_call_llm(system_prompt, context[:30000], True, temp=0.4))

def build_case_chronology(text: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_PERSONA}
    DETYRA: Kronologji e fakteve juridike. JSON: {{'timeline': [{{'date': '...', 'event': '...', 'source': '...'}}]}}"""
    return _parse_json_safely(_call_llm(system_prompt, text[:40000], True))

def detect_contradictions(text: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_PERSONA}
    DETYRA: Identifiko mospërputhjet. Dokumentet publike kanë përparësi.
    JSON: {{'contradictions': [{{'claim': '...', 'evidence': '...', 'severity': 'HIGH|LOW', 'impact': '...'}}]}}"""
    return _parse_json_safely(_call_llm(system_prompt, text[:30000], True))

# --- UTILITIES & REST OF 18 FUNCTIONS ---
def extract_graph_data(t: str): return _parse_json_safely(_call_llm(f"{KOSOVO_LEGAL_PERSONA} Graph JSON.", t[:30000], True))
def analyze_financial_portfolio(d: str): return _parse_json_safely(_call_llm(f"{KOSOVO_LEGAL_PERSONA} Financa JSON.", d, True))
def translate_for_client(t: str): return _call_llm(f"{KOSOVO_LEGAL_PERSONA} Thjeshto për klientin.", t)
def extract_deadlines(t: str): return _parse_json_safely(_call_llm(f"{KOSOVO_LEGAL_PERSONA} Afatet JSON.", t[:15000], True))
def perform_litigation_cross_examination(tt: str, cs: List[str]): return _parse_json_safely(_call_llm(f"{KOSOVO_LEGAL_PERSONA} Cross-check.", f"{tt} {cs}", True))
def generate_summary(t: str): return _call_llm(f"{KOSOVO_LEGAL_PERSONA} Përmblidh.", t[:20000])
def get_embedding(t: str): 
    c = get_openai_client()
    return c.embeddings.create(input=[t.replace("\n"," ")], model=EMBEDDING_MODEL).data[0].embedding if c else [0.0]*1536
def forensic_interrogation(q: str, cr: List[str]): return _call_llm(f"Bazo pyetjen në: {cr}", q)
def categorize_document_text(t: str): return _parse_json_safely(_call_llm("Kategorizo.", t[:5000], True)).get("category", "Të tjera")
def sterilize_legal_text(t: str): return sterilize_text_for_llm(t)
def extract_expense_details_from_text(rt: str):
    res = _parse_json_safely(_call_llm("OCR Faturë JSON.", rt[:3000], True))
    return {"category": res.get("category", "Të tjera"), "amount": float(res.get("amount", 0.0)), "date": res.get("date", datetime.now().strftime("%Y-%m-%d")), "description": res.get("merchant", "")}
def query_global_rag_for_claims(rr: str, uq: str): return _parse_json_safely(_call_llm(f"{KOSOVO_LEGAL_PERSONA} Sugjerime JSON.", f"{rr} {uq}", True))
async def process_large_document_async(t: str, tt: str = "SUMMARY"): return generate_summary(t)
async def stream_text_async(sp: str, up: str, temp: float = 0.2) -> AsyncGenerator[str, None]:
    c = get_async_deepseek_client()
    if not c: yield "[Offline]"; return
    s = await c.chat.completions.create(model=OPENROUTER_MODEL, messages=[{"role": "system", "content": f"{KOSOVO_LEGAL_PERSONA}\n{sp}"}, {"role": "user", "content": up}], temperature=temp, stream=True)
    async for ch in s:
        if ch.choices[0].delta.content: yield ch.choices[0].delta.content