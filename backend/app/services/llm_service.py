# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - CORE INTELLIGENCE V69.2 (ANTI-PARROT ENFORCEMENT)
# 1. FIX: Enforced 'Argumentative Reasoning' - AI must justify every law citation.
# 2. RESTORED: All 18 legacy and parallel functions (Hydra Map-Reduce).
# 3. ENFORCED: Strict 'doc://ligji' formatting for all domains.
# 4. STATUS: Unabridged. Total Integrity achieved.

import os, json, logging, re, asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime
from openai import OpenAI, AsyncOpenAI
from .text_sterilization_service import sterilize_text_for_llm

logger = logging.getLogger(__name__)

# --- UNABRIDGED EXPORT LIST ---
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

# --- SENIOR PARTNER UNIVERSAL PERSONA ---
KOSOVO_LEGAL_BRAIN = """
ROLI: Ti je 'Senior Legal Partner' në Kosovë.
MANDATI: Është e ndaluar të japësh vetëm emrin e ligjit (Parroting).
DETYRA: Për çdo ligj të cituar, DUHET:
1. Të përdorësh formatin: [Emri i Ligjit, Neni X](doc://ligji).
2. Të tregosh 'RELEVANCËN' (Pse ky ligj mbron ose rrezikon palën në këtë rast specifik).
HIERARKIA: Alimentacion/Kujdestari -> [Ligji 2004/32 Për Familjen](doc://ligji).
"""

def _call_llm(sys_p: str, user_p: str, json_mode: bool = False, temp: float = 0.1) -> Optional[str]:
    c = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=OPENROUTER_BASE_URL) if DEEPSEEK_API_KEY else None
    if not c: return None
    try:
        messages = [{"role": "system", "content": f"{KOSOVO_LEGAL_BRAIN}\n{sys_p}"}, {"role": "user", "content": user_p}]
        kwargs = {"model": OPENROUTER_MODEL, "messages": messages, "temperature": temp}
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

# --- HYDRA PARALLEL PROCESSING (UNABRIDGED) ---

async def process_large_document_async(text: str, task_type: str = "SUMMARY") -> str:
    if not text: return "Nuk u gjet tekst."
    map_p = "Analizo këtë segment. Identifiko faktet dhe citoni [Ligjin](doc://ligji)."
    reduce_p = "Sintezo në opinion suprem juridik me citime të plota [Ligji](doc://ligji)."
    chunks = [text[i:i+5000] for i in range(0, len(text), 5000)]
    tasks = [_call_llm_async(map_p, f"SEGMENTI:\n{c}") for c in chunks]
    results = await asyncio.gather(*tasks)
    combined = "\n---\n".join([r for r in results if r])
    return await _call_llm_async(reduce_p, f"ANALIZAT:\n{combined}") or "Sinteza dështoi."

# --- ANALYSIS PERSONA FUNCTIONS ---

def analyze_case_integrity(context: str, custom_prompt: Optional[str] = None) -> Dict[str, Any]:
    sys = custom_prompt or "Analizo integritetin statutore. Kthe JSON."
    return _parse_json_safely(_call_llm(sys, context[:100000], True, 0.1))

def generate_adversarial_simulation(context: str) -> Dict[str, Any]:
    sys = "Avokati Kundërshtar. Gjej dobësitë. Cito [Emri](doc://ligji). JSON: {'opponent_strategy':'', 'weakness_attacks':[], 'counter_claims':[]}"
    return _parse_json_safely(_call_llm(sys, context[:30000], True, 0.4))

def detect_contradictions(text: str) -> Dict[str, Any]:
    sys = "Gjej mospërputhjet. Cito [Ligji/Dokumenti](doc://ligji). JSON: {'contradictions': [{'severity': 'HIGH', 'claim': '...', 'evidence': '...', 'impact': '...'}]}"
    return _parse_json_safely(_call_llm(sys, text[:30000], True))

def build_case_chronology(text: str) -> Dict[str, Any]:
    sys = "Nxirr kronologjinë. Përdor 'date' dhe 'event'. JSON: {'timeline': []}"
    return _parse_json_safely(_call_llm(sys, text[:40000], True))

# --- UTILITIES ---

def extract_deadlines(text: str) -> Dict[str, Any]:
    return _parse_json_safely(_call_llm("Gjej afatet. JSON: {'deadlines':[]}", text[:20000], True))

def perform_litigation_cross_examination(target: str, context: List[str]) -> Dict[str, Any]:
    return _parse_json_safely(_call_llm(f"Pyetje për: {target}. JSON.", "\n".join(context)[:40000], True))

def generate_summary(text: str) -> str:
    return _call_llm("Krijo përmbledhje në 3 pika.", text[:20000]) or ""

def extract_graph_data(text: str) -> Dict[str, Any]:
    return _parse_json_safely(_call_llm("Nxjerr nyjet. JSON: {'nodes':[], 'edges':[]}", text[:30000], True))

def get_embedding(text: str) -> List[float]:
    from openai import OpenAI as OAI
    c = OAI(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None
    if not c: return [0.0] * 1536
    try: return c.embeddings.create(input=[text.replace("\n", " ")], model=EMBEDDING_MODEL).data[0].embedding
    except: return [0.0] * 1536

async def stream_text_async(sys_p: str, user_p: str, temp: float = 0.2) -> AsyncGenerator[str, None]:
    client = get_async_deepseek_client()
    if not client: yield "[OFFLINE]"; return
    async with get_semaphore():
        try:
            stream = await client.chat.completions.create(model=OPENROUTER_MODEL, messages=[{"role": "system", "content": f"{KOSOVO_LEGAL_BRAIN}\n{sys_p}"}, {"role": "user", "content": user_p}], temperature=temp, stream=True)
            async for chunk in stream:
                if chunk.choices[0].delta.content: yield chunk.choices[0].delta.content
        except Exception as e: yield f"[Gabim: {str(e)}]"

def forensic_interrogation(q: str, rows: List[str]) -> str:
    return _call_llm(f"Përgjigju statutore me [Ligji](doc://ligji) duke u bazuar në: {' '.join(rows)}", q, temp=0.0) or ""

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
    return _parse_json_safely(_call_llm("Argumente statutore me [Ligji](doc://ligji). JSON.", f"RAG: {r}\nQ: {q}", True))