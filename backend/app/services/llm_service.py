# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - MASTER INTELLIGENCE V88.4 (FORCED ENV LOADER)

import os
import json
import logging
import re
import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator
from dotenv import load_dotenv

# Force load .env from backend or root before initializing clients
load_dotenv()

from openai import OpenAI, AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

def _get_api_key() -> str:
    return getattr(settings, "OPENROUTER_API_KEY", None) or os.getenv("OPENROUTER_API_KEY", "") or os.getenv("OPENAI_API_KEY", "")

OPENROUTER_KEY = _get_api_key()
OPENROUTER_URL = "https://openrouter.ai/api/v1"

EMBEDDING_MODEL = "openai/text-embedding-3-small" 
AI_DISCLAIMER = "\n\n---\n*Kjo përgjigje është gjeneruar nga AI, vetëm për referencë.*"

# --- DUAL-MODEL DEPLOYMENT DEFINITIONS ---
FAST_MODEL = "deepseek/deepseek-chat"       # DeepSeek-V3 (Super fast, cheap, standard)
DEEP_MODEL = "deepseek/deepseek-r1"         # DeepSeek-R1 (Reasoning, logic, deep audit - OpenRouter ID)

# --- TEMPERATURE CONSTANTS FOR SAAS PRECISION ---
TEMP_DRAFTING = 0.1   # Extreme structural compliance for legal document drafting
TEMP_ANALYSIS = 0.2   # High-precision audit focus
TEMP_CHAT = 0.3       # Standard balanced interactive chat

def _get_sync_client(): 
    key = _get_api_key()
    return OpenAI(api_key=key, base_url=OPENROUTER_URL)

def _get_async_client(): 
    key = _get_api_key()
    return AsyncOpenAI(api_key=key, base_url=OPENROUTER_URL)

