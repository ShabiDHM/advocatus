# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - CORE INTELLIGENCE V68.7 (STATUTORY PRECISION)
# 1. FIX: Enforced Statutory Precision Protocol (Law Name, Number, Year, Article/Paragraph).
# 2. FIX: Hardened 'build_case_chronology' keys to strictly use "date" and "event".
# 3. FIX: Mandatory [Law/Doc](doc://ligji) formatting inside all JSON arrays.
# 4. STATUS: Senior Partner Logic Active. Zero Degradation.

import os
import json
import logging
import re
import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime
from openai import OpenAI, AsyncOpenAI
from .text_sterilization_service import sterilize_text_for_llm

logger = logging.getLogger(__name__)

__all__ = [
    "analyze_financial_portfolio", "analyze_case_integrity", "generate_adversarial_simulation",
    "build_case_chronology", "translate_for_client", "detect_contradictions",
    "extract_deadlines", "perform_litigation_cross_examination", "generate_summary",
    "extract_graph_data", "get_embedding", "forensic_interrogation",
    "categorize_document_text", "sterilize_legal_text", "extract_expense_details_from_text",
    "query_global_rag_for_claims", "process_large_document_async", "stream_text_async"
]

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat" 
EMBEDDING_MODEL = "text-embedding-3-small"

_async_client, _api_semaphore = None, None

def get_async_deepseek_client():
    global _async_client
    if not _async_client and DEEPSEEK_API_KEY:
        _async_client = AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url=OPENROUTER_BASE_URL)
    return _async_client

def get_semaphore():
    global _api_semaphore
    if _api_semaphore is None: _api_semaphore = asyncio.Semaphore(10)
    return _api_semaphore

def _parse_json_safely(content: Optional[str]) -> Dict[str, Any]:
    if not content: return {}
    try: return json.loads(content)
    except:
        match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
        if match:
            try: return json.loads(match.group(1))
            except: pass
        return {"raw_response": content, "error": "JSON_PARSE_FAILED"}

# --- SENIOR PARTNER PERSONA ---
KOSOVO_LEGAL_BRAIN = """
ROLI: Ti je 'Senior Legal Partner' me 20 vjet përvojë në Kosovë.
PROTOKOLLI I CITIMIT (STRIKT):
1. Çdo referencë ligjore DUHET të përmbajë: [Emri i Plotë i Ligjit, Nr. i Ligjit, Viti, dhe Neni/Paragrafi specifik].
2. Çdo referencë DUHET të jetë e formatuar si badge: [Teksti](doc://ligji).
3. MOS jep opinione pa bazë ligjore materiale.
"""

def _call_llm(sys_p: str, user_p: str, json_mode: bool = False, temp: float = 0.1) -> Optional[str]:
    c = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=OPENROUTER_BASE_URL) if DEEPSEEK_API_KEY else None
    if not c: return None
    try:
        kwargs = {"model": OPENROUTER_MODEL, "messages": [{"role": "system", "content": f"{KOSOVO_LEGAL_BRAIN}\n{sys_p}"}, {"role": "user", "content": user_p}], "temperature": temp}
        if json_mode: kwargs["response_format"] = {"type": "json_object"}
        return c.chat.completions.create(**kwargs).choices[0].message.content
    except Exception as e:
        logger.error(f"LLM Error: {e}")
        return None

async def _call_llm_async(sys_p: str, user_p: str, json_mode: bool = False, temp: float = 0.1) -> Optional[str]:
    client = get_async_deepseek_client()
    if not client: return None
    async with get_semaphore():
        try:
            kwargs = {"model": OPENROUTER_MODEL, "messages": [{"role": "system", "content": f"{KOSOVO_LEGAL_BRAIN}\n{sys_p}"}, {"role": "user", "content": user_p}], "temperature": temp}
            if json_mode: kwargs["response_format"] = {"type": "json_object"}
            res = await client.chat.completions.create(**kwargs)
            return res.choices[0].message.content
        except Exception as e:
            logger.error(f"Async LLM Error: {e}")
            return None

# --- CORE ANALYSIS FUNCTIONS ---

def analyze_case_integrity(context: str, custom_prompt: Optional[str] = None) -> Dict[str, Any]:
    sys = custom_prompt or "Analizo integritetin e rastit. Përdor citime të plota statutore."
    return _parse_json_safely(_call_llm(sys, context[:100000], True, 0.1))

def generate_adversarial_simulation(context: str) -> Dict[str, Any]:
    sys = """
    DETYRA: Gjej dobësitë materiale.
    CITIMI: Përdor formatin statutore: [Ligji Nr. XX, Neni YY](doc://ligji).
    JSON: {'opponent_strategy':'', 'weakness_attacks':[], 'counter_claims':[]}
    """
    return _parse_json_safely(_call_llm(sys, context[:30000], True, 0.4))

