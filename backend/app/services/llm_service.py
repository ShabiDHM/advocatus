# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - CORE INTELLIGENCE V58.0 (BRUTE FORCE CONSTRAINTS)
# 1. FIX: Embedded Legal Reference Table to stop article hallucination.
# 2. FIX: Strict Terminology Blacklist (Alimentacion, Issue, Gap, Summary).
# 3. FIX: Forced quoting of "Substanca e Nenit" for professional authority.
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

# --- EXPORT LIST (18 FUNCTIONS VERIFIED) ---
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

def get_deepseek_client(): return OpenAI(api_key=DEEPSEEK_API_KEY, base_url=OPENROUTER_BASE_URL) if DEEPSEEK_API_KEY else None
def get_openai_client(): return OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
def get_async_deepseek_client(): return AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url=OPENROUTER_BASE_URL) if DEEPSEEK_API_KEY else None

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

# --- KOSOVO LEGAL MASTER RULEBOOK (CONSTRAINTS) ---
KOSOVO_LEGAL_PERSONA = """
ROLI: Ti je Avokat i Lartë (Senior Partner) në Prishtinë. 
DETYRA: Analizë juridike strikte, pa emocione, e bazuar në ligjet e RKS.

TABELA E REFERENCAVE (MANDATORE - MOS GUXO TË PËRDORËSH TË TJERA):
1. FAMILJA (Fëmijët/Mbajtja): Ligji Nr. 2004/32 për Familjen i Kosovës. 
   - Neni 170: Obligimi i prindërve për mbajtjen e fëmijës.
   - Neni 171: Ndryshimi i shumës së kontributit nëse ndryshojnë rrethanat.
2. PROCEDURA CIVILE: Ligji Nr. 03/L-006 për Procedurën Kontestimore (LPK).
   - Neni 7: Barra e palëve për të paraqitur faktet.
   - Neni 319: Barra e provës (Kush e thotë një fakt, duhet ta provojë).
3. PUNA: Ligji Nr. 03/L-212 i Punës.
4. DETYRIMET: Ligji Nr. 04/L-077 për Marrëdhëniet e Detyrimeve.

BLACKLISTA E FJALËVE (NDALOHET RREPTËSISHT):
- MOS PËRDOR: "Alimentacion", "Issue", "Gap", "Summary", "Plan", "Alimentacioni".
- PËRDOR VETËM: "Kontributi për mbajtje", "Çështja", "Mangësia", "Përmbledhja", "Plani i Veprimit".

RREGULLI I RELEVANCËS:
Te fusha 'relevance', DUHET të citosh tekstualisht substancën: "Sipas Nenit [X], [Shkruaj rregullin e plotë ligjor]. Në rastin e klientit tonë, kjo do të thotë se...".
"""

def analyze_case_integrity(context: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_PERSONA}
    OBJEKTIVI: Auditimi Juridik i Integritetit të Lëndës.
    
    UDHËZIME PËR JSON:
    - Çelësi 'summary' duhet të jetë: "Përmbledhja Ekzekutive".
    - Çelësi 'missing_evidence' duhet të identifikohet si: "Mangësia [X] (Dokumenti)".
    - Çelësi 'legal_basis' duhet të jetë citim shterues.
    
    JSON STRUCTURE:
    {{
        "summary": "Përmbledhja formale juridike (Letrare)...",
        "key_issues": ["Çështja 1 (Juridike): [Teksti]", "Çështja 2 (Procedurale): [Teksti]"],
        "burden_of_proof": "Auditimi i detajuar i Barrës së Provës sipas Nenit 319 të LPK-së...",
        "legal_basis": [{{ 
            "law": "Ligji Nr. [Numri] për [Emri i Plotë] i Kosovës", 
            "article": "Neni [X]", 
            "relevance": "SUBSTANCA E LIGJIT: [Citim i saktë i substancës]. LIDHJA ME RASTIN: [Analiza]." 
        }}],
        "strategic_analysis": "Strategjia e mbrojtjes bazuar në Lex Specialis...",
        "missing_evidence": ["Mangësia 1 (Dokumenti): [Përshkrimi]", "Mangësia 2 (Prova): [Përshkrimi]"],
        "action_plan": ["Hapi 1: [Veprimi]", "Hapi 2: [Veprimi]"],
        "success_probability": "XX%",
        "risk_level": "I ULËT|I MESËM|I LARTË"
    }}"""
    return _parse_json_safely(_call_llm(system_prompt, context[:50000], True, temp=0.1))

# --- WAR ROOM FUNCTIONS ---

def generate_adversarial_simulation(context: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_PERSONA}
    ROLI: Avokati Kundërshtar. Gjej dobësitë tona (Parashkrimi, Kompetenca, Legjitimiteti).
    JSON: {{ 'opponent_strategy': 'Strategjia e kundërshtarit...', 'weakness_attacks': ['Pika 1', 'Pika 2'], 'counter_claims': ['...'] }}"""
    return _parse_json_safely(_call_llm(system_prompt, context[:30000], True, temp=0.3))

