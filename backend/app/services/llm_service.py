# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - CORE INTELLIGENCE V68.1 (POLYMATH & DOMAIN INTEGRITY)
# 1. FIX: Updated KOSOVO_LEGAL_BRAIN to be Domain-Agnostic (Criminal, Civil, Admin).
# 2. FIX: Refined stream_text_async to ensure prompt-priority for complex legal drafting.
# 3. STABILITY: Retained 10-concurrency Semaphore and Hydra Map-Reduce logic.
# 4. STATUS: 100% Compatible. Zero-Degradation.

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
OPENROUTER_MODEL = "deepseek/deepseek-chat" # Can be changed to deepseek/deepseek-r1 for higher IQ
EMBEDDING_MODEL = "text-embedding-3-small"

_async_client: Optional[AsyncOpenAI] = None
_api_semaphore: Optional[asyncio.Semaphore] = None

def get_deepseek_client():
    return OpenAI(api_key=DEEPSEEK_API_KEY, base_url=OPENROUTER_BASE_URL) if DEEPSEEK_API_KEY else None

def get_openai_client():
    return OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

def get_async_deepseek_client():
    global _async_client
    if _async_client: return _async_client
    if DEEPSEEK_API_KEY:
        _async_client = AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url=OPENROUTER_BASE_URL)
        return _async_client
    return None

def get_semaphore() -> asyncio.Semaphore:
    """The Global Traffic Light for API Calls (Limit 10)."""
    global _api_semaphore
    if _api_semaphore is None:
        _api_semaphore = asyncio.Semaphore(10)
    return _api_semaphore

def _parse_json_safely(content: Optional[str]) -> Dict[str, Any]:
    if not content: return {}
    try:
        return json.loads(content)
    except:
        match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
        if match:
            try: return json.loads(match.group(1))
            except: pass
        try:
            match_loose = re.search(r'(\{.*\})', content, re.DOTALL)
            if match_loose: return json.loads(match_loose.group(1))
        except: pass
        return {"raw_response": content, "error": "JSON_PARSE_FAILED"}

# --- INTELLIGENCE CORE ---

# PHOENIX FIX: Universal Legal Brain - No longer limited to just Civil/Family
KOSOVO_LEGAL_BRAIN = """
ROLI: Ti je 'Senior Legal Partner' në një firmë ligjore prestigjioze në Kosovë. 
EKSPERTIZA: Njohës i thellë i të gjitha fushave të sistemit ligjor të Kosovës (E Drejta Penale, Civile, Familjare, e Punës, Detyrimeve dhe Administrative).
DETYRA: Të prodhosh analiza ligjore të nivelit të Gjykatës Supreme: të sakta, të bazuara në fakte dhe strategjike.
GJUHA: VETËM SHQIP JURIDIKE PROFESIONALE.
"""

def _call_llm(system_prompt: str, user_prompt: str, json_mode: bool = False, temp: float = 0.1) -> Optional[str]:
    client = get_deepseek_client()
    if not client: return None
    try:
        # Prepend the Universal Brain for context
        full_system = f"{KOSOVO_LEGAL_BRAIN}\n{system_prompt}"
        kwargs = {"model": OPENROUTER_MODEL, "messages": [{"role": "system", "content": full_system}, {"role": "user", "content": user_prompt}], "temperature": temp}
        if json_mode: kwargs["response_format"] = {"type": "json_object"}
        res = client.chat.completions.create(**kwargs)
        return res.choices[0].message.content
    except Exception as e:
        logger.error(f"LLM Call Failed: {e}")
        return None

async def _call_llm_async(system_prompt: str, user_prompt: str, json_mode: bool = False, temp: float = 0.1) -> Optional[str]:
    client = get_async_deepseek_client()
    sem = get_semaphore()
    if not client: return None
    
    async with sem:
        try:
            full_system = f"{KOSOVO_LEGAL_BRAIN}\n{system_prompt}"
            kwargs = {"model": OPENROUTER_MODEL, "messages": [{"role": "system", "content": full_system}, {"role": "user", "content": user_prompt}], "temperature": temp}
            if json_mode: kwargs["response_format"] = {"type": "json_object"}
            res = await client.chat.completions.create(**kwargs)
            return res.choices[0].message.content
        except Exception as e:
            logger.error(f"Async LLM Call Failed: {e}")
            return None

