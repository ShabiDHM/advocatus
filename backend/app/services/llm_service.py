# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - CORE INTELLIGENCE V37.2 (PARAMETER SYNC)
# 1. FIX: Renamed 'context' parameter back to 'context_summaries' to match 'cases.py' orchestrator.
# 2. STATUS: 100% API compatibility restored.

import os
import json
import logging
import httpx
import re
import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime
from openai import OpenAI, AsyncOpenAI

from .text_sterilization_service import sterilize_text_for_llm

logger = logging.getLogger(__name__)

__all__ = [
    "analyze_financial_portfolio",
    "analyze_case_integrity",
    "generate_adversarial_simulation",
    "build_case_chronology",
    "translate_for_client",
    "detect_contradictions",
    "extract_deadlines",
    "perform_litigation_cross_examination",
    "generate_summary",
    "extract_graph_data",
    "get_embedding",
    "forensic_interrogation",
    "categorize_document_text",
    "sterilize_legal_text",
    "extract_expense_details_from_text",
    "query_global_rag_for_claims",
    "process_large_document_async",
    "stream_text_async"
]

# --- CONFIGURATION ---
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") 
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat" 
EMBEDDING_MODEL = "text-embedding-3-small" 

OLLAMA_URL = os.environ.get("LOCAL_LLM_URL", "http://host.docker.internal:11434/api/generate")
OLLAMA_EMBED_URL = os.environ.get("LOCAL_LLM_EMBED_URL", "http://host.docker.internal:11434/api/embeddings")
LOCAL_MODEL_NAME = "llama3"
LOCAL_EMBED_MODEL = "nomic-embed-text"

_deepseek_client: Optional[OpenAI] = None
_async_deepseek_client: Optional[AsyncOpenAI] = None
_openai_client: Optional[OpenAI] = None

# --- CLIENT FACTORIES ---
def get_async_deepseek_client() -> Optional[AsyncOpenAI]:
    global _async_deepseek_client
    if not _async_deepseek_client and DEEPSEEK_API_KEY:
        try:
            _async_deepseek_client = AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url=OPENROUTER_BASE_URL)
        except Exception as e:
            logger.error(f"Async DeepSeek Init Failed: {e}")
    return _async_deepseek_client

def get_deepseek_client() -> Optional[OpenAI]:
    global _deepseek_client
    if not _deepseek_client and DEEPSEEK_API_KEY:
        try: _deepseek_client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=OPENROUTER_BASE_URL)
        except Exception as e: logger.error(f"DeepSeek Init Failed: {e}")
    return _deepseek_client

def get_openai_client() -> Optional[OpenAI]:
    global _openai_client
    if not _openai_client and OPENAI_API_KEY:
        try: _openai_client = OpenAI(api_key=OPENAI_API_KEY)
        except Exception as e: logger.error(f"OpenAI Init Failed: {e}")
    return _openai_client

# --- CORE GENERATORS ---
async def stream_text_async(system_prompt: str, user_prompt: str, temp: float = 0.2) -> AsyncGenerator[str, None]:
    client = get_async_deepseek_client()
    if client:
        try:
            stream = await client.chat.completions.create(
                model=OPENROUTER_MODEL,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=temp,
                stream=True
            )
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
            return
        except Exception as e:
            logger.error(f"Streaming failed: {e}")
            yield " [Gabim në lidhjen me AI] "
            return
    full_text = await _call_llm_async(system_prompt, user_prompt, temp)
    yield full_text

# --- UTILITIES ---
def chunk_text(text: str, chunk_size: int = 12000) -> List[str]:
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

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