def detect_contradictions(text: str) -> Dict[str, Any]:
    sys = """
    DETYRA: Identifiko kontradiktat mes fakteve dhe ligjit.
    FORMATI: Cito me [Ligji Nr. XX/Dokumenti YY](doc://ligji).
    JSON: {'contradictions': [{'severity': 'HIGH', 'claim': '...', 'evidence': '...', 'impact': '...'}]}
    """
    return _parse_json_safely(_call_llm(sys, text[:30000], True))

def build_case_chronology(text: str) -> Dict[str, Any]:
    sys = "Nxirr kronologjinë e fakteve. Përdor VETËM çelësat: 'date' dhe 'event'. JSON: {'timeline': [{'date': '...', 'event': '...'}]}"
    return _parse_json_safely(_call_llm(sys, text[:40000], True))

async def process_large_document_async(text: str, task_type: str = "SUMMARY") -> str:
    if not text: return "Teksti nuk u gjet."
    map_prompt = "Analizo segmentin. Identifiko faktet kyçe me citime."
    reduce_prompt = "Sintezo në një opinion suprem me bazë ligjore të plotë."
    chunks = [text[i:i+5000] for i in range(0, len(text), 5000)]
    tasks = [_call_llm_async(map_prompt, f"SEGMENTI:\n{c}") for c in chunks]
    results = await asyncio.gather(*tasks)
    combined = "\n---\n".join([r for r in results if r])
    return await _call_llm_async(reduce_prompt, f"ANALIZAT:\n{combined}") or "Dështoi."

# --- LEGACY UTILITIES ---

def extract_deadlines(text: str) -> Dict[str, Any]:
    return _parse_json_safely(_call_llm("Gjej afatet. JSON: {'deadlines':[]}", text[:20000], True))

def perform_litigation_cross_examination(target: str, context: List[str]) -> Dict[str, Any]:
    return _parse_json_safely(_call_llm(f"Pyetje për: {target}. JSON.", "\n".join(context)[:40000], True))

def generate_summary(text: str) -> str:
    return _call_llm("Përmbledhje në 3 pika.", text[:20000]) or ""

def extract_graph_data(text: str) -> Dict[str, Any]:
    return _parse_json_safely(_call_llm("Nxjerr nyjet dhe lidhjet. JSON: {'nodes':[], 'edges':[]}", text[:30000], True))

def get_embedding(text: str) -> List[float]:
    from openai import OpenAI as OAI
    c = OAI(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None
    if not c: return [0.0] * 1536
    try: return c.embeddings.create(input=[text.replace("\n", " ")], model=EMBEDDING_MODEL).data[0].embedding
    except: return [0.0] * 1536

async def stream_text_async(sys_p: str, user_p: str, temp: float = 0.2) -> AsyncGenerator[str, None]:
    c = get_async_deepseek_client()
    if not c: yield "[OFFLINE]"; return
    async with get_semaphore():
        try:
            stream = await c.chat.completions.create(model=OPENROUTER_MODEL, messages=[{"role": "system", "content": f"{KOSOVO_LEGAL_BRAIN}\n{sys_p}"}, {"role": "user", "content": user_p}], temperature=temp, stream=True)
            async for chunk in stream:
                if chunk.choices[0].delta.content: yield chunk.choices[0].delta.content
        except Exception as e: yield f"[Gabim: {str(e)}]"

def forensic_interrogation(q: str, rows: List[str]) -> str:
    return _call_llm(f"Përgjigju statutore duke u bazuar në: {' '.join(rows)}", q, temp=0.0) or ""

def categorize_document_text(text: str) -> str:
    res = _call_llm("Kategorizo. JSON {'category': '...'}.", text[:5000], True)
    return _parse_json_safely(res).get("category", "Të tjera")

def sterilize_legal_text(text: str) -> str:
    from .text_sterilization_service import sterilize_text_for_llm
    return sterilize_text_for_llm(text)

def extract_expense_details_from_text(t: str) -> Dict[str, Any]:
    r = _parse_json_safely(_call_llm("Nxirr shpenzimin JSON.", t[:3000], True))
    return {"category": r.get("category", "Shpenzime"), "amount": float(r.get("amount", 0.0)), "date": r.get("date", datetime.now().strftime("%Y-%m-%d")), "description": r.get("merchant", "")}

def analyze_financial_portfolio(d: str) -> Dict[str, Any]:
    return _parse_json_safely(_call_llm("Analizo financat. JSON.", d, True))

def translate_for_client(t: str) -> str:
    return _call_llm("Përkthe.", t) or ""

def query_global_rag_for_claims(r: str, q: str) -> Dict[str, Any]:
    return _parse_json_safely(_call_llm("Sugjero argumente statutore. JSON.", f"RAG: {r}\nQ: {q}", True))