def build_case_chronology(text: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_PERSONA}
    DETYRA: Kronologjia e fakteve juridike (Jo biseda, vetëm veprime ligjore).
    JSON: {{'timeline': [{{'date': 'YYYY-MM-DD', 'event': 'Ngjarja', 'source': '...'}}]}}"""
    return _parse_json_safely(_call_llm(system_prompt, text[:40000], True))

def detect_contradictions(text: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_PERSONA}
    DETYRA: Gjej mospërputhjet në dëshmi dhe dokumente. JSON: {{'contradictions': [{{'claim': '...', 'evidence': '...', 'severity': 'HIGH|LOW', 'impact': '...'}}]}}"""
    return _parse_json_safely(_call_llm(system_prompt, text[:30000], True))

# --- SYSTEM UTILITIES ---

def extract_graph_data(text: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_PERSONA} Shndërro në Nodes/Edges JSON."""
    return _parse_json_safely(_call_llm(system_prompt, text[:30000], True))

def analyze_financial_portfolio(data: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_PERSONA} Analist Financiar JSON."""
    return _parse_json_safely(_call_llm(system_prompt, data, True))

def translate_for_client(legal_text: str) -> str:
    return _call_llm(f"{KOSOVO_LEGAL_PERSONA} Shpjego thjeshtë.", legal_text) or "Gabim."

def extract_deadlines(text: str) -> Dict[str, Any]:
    return _parse_json_safely(_call_llm(f"{KOSOVO_LEGAL_PERSONA} Gjej afatet JSON.", text[:15000], True))

def perform_litigation_cross_examination(target: str, context: List[str]) -> Dict[str, Any]:
    return _parse_json_safely(_call_llm(f"{KOSOVO_LEGAL_PERSONA} Cross-check.", f"{target} {context}", True))

def generate_summary(text: str) -> str:
    return _call_llm(f"{KOSOVO_LEGAL_PERSONA} Përmblidh në 3 pika juridike.", text[:20000]) or ""

def get_embedding(text: str) -> List[float]:
    client = get_openai_client()
    if not client: return [0.0] * 1536
    try:
        res = client.embeddings.create(input=[text.replace("\n", " ")], model=EMBEDDING_MODEL)
        return res.data[0].embedding
    except: return [0.0] * 1536

def forensic_interrogation(question: str, context_rows: List[str]) -> str:
    prompt = f"{KOSOVO_LEGAL_PERSONA} Përgjigju nga provat: {' '.join(context_rows)}"
    return _call_llm(prompt, question) or "Nuk ka informacion."

def categorize_document_text(text: str) -> str:
    res = _call_llm("Kategorizo: Padi, Aktgjykim, Kontratë.", text[:5000], True)
    return _parse_json_safely(res).get("category", "Të tjera")

def sterilize_legal_text(text: str) -> str:
    return sterilize_text_for_llm(text)

def extract_expense_details_from_text(raw_text: str) -> Dict[str, Any]:
    res = _parse_json_safely(_call_llm("OCR Shpenzime JSON.", raw_text[:3000], True))
    return {"category": res.get("category", "Të tjera"), "amount": float(res.get("amount", 0.0)), "date": res.get("date", datetime.now().strftime("%Y-%m-%d")), "description": res.get("merchant", "")}

def query_global_rag_for_claims(rag_results: str, user_query: str) -> Dict[str, Any]:
    return _parse_json_safely(_call_llm(f"{KOSOVO_LEGAL_PERSONA} Sugjero pretendime JSON.", f"{rag_results} {user_query}", True))

async def process_large_document_async(text: str, task_type: str = "SUMMARY") -> str:
    return generate_summary(text)

async def stream_text_async(system_prompt: str, user_prompt: str, temp: float = 0.2) -> AsyncGenerator[str, None]:
    client = get_async_deepseek_client()
    if not client: yield "[Offline]"; return
    full_system = system_prompt if "Avokat" in system_prompt else f"{KOSOVO_LEGAL_PERSONA}\n{system_prompt}"
    try:
        stream = await client.chat.completions.create(model=OPENROUTER_MODEL, messages=[{"role": "system", "content": full_system}, {"role": "user", "content": user_prompt}], temperature=temp, stream=True)
        async for chunk in stream:
            if chunk.choices[0].delta.content: yield chunk.choices[0].delta.content
    except Exception as e: yield f"[Gabim: {str(e)}]"

# --- END OF FILE ---