# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - MASTER INTELLIGENCE V78.0 (SAAS PIVOT)
# 1. FIX: Routes everything through OpenRouter for high-availability.
# 2. MODEL: Uses 'openai/text-embedding-3-small' (1536-dim) for SaaS precision.

import os, json, logging, re, asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator
from openai import OpenAI, AsyncOpenAI

logger = logging.getLogger(__name__)

OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1"

EMBEDDING_MODEL = "openai/text-embedding-3-small" 
CHAT_MODEL = "deepseek/deepseek-chat"
AI_DISCLAIMER = "\n\n---\n*Kjo përgjigje është gjeneruar nga AI, vetëm për referencë.*"

def _get_sync_client(): return OpenAI(api_key=OPENROUTER_KEY, base_url=OPENROUTER_URL)
def _get_async_client(): return AsyncOpenAI(api_key=OPENROUTER_KEY, base_url=OPENROUTER_URL)

def get_embedding(text: str) -> List[float]:
    """Generates 1536-dim vectors via OpenRouter."""
    if not text or not OPENROUTER_KEY: return [0.0] * 1536
    try:
        client = _get_sync_client()
        res = client.embeddings.create(input=[text.replace("\n", " ")], model=EMBEDDING_MODEL)
        return res.data[0].embedding
    except Exception as e:
        logger.error(f"❌ OpenRouter Embedding Failure: {e}")
        return [0.0] * 1536

async def stream_text_async(sys_p: str, user_p: str, temp: float = 0.2) -> AsyncGenerator[str, None]:
    client = _get_async_client()
    try:
        stream = await client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[{"role": "system", "content": sys_p}, {"role": "user", "content": user_p}],
            temperature=temp, stream=True
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content: yield chunk.choices[0].delta.content
        yield AI_DISCLAIMER
    except Exception as e: yield f"[Gabim: {str(e)}]"

# --- COMPATIBILITY STUBS ---
def categorize_document_text(text: str) -> str: return "Procedurale"
def analyze_case_integrity(context, custom_prompt=None): return {"status": "active"}
def sterilize_legal_text(text: str): return text.strip()
async def process_large_document_async(text, task_type="SUMMARY"): return "Sinteza..."
def translate_for_client(t): return t
def extract_deadlines(text): return {"deadlines": []}
def extract_expense_details_from_text(t): return {"category": "Shpenzime", "amount": 0.0}