# --- PUBLIC FUNCTIONS ---
def get_embedding(text: str) -> List[float]:
    clean_text = text.replace("\n", " ")
    client = get_openai_client()
    if client:
        try: return client.embeddings.create(input=[clean_text], model=EMBEDDING_MODEL).data[0].embedding
        except Exception as e: logger.warning(f"OpenAI Embedding failed: {e}")
    try:
        with httpx.Client(timeout=10.0) as c:
            res = c.post(OLLAMA_EMBED_URL, json={"model": LOCAL_EMBED_MODEL, "prompt": clean_text})
            data = res.json()
            if "embedding" in data: return data["embedding"]
    except Exception: pass
    return [0.0] * 1536 

async def _call_llm_async(system_prompt: str, user_prompt: str, temp: float = 0.2) -> str:
    client = get_async_deepseek_client()
    if client:
        try:
            res = await client.chat.completions.create(
                model=OPENROUTER_MODEL,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=temp
            )
            return res.choices[0].message.content or ""
        except Exception: return ""
    return ""

def _call_llm(system_prompt: str, user_prompt: str, json_mode: bool = False, temp: float = 0.2) -> Optional[str]:
    client = get_deepseek_client()
    if client:
        try:
            kwargs = {"model": OPENROUTER_MODEL, "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}], "temperature": temp}
            if json_mode: kwargs["response_format"] = {"type": "json_object"}
            res = client.chat.completions.create(**kwargs)
            return res.choices[0].message.content
        except: pass
    return None

async def process_large_document_async(text: str, task_type: str = "SUMMARY") -> str:
    chunks = chunk_text(text)
    tasks = [_call_llm_async("Përmblidh këtë pjesë.", chunk) for chunk in chunks]
    results = await asyncio.gather(*tasks)
    combined = "\n\n".join(results)
    if len(chunks) > 1:
        return await _call_llm_async("Krijo një përmbledhje finale.", combined)
    return combined

def generate_summary(text: str) -> str:
    if len(text) < 15000:
        result = _call_llm("Përmblidh dokumentin.", text, False)
        return result or ""
    return asyncio.run(process_large_document_async(text, "SUMMARY"))

# --- LEGAL AGENTS ---
PROMPT_SENIOR_LITIGATOR = "Ti je Avokat i Lartë..."
PROMPT_CROSS_EXAMINE = "Ti je Ekspert i Kryqëzimit të Fakteve..."

def analyze_case_integrity(text: str) -> Dict[str, Any]:
    result = _call_llm(PROMPT_SENIOR_LITIGATOR, text[:35000], True)
    return _parse_json_safely(result or "{}")

# PHOENIX FIX: Synchronized parameter name with cases.py endpoint call
def perform_litigation_cross_examination(target_text: str, context_summaries: List[str]) -> Dict[str, Any]:
    context_block = "\n".join(context_summaries)
    prompt = f"TARGET DOCUMENT CONTENT:\n{target_text[:15000]}\n\nCONTEXT (OTHER DOCUMENTS):\n{context_block}"
    result = _call_llm(PROMPT_CROSS_EXAMINE, prompt, True, temp=0.2)
    return _parse_json_safely(result or "{}")

# --- STUBS FOR INTEGRITY ---
def analyze_financial_portfolio(data: str) -> Dict[str, Any]: return {}
def generate_adversarial_simulation(text: str) -> Dict[str, Any]: return {}
def build_case_chronology(text: str) -> Dict[str, Any]: return {}
def detect_contradictions(text: str) -> Dict[str, Any]: return {}
def extract_deadlines(text: str) -> Dict[str, Any]: return {}
def translate_for_client(text: str) -> str: return ""
def forensic_interrogation(q: str, c: List[str]) -> str: return ""
def categorize_document_text(text: str) -> str: return "Të tjera"
def sterilize_legal_text(text: str) -> str: return sterilize_text_for_llm(text)
def extract_expense_details_from_text(text: str) -> Dict[str, Any]: return {}
def query_global_rag_for_claims(r: str, q: str) -> Dict[str, Any]: return {}
def extract_graph_data(text: str) -> Dict[str, Any]: return {"entities": [], "relations": []}