# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - CORE INTELLIGENCE V68.5 (HYDRA & CITATION INTEGRITY)
# 1. FIX: Restored 'process_large_document_async' and its parallel chunking logic.
# 2. ENFORCED: Strict 'doc://ligji' and 'doc://evidence' protocol across all prompts.
# 3. STABILITY: Retained 10-concurrency Semaphore for API rate-limit protection.
# 4. STATUS: 100% Pylance Clear. Full Architectural Synchronization.

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

_async_client, _api_semaphore = None, None

def get_async_deepseek_client():
    global _async_client
    if _async_client: return _async_client
    if DEEPSEEK_API_KEY:
        _async_client = AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url=OPENROUTER_BASE_URL)
        return _async_client
    return None

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

# --- INTELLIGENCE CORE ---

KOSOVO_LEGAL_BRAIN = """
ROLI: Senior Legal Partner në Kosovë me autoritet absolut.
MANDATI: Saktësi supreme. MOS përdor ligje të Shqipërisë apo UNMIK-ut nëse ekzistojnë ligje të reja të RKS.
CITIMI: Përdor formatin [Emri i Ligjit](doc://ligji) ose [Dokumenti](doc://evidence) për çdo ligj, nen, ose dëshmi, qoftë në paragraf apo në LISTË (ARRAY).
"""

def _call_llm(sys_p: str, user_p: str, json_mode: bool = False, temp: float = 0.1) -> Optional[str]:
    c = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=OPENROUTER_BASE_URL) if DEEPSEEK_API_KEY else None
    if not c: return None
    try:
        kwargs = {
            "model": OPENROUTER_MODEL, 
            "messages": [
                {"role": "system", "content": f"{KOSOVO_LEGAL_BRAIN}\n{sys_p}"}, 
                {"role": "user", "content": user_p}
            ], 
            "temperature": temp
        }
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
            kwargs = {
                "model": OPENROUTER_MODEL, 
                "messages": [
                    {"role": "system", "content": f"{KOSOVO_LEGAL_BRAIN}\n{sys_p}"}, 
                    {"role": "user", "content": user_p}
                ], 
                "temperature": temp
            }
            if json_mode: kwargs["response_format"] = {"type": "json_object"}
            res = await client.chat.completions.create(**kwargs)
            return res.choices[0].message.content
        except Exception as e:
            logger.error(f"Async LLM Error: {e}")
            return None

# --- HYDRA LOGIC (RESTORED) ---

async def process_large_document_async(text: str, task_type: str = "SUMMARY") -> str:
    """
    Map-Reduce logic for large legal files.
    """
    if not text: return "Teksti nuk u gjet."
    
    map_prompt = "Analizo këtë segment të dokumentit ligjor. Identifiko faktet kyçe dhe shkeljet materiale."
    reduce_prompt = "Sintezo këto analiza të pjesshme në një opinion juridik koherent të nivelit të Gjykatës Supreme."
    
    # Split text into 5000 char chunks
    chunks = [text[i:i+5000] for i in range(0, len(text), 5000)]
    tasks = [_call_llm_async(map_prompt, f"SEGMENTI LIGJOR:\n{c}") for c in chunks]
    
    partial_results = await asyncio.gather(*tasks)
    combined_context = "\n---\n".join([r for r in partial_results if r])
    
    if not combined_context: return "Analiza dështoi."
    
    final_opinion = await _call_llm_async(reduce_prompt, f"ANALIZAT E PJESSHME:\n{combined_context}")
    return final_opinion or "Sinteza dështoi."

# --- ANALYSIS PERSONA FUNCTIONS ---

def analyze_case_integrity(context: str, custom_prompt: Optional[str] = None) -> Dict[str, Any]:
    sys = custom_prompt or "Analizo integritetin e rastit. JSON."
    return _parse_json_safely(_call_llm(sys, context[:100000], True, 0.1))

def generate_adversarial_simulation(context: str) -> Dict[str, Any]:
    sys = """
    ROLI: Avokati i Palës Kundërshtare. 
    CITIMI: Përdor [Emri i Ligjit](doc://ligji) për të sulmuar rasti tonë.
    JSON: {'opponent_strategy':'', 'weakness_attacks':[], 'counter_claims':[]}
    """
    return _parse_json_safely(_call_llm(sys, context[:30000], True, 0.4))