# --- HYDRA UTILITIES ---

def chunk_text(text: str, chunk_size: int = 5000) -> List[str]:
    if not text: return []
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

async def process_chunks_parallel(text: str, system_prompt: str) -> List[str]:
    chunks = chunk_text(text)
    if not chunks: return []
    tasks = [_call_llm_async(system_prompt, f"SEGMENTI LIGJOR:\n{chunk}") for chunk in chunks]
    results = await asyncio.gather(*tasks)
    return [res for res in results if res]

async def process_large_document_async(text: str, task_type: str = "SUMMARY") -> str:
    if not text: return "Teksti nuk u gjet."
    map_prompt = "Analizo këtë segment të dokumentit. Identifiko faktet kyçe dhe shkeljet potenciale materiale."
    reduce_prompt = "Sintezo këto analiza të pjesshme në një përmbledhje finale profesionale dhe koherente."
    partial_analyses = await process_chunks_parallel(text, map_prompt)
    if not partial_analyses: return "Analiza dështoi."
    if len(partial_analyses) == 1: return partial_analyses[0]
    combined_context = "\n---\n".join(partial_analyses)
    final_opinion = await _call_llm_async(reduce_prompt, f"ANALIZAT E PJESSHME:\n{combined_context}")
    return final_opinion or "Sinteza dështoi."

# --- SPECIALIZED FUNCTIONS ---

def analyze_case_integrity(context: str) -> Dict[str, Any]:
    system_prompt = f"""--- URDHËR I PADISKUTUESHËM: ZERO-TRUST RAG ---
    1. ANALIZA JOTE DUHET TË BAZOHET **VETËM** NË KONTEKSTIN E OFRUAR.
    --- DETYRA: KRIJO ANALIZËN JSON ---
    {{
      "executive_summary": "...",
      "paralegal_checklist": {{ "missing_evidence": [], "action_plan": [] }},
      "legal_audit": {{ "burden_of_proof": "...", "legal_basis": [] }},
      "strategic_recommendation": {{ "recommendation_text": "...", "success_probability": "XX%", "risk_level": "..." }}
    }}"""
    safe_context = context[:100000] if context else "Konteksti nuk u ofrua."
    new_analysis = _parse_json_safely(_call_llm(system_prompt, safe_context, json_mode=True, temp=0.2))
    if not new_analysis or "executive_summary" not in new_analysis:
        return {"summary": "Analiza dështoi.", "key_issues": [], "legal_basis": [], "strategic_analysis": "Nuk ka.", "burden_of_proof": "Nuk ka.", "missing_evidence": [], "action_plan": [], "risk_level": "I LARTË", "success_probability": "0%"}
    legal_audit = new_analysis.get("legal_audit", {})
    paralegal_checklist = new_analysis.get("paralegal_checklist", {})
    strategic_rec = new_analysis.get("strategic_recommendation", {})
    return {"summary": new_analysis.get("executive_summary"), "key_issues": [], "burden_of_proof": legal_audit.get("burden_of_proof"), "legal_basis": legal_audit.get("legal_basis"), "strategic_analysis": strategic_rec.get("recommendation_text"), "missing_evidence": paralegal_checklist.get("missing_evidence"), "action_plan": paralegal_checklist.get("action_plan"), "success_probability": strategic_rec.get("success_probability"), "risk_level": strategic_rec.get("risk_level")}

def generate_adversarial_simulation(context: str) -> Dict[str, Any]:
    system_prompt = "ROLI: Avokati i Palës Kundërshtare. Gjej pikat tona më të dobëta materiale. JSON: {'opponent_strategy':'', 'weakness_attacks':[], 'counter_claims':[]}"
    return _parse_json_safely(_call_llm(system_prompt, context[:30000], True, temp=0.4))

def build_case_chronology(text: str) -> Dict[str, Any]:
    system_prompt = "DETYRA: Ekstrakto një kronologji të verifikuar. JSON: {'timeline':[]}"
    return _parse_json_safely(_call_llm(system_prompt, text[:40000], True))

def detect_contradictions(text: str) -> Dict[str, Any]:
    system_prompt = "DETYRA: Gjej mospërputhje mes dëshmive dhe provave. JSON: {'contradictions':[]}"
    return _parse_json_safely(_call_llm(system_prompt, text[:30000], True))

