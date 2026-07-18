# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - MASTER INTELLIGENCE V80.0 (SAAS PIVOT)
# 1. FIX: Added synchronous '_call_llm' helper to prevent AttributeError crashes in spreadsheet_service.py.
# 2. MODEL: Uses OpenRouter deepseek-chat and text-embedding-3-small.

import os
import json
import logging
import re
import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator
from openai import OpenAI, AsyncOpenAI

logger = logging.getLogger(__name__)

OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1"

EMBEDDING_MODEL = "openai/text-embedding-3-small" 
CHAT_MODEL = "deepseek/deepseek-chat"
AI_DISCLAIMER = "\n\n---\n*Kjo përgjigje është gjeneruar nga AI, vetëm për referencë.*"

def _get_sync_client(): 
    return OpenAI(api_key=OPENROUTER_KEY, base_url=OPENROUTER_URL)

def _get_async_client(): 
    return AsyncOpenAI(api_key=OPENROUTER_KEY, base_url=OPENROUTER_URL)

def _call_llm(system_prompt: str, user_content: str, json_mode: bool = False, temperature: float = 0.2) -> str:
    """
    Synchronous helper for backend services to perform standard non-streaming generation.
    """
    if not OPENROUTER_KEY:
        return "Gabim: Mungon OPENROUTER_API_KEY"
    try:
        client = _get_sync_client()
        kwargs = {
            "model": CHAT_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            "temperature": temperature
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
            
        res = client.chat.completions.create(**kwargs)
        return res.choices[0].message.content or ""
    except Exception as e:
        logger.error(f"Error in _call_llm: {e}")
        return ""

def get_embedding(text: str) -> List[float]:
    """Generates 1536-dim vectors via OpenRouter."""
    if not text or not OPENROUTER_KEY: 
        return [0.0] * 1536
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
            if chunk.choices[0].delta.content: 
                yield chunk.choices[0].delta.content
        yield AI_DISCLAIMER
    except Exception as e: 
        yield f"[Gabim: {str(e)}]"

# --- LIVE RECONSTRUCTION OF SPECIALIZED WAR ROOM METHODS ---

async def generate_adversarial_simulation(context: str) -> Dict[str, Any]:
    """
    Generates an adversarial simulation predicting the opponent's strategy and attack angles.
    """
    if not OPENROUTER_KEY:
        return {}
    client = _get_async_client()
    system_prompt = """
    Detyra: Shërbe si një avokat kundërshtar shumë i zgjuar dhe agresiv. Analizo kontekstin e rastit dhe identifiko strategjinë më të mirë të sulmit për palën kundërshtare.
    
    Përgjigju VETËM në formatin e strukturuar JSON si më poshtë:
    {
      "opponent_strategy": "Përshkrimi i hollësishëm i strategjisë agresive të kundërshtarit...",
      "weakness_attacks": [
         "Sulm specifik i bazuar në dobësitë tona ose provat që na mungojnë...",
         "Sulm tjetër specifik..."
      ]
    }
    MOS shto asnjë tekst tjetër jashtë objektit JSON.
    """
    try:
        res = await client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"KONTEKSTI I RASTIT:\n{context}"}
            ],
            temperature=0.4,
            response_format={"type": "json_object"}
        )
        content = res.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        logger.error(f"Failed to generate adversarial simulation: {e}")
        return {
            "opponent_strategy": "Dështoi simulimi i kundërshtarit.",
            "weakness_attacks": ["Nuk u identifikuan dot pikat e sulmit."]
        }

async def build_case_chronology(context: str) -> Dict[str, Any]:
    """
    Builds a structured chronological timeline of events based on case facts.
    """
    if not OPENROUTER_KEY:
        return {}
    client = _get_async_client()
    system_prompt = """
    Detyra: Krijo një kronologji të saktë dhe të strukturuar të ngjarjeve bazuar në faktet e rastit.
    Çdo ngjarje duhet të ketë një datë (p.sh. DD.MM.YYYY ose Viti) dhe përshkrimin përkatës.
    
    Përgjigju VETËM në formatin e strukturuar JSON si më poshtë:
    {
      "timeline": [
        {"date": "Data e ngjarjes", "event": "Përshkrimi i saktë i asaj që ka ndodhur"}
      ]
    }
    MOS shto asnjë tekst tjetër jashtë objektit JSON.
    """
    try:
        res = await client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"KONTEKSTI I RASTIT:\n{context}"}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        content = res.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        logger.error(f"Failed to build chronology: {e}")
        return {"timeline": []}

async def detect_contradictions(context: str) -> Dict[str, Any]:
    """
    Detects factual or legal contradictions in the context.
    """
    if not OPENROUTER_KEY:
        return {}
    client = _get_async_client()
    system_prompt = """
    Detyra: Analizo të gjitha dëshmitë, deklaratat dhe faktet në kontekst për të gjetur kontradikta, mospërputhme ose deklarata të rreme të palës tjetër ose dëshmitarëve.
    
    Përgjigju VETËM në formatin e strukturuar JSON si më poshtë:
    {
      "contradictions": [
        {
          "severity": "LOW, MEDIUM ose HIGH",
          "claim": "Deklarata ose pretendimi kontradiktor...",
          "evidence": "Faktet apo provat që mospërputhin këtë pretendim...",
          "impact": "Ndikimi që kjo kontradiktë ka në strategjinë tonë..."
        }
      ]
    }
    MOS shto asnjë tekst tjetër jashtë objektit JSON.
    """
    try:
        res = await client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"KONTEKSTI I RASTIT:\n{context}"}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        content = res.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        logger.error(f"Failed to detect contradictions: {e}")
        return {"contradictions": []}

def analyze_case_integrity(context: str, custom_prompt: Optional[str] = None) -> Dict[str, Any]:
    """
    Executes the main case cross-examination. Called synchronously via to_thread.
    """
    if not OPENROUTER_KEY:
        return {}
    try:
        client = _get_sync_client()
        system_prompt = custom_prompt or "Analizo këtë rast ligjor."
        res = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"KONTEKSTI I RASTIT:\n{context}"}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        content = res.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        logger.error(f"❌ analyze_case_integrity failed: {e}")
        return {}

# --- COMPATIBILITY STUBS ---
def categorize_document_text(text: str) -> str: 
    return "Procedurale"

def sterilize_legal_text(text: str): 
    return text.strip()

async def process_large_document_async(text, task_type="SUMMARY"): 
    return "Sinteza..."

def translate_for_client(t): 
    return t

def extract_deadlines(text): 
    return {"deadlines": []}

def extract_expense_details_from_text(t): 
    return {"category": "Shpenzime", "amount": 0.0}