def detect_contradictions(text: str) -> Dict[str, Any]:
    sys = """
    DETYRA: Gjej mospërputhje. 
    FORMATI: Cito me [Emri i Ligjit/Dokumentit](doc://ligji).
    JSON: {'contradictions': [{'severity': 'HIGH', 'claim': '...', 'evidence': '...', 'impact': '...'}]}
    """
    return _parse_json_safely(_call_llm(sys, text[:30000], True))

def build_case_chronology(text: str) -> Dict[str, Any]:
    return _parse_json_safely(_call_llm("Krijo kronologjinë. JSON: {'timeline':[]}", text[:40000], True))

# --- UTILITIES ---

def extract_deadlines(text: str) -> Dict[str, Any]:
    return _parse_json_safely(_call_llm("Gjej afatet. JSON: {'deadlines':[]}", text[:20000], True))

def perform_litigation_cross_examination(target: str, context: List[str]) -> Dict[str, Any]:
    return _parse_json_safely(_call_llm(f"Pyetje kryqëzuese për: {target}. JSON.", "\n".join(context)[:40000], True))

def generate_summary(text: str) -> str:
    return _call_llm("Krijo një përmbledhje ekzekutive në 3 pika.", text[:20000]) or ""

def extract_graph_data(text: str) -> Dict[str, Any]:
    return _parse_json_safely(_call_llm("Nxjerr Entitetet dhe Lidhjet. JSON: {'nodes':[], 'edges':[]}", text[:30000], True))

def get_embedding(text: str) -> List[float]:
    c = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
    if not c: return [0.0] * 1536
    try:
        res = c.embeddings.create(input=[text.replace("\n", " ")], model=EMBEDDING_MODEL)
        return res.data[0].embedding
    except: return [0.0] * 1536

async def stream_text_async(sys_p: str, user_p: str, temp: float = 0.2) -> AsyncGenerator[str, None]:
    client = get_async_deepseek_client()
    if not client: yield "[SISTEMI OFFLINE]"; return
    async with get_semaphore():
        try:
            stream = await client.chat.completions.create(
                model=OPENROUTER_MODEL, 
                messages=[
                    {"role": "system", "content": f"{KOSOVO_LEGAL_BRAIN}\n{sys_p}"}, 
                    {"role": "user", "content": user_p}
                ], 
                temperature=temp, 
                stream=True
            )
            async for chunk in stream:
                if chunk.choices[0].delta.content: 
                    yield chunk.choices[0].delta.content
        except Exception as e: 
            yield f"[Gabim: {str(e)}]"

def forensic_interrogation(q: str, rows: List[str]) -> str:
    prompt = f"Përgjigju shkurt duke u bazuar në këto dokumente: {' '.join(rows)}"
    return _call_llm(prompt, q, temp=0.0) or "Nuk ka informacion."

def categorize_document_text(text: str) -> str:
    res = _call_llm("Kategorizo këtë tekst. JSON {'category': '...'}.", text[:5000], True)
    return _parse_json_safely(res).get("category", "Të tjera")

def sterilize_legal_text(text: str) -> str: 
    return sterilize_text_for_llm(text)

def extract_expense_details_from_text(raw_text: str) -> Dict[str, Any]:
    res = _parse_json_safely(_call_llm("Nxirr shpenzimin JSON: {'amount': float, 'date': 'YYYY-MM-DD', 'merchant': 'emri', 'category': 'kategoria'}.", raw_text[:3000], True))
    return {
        "category": res.get("category", "Shpenzime"), 
        "amount": float(res.get("amount", 0.0)), 
        "date": res.get("date", datetime.now().strftime("%Y-%m-%d")), 
        "description": res.get("merchant", "")
    }

def analyze_financial_portfolio(data: str) -> Dict[str, Any]:
    return _parse_json_safely(_call_llm("Analizo të dhënat financiare. JSON.", data, True))

def translate_for_client(legal_text: str) -> str:
    return _call_llm("Përkthe këtë tekst ligjor në gjuhë popullore.", legal_text) or "Dështoi."

def query_global_rag_for_claims(rag_results: str, user_query: str) -> Dict[str, Any]:
    return _parse_json_safely(_call_llm("Sugjero argumente shtesë. JSON: {'suggestions':[]}.", f"RAG: {rag_results}\nQuery: {user_query}", True))