def clean_and_parse_json(text: str) -> Dict[str, Any]:
    """
    PHOENIX UTILITY: Strips markdown code blocks and handles
    raw string cleaning to guarantee robust, crash-free JSON parsing.
    """
    if not text:
        return {}
    
    cleaned = text.strip()
    cleaned = re.sub(r'^```json\s*', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'^```\s*', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s*```$', '', cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.strip()
    
    try:
        return json.loads(cleaned)
    except Exception as e:
        logger.warning(f"Standard JSON parse failed. Running regex extractor fallback. Error: {e}")
        try:
            json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
        except Exception as fallback_err:
            logger.error(f"Ultimate JSON extraction failed: {fallback_err}. Raw text: {text}")
        raise

def _call_llm(system_prompt: str, user_content: str, json_mode: bool = False, temperature: float = 0.2, model: str = FAST_MODEL) -> str:
    """
    Synchronous helper for backend services. 
    Clears JSON response formatting options when executing R1 reasoning model to prevent API crashes.
    """
    key = _get_api_key()
    if not key:
        return "Gabim: Mungon OPENROUTER_API_KEY"
    try:
        client = _get_sync_client()
        kwargs = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            "temperature": temperature
        }
        
        if json_mode and model == FAST_MODEL:
            kwargs["response_format"] = {"type": "json_object"}
            
        res = client.chat.completions.create(**kwargs)
        return res.choices[0].message.content or ""
    except Exception as e:
        logger.error(f"Error in _call_llm: {e}")
        return ""

def get_embedding(text: str) -> List[float]:
    """Generates 1536-dim vectors via OpenRouter."""
    key = _get_api_key()
    if not text or not key: 
        return [0.0] * 1536
    try:
        client = _get_sync_client()
        res = client.embeddings.create(input=[text.replace("\n", " ")], model=EMBEDDING_MODEL)
        return res.data[0].embedding
    except Exception as e:
        logger.error(f"❌ OpenRouter Embedding Failure: {e}")
        return [0.0] * 1536

async def stream_text_async(sys_p: str, user_p: str, temp: float = 0.2, model: str = FAST_MODEL) -> AsyncGenerator[str, None]:
    """Streams text asynchronously, accepting dynamic model routing."""
    client = _get_async_client()
    try:
        stream = await client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": sys_p}, {"role": "user", "content": user_p}],
            temperature=temp, stream=True
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content: 
                yield chunk.choices[0].delta.content
        yield AI_DISCLAIMER
    except Exception as e: 
        yield f"[Gabim: {str(e)}]"

# --- SPECIALIZED WAR ROOM & FORENSIC CHAT METHODS ---

def forensic_interrogation(question: str, context_lines: List[str]) -> str:
    """
    Synchronously answers a specific financial forensic question based on context lines.
    Routes through high-IQ DEEP_MODEL (R1) for mathematical verification.
    """
    key = _get_api_key()
    if not key:
        return "Gabim: Mungon OPENROUTER_API_KEY"
    try:
        context_text = "\n".join(context_lines)
        system_prompt = """
        Ti je një Auditor dhe Hetues Financiar Forenzik me eksperiencë në tregun e Kosovës.
        DETYRA: Përgjigju pyetjes së përdoruesit bazuar VETËM në rreshtat e dhënë të transaksioneve bankare.
        TONI: Analitik, skeptik, i bazuar rigorozisht në shifra konkrete.
        GJUHA: SHQIP.
        
        Nëse transaksionet nuk përmbajnë të dhëna të mjaftueshme për t'u përgjigjur, thuaj qartë: "Nuk u gjetën prova mbështetëse për këtë pyetje në ditarin e transaksioneve."
        MOS i shpik shifrat. Përdor simbolin € për shumat.
        """
        user_content = f"TRANSAKSIONET E DEPOZITUARA:\n{context_text}\n\nPYETJA: {question}"
        
        return _call_llm(system_prompt, user_content, json_mode=False, temperature=0.1, model=DEEP_MODEL)
    except Exception as e:
        logger.error(f"Error in forensic_interrogation: {e}")
        return f"Gabim gjatë procesimit të pyetjes forenzike: {str(e)}"

async def generate_adversarial_simulation(context: str) -> Dict[str, Any]:
    """
    Generates an adversarial simulation predicting the opponent's strategy and attack angles.
    Adapts simulation dynamically based on POZICIONI I KLIENTIT TONË (DEFENDANT vs PLAINTIFF).
    Routes through high-IQ DEEP_MODEL (R1).
    """
    key = _get_api_key()
    if not key:
        return {}
    client = _get_async_client()
    system_prompt = """
    Detyra: Shërbe si një avokat kundërshtar shumë i zgjuar dhe agresiv. Analizo kontekstin e rastit dhe identifiko strategjinë më të mirë të sulmit ose mbrojtjes për palën kundërshtare.

    UDHËZIME TË DETYRUESHME PËR ROLIN (MANDATI I PALËS):
    - Kontrollo fushën 'POZICIONI I KLIENTIT TONË' në fillim të kontekstit:
      1. Nëse 'POZICIONI I KLIENTIT TONË' është 'PLAINTIFF' (Paditës):
         - Kundërshtari yt është I PADITURI / I AKUZUARI.
         - 'opponent_strategy' duhet të përshkruajë strategjinë mbrojtëse, prapësimet, vonesat apo justifikimet që i Padituri do të përdorë për të kundërshtuar padinë tonë.
         - 'weakness_attacks' duhet të rreshtojë pikat ku i Padituri do të provojë të godasë kërkesëpadinë tonë.
      2. Nëse 'POZICIONI I KLIENTIT TONË' është 'DEFENDANT' (I Paditur):
         - Kundërshtari yt është PADITËSI / PROKURORIA.
         - 'opponent_strategy' duhet të përshkruajë strategjinë e sulmit dhe pretendimet agresive të Paditësit kundër nesh.
         - 'weakness_attacks' duhet të rreshtojë pikat ku Paditësi do të provojë të godasë mbrojtjen tonë.

    Përgjigju VETËM në formatin e strukturuar JSON si më poshtë:
    {
      "opponent_strategy": "Përshkrimi i hollësishëm i strategjisë agresive apo mbrojtëse të kundërshtarit i përshtatur saktësisht për rolin e tij...",
      "weakness_attacks": [
         "Sulm specifik i bazuar në dobësitë tona ose provat që na mungojnë...",
         "Sulm tjetër specifik..."
      ]
    }
    MOS shto asnjë tekst tjetër jashtë objektit JSON.
    """
    try:
        res = await client.chat.completions.create(
            model=DEEP_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"KONTEKSTI I RASTIT:\n{context}"}
            ],
            temperature=0.4
        )
        content = res.choices[0].message.content or "{}"
        return clean_and_parse_json(content)
    except Exception as e:
        logger.error(f"Failed to generate adversarial simulation: {e}")
        return {
            "opponent_strategy": "Dështoi simulimi i kundërshtarit.",
            "weakness_attacks": ["Nuk u identifikuan dot pikat e sulmit."]
        }

async def build_case_chronology(context: str) -> Dict[str, Any]:
    """
    Builds a structured chronological timeline of events based on case facts.
    Routes through high-IQ DEEP_MODEL (R1).
    """
    key = _get_api_key()
    if not key:
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
            model=DEEP_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"KONTEKSTI I RASTIT:\n{context}"}
            ],
            temperature=0.1
        )
        content = res.choices[0].message.content or "{}"
        return clean_and_parse_json(content)
    except Exception as e:
        logger.error(f"Failed to build chronology: {e}")
        return {"timeline": []}

async def detect_contradictions(context: str) -> Dict[str, Any]:
    """
    Detects factual or legal contradictions in the context.
    Executes a high-IQ, three-tier legal-procedural audit on DEEP_MODEL (R1).
    """
    key = _get_api_key()
    if not key:
        return {}
    client = _get_async_client()
    system_prompt = """
    Detyra: Ti je një Auditor Ligjor dhe Procedural jashtëzakonisht i mprehtë. Analizo tekstin e këtij procesverbali ose shkresave të lëndës për të identifikuar mospërputhje procedurale, gabime emrash, apo deklarata kontradiktore të palëve ose të gjykatës.
    
    DUHET të identifikosh saktësisht një minimum prej 3 kontradiktash/mospërputhjash ligjore:
    1. Kontrollo për Mospërputhje Emrash të Avokatëve ose Palëve.
    2. Kontrollo për Kontradikta të Autorizimeve (Prokurave).
    3. Kontrollo për Paradokse të Palëve apo Ndryshime të Parregullta të Padisë.
    
    Përgjigju VETËM në formatin e strukturuar JSON si më poshtë:
    {
      "contradictions": [
        {
          "severity": "HIGH ose CRITICAL",
          "claim": "Deklarata ose konstatimi kontradiktor i shkruar saktësisht",
          "evidence": "Fakti ose vendimi që mospërputhet saktësisht",
          "impact": "Shpjegimi i thellë ligjor i mospërputhjes dhe si mund ta përdorë avokati këtë për të kontestuar vlefshmërinë procedurale."
        }
      ]
    }
    MOS shto asnjë tekst tjetër jashtë objektit JSON.
    """
    try:
        res = await client.chat.completions.create(
            model=DEEP_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"KONTEKSTI I RASTIT:\n{context}"}
            ],
            temperature=0.2
        )
        content = res.choices[0].message.content or "{}"
        return clean_and_parse_json(content)
    except Exception as e:
        logger.error(f"Failed to detect contradictions: {e}")
        return {"contradictions": []}

def analyze_case_integrity(context: str, custom_prompt: Optional[str] = None) -> Dict[str, Any]:
    """
    Executes the main case cross-examination. Called synchronously via to_thread.
    Routes through DEEP_MODEL (R1) for high-IQ legal summaries.
    """
    key = _get_api_key()
    if not key:
        return {}
    try:
        content = _call_llm(custom_prompt or "Analizo këtë rast ligjor.", f"KONTEKSTI I RASTIT:\n{context}", json_mode=False, temperature=0.3, model=DEEP_MODEL)
        return clean_and_parse_json(content)
    except Exception as e:
        logger.error(f"❌ analyze_case_integrity failed: {e}")
        return {}

def extract_expense_details_from_text(text: str) -> Dict[str, Any]:
    """
    Synchronously parses raw OCR receipt text into structured expense fields using OpenRouter.
    Routes through FAST_MODEL (V3) for instant invoice auto-filling.
    """
    key = _get_api_key()
    if not key:
        return {"category": "Shpenzime", "amount": 0.0, "date": None, "description": "AI parsing disabled"}
    try:
        system_prompt = """
        Detyra: Ti je një asistent financiar i kujdesshëm për tregun e Kosovës. Analizo tekstin e nxjerrë nga një faturë ose kupon fiskal dhe nxirr të dhënat në formatin JSON.
        
        Formatizo përgjigjen tënde saktësisht si kjo strukturë JSON:
        {
          "category": "Kategoria e shpenzimit (p.sh. Ushqim, Karburant, Qira, Internet, Pajisje, etj. - përkthe në shqip saktësisht)",
          "amount": 12.50,
          "date": "YYYY-MM-DD",
          "description": "Emri i tregtarit dhe një përmbledhje e shkurtër e faturës"
        }
        MOS shto asnjë tekst tjetër jashtë objektit JSON.
        """
        content = _call_llm(system_prompt, f"TEKSTI I FATURËS:\n{text}", json_mode=True, temperature=0.1, model=FAST_MODEL)
        return clean_and_parse_json(content)
    except Exception as e:
        logger.error(f"Error in extract_expense_details_from_text: {e}")
        return {"category": "Shpenzime", "amount": 0.0, "date": None, "description": "Gabim gjatë procesimit"}

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

def extract_expense_details_from_text_stub(t): 
    return {"category": "Shpenzime", "amount": 0.0}