def extract_graph_data(text: str) -> Dict[str, Any]:
    system_prompt = "Nxjerr Entitetet dhe Lidhjet mes tyre. JSON: {'nodes':[], 'edges':[]}."
    return _parse_json_safely(_call_llm(system_prompt, text[:30000], True))

def analyze_financial_portfolio(data: str) -> Dict[str, Any]:
    system_prompt = "Analizo të dhënat financiare. JSON."
    return _parse_json_safely(_call_llm(system_prompt, data, True))

def translate_for_client(legal_text: str) -> str:
    return _call_llm("Përkthe këtë tekst ligjor në gjuhë popullore.", legal_text) or "Përkthimi dështoi."

def extract_deadlines(text: str) -> Dict[str, Any]:
    system_prompt = "Gjej të gjitha Afatet Ligjore. JSON: {'deadlines':[]}."
    return _parse_json_safely(_call_llm(system_prompt, text[:20000], True))

def perform_litigation_cross_examination(target: str, context: List[str]) -> Dict[str, Any]:
    context_str = "\n".join(context)
    system_prompt = f"Përgatit pyetje kryqëzuese për: {target}. JSON: {{'questions':[]}}."
    return _parse_json_safely(_call_llm(system_prompt, context_str[:40000], True))

def generate_summary(text: str) -> str:
    return _call_llm("Krijo një përmbledhje ekzekutive në 3 pika.", text[:20000]) or ""

def get_embedding(text: str) -> List[float]:
    client = get_openai_client()
    if not client: return [0.0] * 1536
    try:
        res = client.embeddings.create(input=[text.replace("\n", " ")], model=EMBEDDING_MODEL)
        return res.data[0].embedding
    except Exception as e:
        logger.error(f"Embedding failed: {e}")
        return [0.0] * 1536

def forensic_interrogation(question: str, context_rows: List[str]) -> str:
    context_block = "\n---\n".join(context_rows)
    prompt = f"Përgjigju VETËM duke përdorur dokumentet: {context_block}"
    return _call_llm(prompt, question, temp=0.0) or "Nuk ka informacion."

def categorize_document_text(text: str) -> str:
    res = _call_llm("Kategorizo këtë tekst. Kthe JSON {'category': '...'}.", text[:5000], True)
    return _parse_json_safely(res).get("category", "Të tjera")

def sterilize_legal_text(text: str) -> str:
    return sterilize_text_for_llm(text)

def extract_expense_details_from_text(raw_text: str) -> Dict[str, Any]:
    res = _parse_json_safely(_call_llm("Nxirr shpenzimin JSON: {'amount': float, 'date': 'YYYY-MM-DD', 'merchant': 'emri', 'category': 'kategoria'}.", raw_text[:3000], True))
    return {"category": res.get("category", "Shpenzime"), "amount": float(res.get("amount", 0.0)), "date": res.get("date", datetime.now().strftime("%Y-%m-%d")), "description": res.get("merchant", "")}

def query_global_rag_for_claims(rag_results: str, user_query: str) -> Dict[str, Any]:
    return _parse_json_safely(_call_llm("Sugjero argumente shtesë nga praktika gjyqësore. JSON: {'suggestions':[]}.", f"RAG Results: {rag_results}\nQuery: {user_query}", True))

async def stream_text_async(system_prompt: str, user_prompt: str, temp: float = 0.2) -> AsyncGenerator[str, None]:
    client = get_async_deepseek_client()
    sem = get_semaphore()
    if not client: yield "[SISTEMI OFFLINE]"; return
    
    # Prepend the Universal Brain context
    full_system = f"{KOSOVO_LEGAL_BRAIN}\n{system_prompt}"
    
    async with sem:
        try:
            stream = await client.chat.completions.create(
                model=OPENROUTER_MODEL, 
                messages=[
                    {"role": "system", "content": full_system}, 
                    {"role": "user", "content": user_prompt}
                ], 
                temperature=temp, 
                stream=True
            )
            async for chunk in stream:
                if chunk.choices[0].delta.content: 
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"Stream Error: {e}")
            yield f"[GABIM NË SISTEM: {str(e)}]"