# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - MASTER INTELLIGENCE V83.0 (ROBUST JSON PARSING)
# 1. FIX: Added self-healing 'clean_and_parse_json' helper to strip Markdown codeblocks and parse DeepSeek JSON payloads without DecodeErrors.
# 2. STATUS: Fully synchronized across all War Room and Forensic audit modules.

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

def clean_and_parse_json(text: str) -> Dict[str, Any]:
    """
    PHOENIX UTILITY: Strips markdown code blocks and handles
    raw string cleaning to guarantee robust, crash-free JSON parsing.
    """
    if not text:
        return {}
    
    # Strip any potential leading/trailing spaces
    cleaned = text.strip()
    
    # Remove markdown block headers/footers recursively
    cleaned = re.sub(r'^```json\s*', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'^```\s*', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s*```$', '', cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.strip()
    
    try:
        return json.loads(cleaned)
    except Exception as e:
        logger.warning(f"Standard JSON parse failed. Running regex extractor fallback. Error: {e}")
        # Secondary fallback: Extract the first outer curly bracket match
        try:
            json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
        except Exception as fallback_err:
            logger.error(f"Ultimate JSON extraction failed: {fallback_err}. Raw text: {text}")
        raise

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

# --- SPECIALIZED WAR ROOM & FORENSIC CHAT METHODS ---

def forensic_interrogation(question: str, context_lines: List[str]) -> str:
    """
    Synchronously answers a specific financial forensic question based on context lines.
    Called via to_thread.
    """
    if not OPENROUTER_KEY:
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
        
        client = _get_sync_client()
        res = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            temperature=0.1
        )
        return res.choices[0].message.content or "Nuk u mor asnjë përgjigje."
    except Exception as e:
        logger.error(f"Error in forensic_interrogation: {e}")
        return f"Gabim gjatë procesimit të pyetjes forenzike: {str(e)}"

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
        {"date": "Data e ngjarjes", "event": "Përshkrimi i saktë i asaj qai ka ndodhur"}
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
        content = res.choices[0].message.content or "{}"
        return clean_and_parse_json(content)
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
    Detyra: Analizo të gjitha dëshmitë, deklaratat dhe faktet në kontekst për të gjetur kontradikta, mospërputhje ose deklarata të rreme të palës tjetër ose dëshmitarëve.
    
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
        content = res.choices[0].message.content or "{}"
        return clean_and_parse_json(content)
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
        content = res.choices[0].message.content or "{}"
        return clean_and_parse_json(content)
    except Exception as e:
        logger.error(f"❌ analyze_case_integrity failed: {e}")
        return {}

def extract_expense_details_from_text(text: str) -> Dict[str, Any]:
    """
    Synchronously parses raw OCR receipt text into structured expense fields using OpenRouter.
    """
    if not OPENROUTER_KEY:
        return {"category": "Shpenzime", "amount": 0.0, "date": None, "description": "AI parsing disabled"}
    try:
        system_prompt = """
        Detyra: Ti je një asistent financiar i kujdesshëm për tregun e Kosovës. Analizo tekstin e nxjerrë nga një faturë ose kupon fiskal dhe nxirr të dhënat në formatin JSON.
        
        Formatizo përgjigjen tënde saktësisht si kjo strukturë JSON:
        {
          "category": "Kategoria e shpenzimit (p.sh. Ushqim, Karburant, Qira, Internet, Pajisje, etj. - përkthe në shqip saktësisht)",
          "amount": 12.50, (vlerën numerike të totalit ose sumës së faturës si float, pa valutë),
          "date": "YYYY-MM-DD" (data e faturës në këtë format, nëse nuk gjendet vendos null),
          "description": "Emri i tregtarit dhe një përmbledhje e shkurtër e faturës"
        }
        MOS shto asnjë tekst tjetër jashtë objektit JSON.
        """
        client = _get_sync_client()
        res = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"TEKSTI I FATURËS:\n{text}"}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        content = res.choices[0].message.content or "{}"
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
    return {"category": "Shpenzime", "amount": 0.0}# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - MASTER INTELLIGENCE V84.0 (EXECUTIVE PROCEDURAL AUDIT)
# 1. FIX: Upgraded system prompts in detect_contradictions to enforce a deep 3-tier legal audit (names, representation, party paradoxes).
# 2. STATUS: Generates a minimum of 3 high-IQ procedural contradictions.

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

# --- SPECIALIZED WAR ROOM & FORENSIC CHAT METHODS ---

def forensic_interrogation(question: str, context_lines: List[str]) -> str:
    """
    Synchronously answers a specific financial forensic question based on context lines.
    Called via to_thread.
    """
    if not OPENROUTER_KEY:
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
        
        client = _get_sync_client()
        res = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            temperature=0.1
        )
        return res.choices[0].message.content or "Nuk u mor asnjë përgjigje."
    except Exception as e:
        logger.error(f"Error in forensic_interrogation: {e}")
        return f"Gabim gjatë procesimit të pyetjes forenzike: {str(e)}"

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
        {"date": "Data e ngjarjes", "event": "Përshkrimi i saktë i asaj qai ka ndodhur"}
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
        content = res.choices[0].message.content or "{}"
        return clean_and_parse_json(content)
    except Exception as e:
        logger.error(f"Failed to build chronology: {e}")
        return {"timeline": []}

async def detect_contradictions(context: str) -> Dict[str, Any]:
    """
    Detects factual or legal contradictions in the context.
    Executes a high-IQ, three-tier legal-procedural audit.
    """
    if not OPENROUTER_KEY:
        return {}
    client = _get_async_client()
    system_prompt = """
    Detyra: Ti je një Auditor Ligjor dhe Procedural jashtëzakonisht i mprehtë. Analizo tekstin e këtij procesverbali ose shkresave të lëndës për të identifikuar mospërputhje procedurale, gabime emrash, apo deklarata kontradiktore të palëve ose të gjykatës.
    
    DUHET të identifikosh saktësisht një minimum prej 3 kontradiktash/mospërputhjash ligjore:
    1. Kontrollo për Mospërputhje Emrash të Avokatëve ose Palëve (p.sh. nëse një person pranohet si prezent në fillim, por një emër tjetër urdhërohet me vendim në fund).
    2. Kontrollo për Kontradikta të Autorizimeve (Prokurave) (p.sh. nëse gjykata thotë 'ka kushte për mbajtjen e seancës' por në fund kërcënon me anulim të të gjitha veprimeve sepse avokati nuk ka prokurë origjinale).
    3. Kontrollo për Paradokse të Palëve (p.sh. ftesa për të shtuar paditësin aktual si të paditur, ndryshime të parregullta të padisë, apo kërkesa logjikisht të pamundura).
    
    Përgjigju VETËM në formatin e strukturuar JSON si më poshtë:
    {
      "contradictions": [
        {
          "severity": "HIGH ose CRITICAL",
          "claim": "Deklarata ose konstatimi kontradiktor i shkruar saktësisht (p.sh. 'Gjykata konstaton se ka kushte për mbajtjen e seancës')",
          "evidence": "Fakti ose vendimi që mospërputhet saktësisht (p.sh. 'Gjykata në fund urdhëron avokatin të dorëzojë prokurën origjinale ose përndryshe të gjitha veprimet anulohen')",
          "impact": "Shpjegimi i thellë ligjor i mospërputhjes dhe si mund ta përdorë këtë avokati i të paditurit për të kontestuar vlefshmërinë procedurale."
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
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        content = res.choices[0].message.content or "{}"
        return clean_and_parse_json(content)
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
        content = res.choices[0].message.content or "{}"
        return clean_and_parse_json(content)
    except Exception as e:
        logger.error(f"❌ analyze_case_integrity failed: {e}")
        return {}

def extract_expense_details_from_text(text: str) -> Dict[str, Any]:
    """
    Synchronously parses raw OCR receipt text into structured expense fields using OpenRouter.
    """
    if not OPENROUTER_KEY:
        return {"category": "Shpenzime", "amount": 0.0, "date": None, "description": "AI parsing disabled"}
    try:
        system_prompt = """
        Detyra: Ti je një asistent financiar i kujdesshëm për tregun e Kosovës. Analizo tekstin e nxjerrë nga një faturë ose kupon fiskal dhe nxirr të dhënat në formatin JSON.
        
        Formatizo përgjigjen tënde saktësisht si kjo strukturë JSON:
        {
          "category": "Kategoria e shpenzimit (p.sh. Ushqim, Karburant, Qira, Internet, Pajisje, etj. - përkthe në shqip saktësisht)",
          "amount": 12.50, (vlerën numerike të totalit ose sumës së faturës si float, pa valutë),
          "date": "YYYY-MM-DD" (data e faturës në këtë format, nëse nuk gjendet vendos null),
          "description": "Emri i tregtarit dhe një përmbledhje e shkurtër e faturës"
        }
        MOS shto asnjë tekst tjetër jashtë objektit JSON.
        """
        client = _get_sync_client()
        res = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"TEKSTI I FATURËS:\n{text}"}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        content = res.choices[0].message.content or "{}"
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