# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - MASTER INTELLIGENCE V95.0 (DYNAMIC CITATION & PARTY ALIGNMENT)

import os
import json
import logging
import re
import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator
from dotenv import load_dotenv

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

FAST_MODEL = "deepseek/deepseek-chat"
DEEP_MODEL = "deepseek/deepseek-r1"

TEMP_DRAFTING = 0.1
TEMP_ANALYSIS = 0.2
TEMP_CHAT = 0.3

def build_dynamic_identity_header(
    client_name: str = "Pala Kliente", 
    opposing_name: str = "Pala Kundërshtare", 
    position: str = "DEFENDANT"
) -> str:
    """
    PHOENIX ENGINE: Generates a dynamic, case-specific identity lock header.
    Forces literal extraction of contract signatories and STRICT MULTI-SOURCE CITATIONS with 0 hardcoded assumptions.
    """
    role_label = "I PADITUR / KUNDËRPADITËS" if position.upper() == "DEFENDANT" else "PADITËS"
    
    return f"""
[MANDATI RIGOROZ I RASTIT - LIGJI DHE ROLAT]
KLIENTI YNË ({role_label}): {client_name}.
PALA KUNDËRSHTARE: {opposing_name}.

MANDATI MULTILINGUAL DHE EMANIMI I SAKTË I PALËVE (SQ / EN / DE):
1. Lexo dhe analizo me saktësi të plotë çdo eksponat (Shqip, Anglisht, Gjermanisht).
2. RREGULLI KRITIK I KONTRATAVE: Kur përgjigjesh për ndonjë kontratë apo marrëveshje, NXJERR PALËT E SAKTA TË EMËRUARA NË PREAMBULËN E KONTRATËS.
3. Mos supozo automatikisht se {client_name} është palë e drejtpërdrejtë e nënshkruar nëse teksti i kontratës specifikon një kompani tjetër ose palë të tretë të nënshkruar me {opposing_name}. Trego saktësisht emrat e entiteteve që figurojnë në tekst!

[RREGULLI I CITIMIT TË BURIMEVE (RAG SOURCE CITATION)]
Ti do të marrësh fragmente nga Baza e Njohurive. Kushtoji rëndësi ikonave për të kuptuar çfarë lloj dokumenti po lexon dhe citoji saktë:
- Nëse burimi ka ikonën ⚖️: Ky është LIGJ ZYRTAR STATUTOR. Citoje si: "Sipas Nenit X të Ligjit Y..."
- Nëse burimi ka ikonën 📚: Ky është MANUAL / KOMENTAR AKADEMIK. Citoje si: "Sipas doktrinës / praktikës së Akademisë së Drejtësisë..."
- Nëse burimi ka ikonën 🔨: Ky është AKTGJYKIM / PRAKTIKË GJYQËSORE. Citoje si: "Bazuar në praktikën gjyqësore në Aktgjykimin [Emri/Numri]..."

RREGULL KRITIK SHFAJËSUES DHE NON-INVERSION:
Rreptësisht dallo viktimën/palën e dëmtuar nga shkelësi. ASNJËHERË mos ia vish shkeljet e drejtorëve, ortakëve ose entiteteve rivale palës kliente.
Veprimet e paautorizuara, përvetësimet ose regjistrimet paralele i ka kryer {opposing_name}.
Klienti ({client_name}) mbron të drejtat e veta ligjore me prova materiale (raporte, pasqyra bankare, kontrata, fatura dhe ARBK).

KORNIZA E DETYRUESHME STATUTORE (CITO SAKTE ME NUMRA LIGJESH DHE NENE):
1. Ligji Nr. 03/L-006 për Procedurën Kontestimore - LPK:
   - Prokura & Afati Prekluziv: Neni 91 par 3, Neni 92 & Neni 93.3 (JO Neni 99).
   - Refuzimi / Ndryshimi i Padisë: Neni 256 par 1 & Neni 258.
   - Këqyrja e Shkresave të Lëndës: Neni 122.1 (JO Neni 113).
   - Baza Procedurale për Kundërpadi & Prapësim: Neni 256.
   - Masa e Sigurisë / Ngrirja e Llogarive: Neni 297, Neni 298, Neni 299 (Neni 299.1 pika a).
   - Abuzimi i Të Drejtave Procedurale & Gjobat: Nenet 10, 11, 110 & Nenet 288/289.
2. Ligji Nr. 06/L-016 për Shoqëritë Tregtare - LSHT:
   - Detyra e Besnikërisë & Ndalimi i Konkurrencës: Neni 258 (par 1, 2, 3).
3. Ligji Nr. 04/L-077 për Marrëdhëniet e Detyrimeve - LMD:
   - Shpërblimi i Dëmit: Neni 136.
   - Pasurimi i Pabazë: Neni 141.
   - Kamata Vonesës Prej 8% në Viti: Neni 382.

STRICT BAN: MOS CITO ASNJËHERË Ligjin për Mbrojtjen e Të Dhënave Personale (GDPR), Ligjet e Falimentimit, apo Ligjet e Administrimit Tatimor sepse janë tërësisht irrelevante kur nuk janë lëndë e kontestit.
"""

UNBREAKABLE_IDENTITY_HEADER = build_dynamic_identity_header()

def _sanitize_and_disambiguate_prompt(user_text: str, opposing_name: str = "Pala Kundërshtare") -> str:
    if not user_text:
        return ""
    
    cleaned = re.sub(r'\b(ai|aj)\s+vetë?\b', f'Pala Kundërshtare ({opposing_name})', user_text, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(ai|aj)\s+(ka|mori|transferoi|solli|regjistroi|bleu|ka hapur)\b', f'Pala Kundërshtare ({opposing_name}) \\2', cleaned, flags=re.IGNORECASE)
    return cleaned

def _get_sync_client(): 
    key = _get_api_key()
    return OpenAI(api_key=key, base_url=OPENROUTER_URL)

def _get_async_client(): 
    key = _get_api_key()
    return AsyncOpenAI(api_key=key, base_url=OPENROUTER_URL)

def clean_and_parse_json(text: str) -> Dict[str, Any]:
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
    key = _get_api_key()
    if not key:
        return "Gabim: Mungon OPENROUTER_API_KEY"
    try:
        client = _get_sync_client()
        
        identity_header = build_dynamic_identity_header()
        full_sys_prompt = f"{identity_header}\n\n{system_prompt}" if "MANDATI RIGOROZ" not in system_prompt else system_prompt
        sanitized_user_content = _sanitize_and_disambiguate_prompt(user_content)

        kwargs = {
            "model": model,
            "messages": [
                {"role": "system", "content": full_sys_prompt},
                {"role": "user", "content": sanitized_user_content}
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
    client = _get_async_client()
    try:
        identity_header = build_dynamic_identity_header()
        full_sys = f"{identity_header}\n\n{sys_p}" if "MANDATI RIGOROZ" not in sys_p else sys_p
        sanitized_user_p = _sanitize_and_disambiguate_prompt(user_p)

        stream = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": full_sys},
                {"role": "user", "content": sanitized_user_p}
            ],
            temperature=temp, stream=True
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content: 
                yield chunk.choices[0].delta.content
        yield AI_DISCLAIMER
    except Exception as e: 
        yield f"[Gabim: {str(e)}]"

async def process_large_document_async(text: str, task_type: str = "SUMMARY") -> str:
    """
    PHOENIX ENGINE: Generates real, structured summaries for Albanian, English, or German documents.
    """
    if not text or not text.strip():
        return "Dokument pa përmbajtje tekstuale."
    try:
        client = _get_async_client()
        system_prompt = """
        Detyra: Ti je një asistent ligjor shumëgjuhësh (Shqip, Anglisht, Gjermanisht).
        Analizo tekstin e këtij dokumenti ligjor ose financiar dhe përpiqet të bësh një përmbledhje të qartë, të saktë dhe të strukturuar në gjuhën shqipe.
        
        Përmbledhja duhet të përfshijë:
        1. Llojin e dokumentit (Kontratë, Faturë, Vendim, Shkresë, etj.)
        2. Palët e saktësisht të emëruara në nënshkrim dhe datat kryesore.
        3. Shumat monetare, obligimet ose fushëveprimin e marrëveshjes.
        4. Fakti më i rëndësishëm ligjor ose financiar.
        """
        res = await client.chat.completions.create(
            model=FAST_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"TEKSTI I DOKUMENTIT PËR PËRMBLEDHJE:\n{text[:6000]}"}
            ],
            temperature=TEMP_ANALYSIS
        )
        content = res.choices[0].message.content or ""
        return content.strip() if content else text[:500]
    except Exception as e:
        logger.error(f"Error in process_large_document_async: {e}")
        return text[:500]

def forensic_interrogation(question: str, context_lines: List[str]) -> str:
    key = _get_api_key()
    if not key:
        return "Gabim: Mungon OPENROUTER_API_KEY"
    try:
        context_text = "\n".join(context_lines)
        system_prompt = """
        Ti je një Auditor dhe Hetues Financiar Forenzik me eksperiencë në tregun e Kosovës.
        DETYRA: Përgjigju pyetjes së përdoruesit bazuar VETËM në rreshtat e dhënë të transaksioneve bankare apo dokumenteve financiare.
        TONI: Analitik, skeptik, i bazuar rigorozisht në shifra konkrete.
        GJUHA: SHQIP.
        """
        user_content = f"TRANSAKSIONET / PROVAT E DEPOZITUARA:\n{context_text}\n\nPYETJA: {question}"
        return _call_llm(system_prompt, user_content, json_mode=False, temperature=0.1, model=DEEP_MODEL)
    except Exception as e:
        logger.error(f"Error in forensic_interrogation: {e}")
        return f"Gabim gjatë procesimit të pyetjes forenzike: {str(e)}"

async def generate_adversarial_simulation(context: str) -> Dict[str, Any]:
    key = _get_api_key()
    if not key:
        return {}
    client = _get_async_client()
    identity_header = build_dynamic_identity_header()
    system_prompt = f"""
    {identity_header}
    Detyra: Shërbe si një avokat kundërshtar shumë i zgjuar dhe agresiv. Analizo kontekstin e rastit (përfshirë dokumentet në Shqip, Anglisht, Gjermanisht) dhe identifiko strategjinë më të mirë të sulmit ose mbrojtjes për palën kundërshtare.

    Përgjigju VETËM në formatin e strukturuar JSON:
    {{
      "opponent_strategy": "Përshkrimi i hollësishëm i strategjisë agresive...",
      "weakness_attacks": [
         "Sulm specifik i bazuar në dobësitë...",
         "Sulm tjetër..."
      ]
    }}
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
    key = _get_api_key()
    if not key:
        return {}
    client = _get_async_client()
    identity_header = build_dynamic_identity_header()
    system_prompt = f"""
    {identity_header}
    Detyra: Krijo një kronologji të saktë dhe të strukturuar të ngjarjeve bazuar në faktet e rastit dhe të gjitha dokumentet e bashkangjitura (Shqip/Anglisht/Gjermanisht).
    Përgjigju VETËM në formatin e strukturuar JSON:
    {{
      "timeline": [
        {{"date": "Data e ngjarjes", "event": "Përshkrimi i saktë"}}
      ]
    }}
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
    key = _get_api_key()
    if not key:
        return {}
    client = _get_async_client()
    identity_header = build_dynamic_identity_header()
    system_prompt = f"""
    {identity_header}
    Detyra: Ti je një Auditor Ligjor dhe Procedural jashtëzakonisht i mprehtë. Analizo shkresat e lëndës për të identifikuar mospërputhje procedurale dhe kontradikta midis deklaratave dhe dokumenteve (Shqip/Anglisht/Gjermanisht).
    Përgjigju VETËM në formatin e strukturuar JSON:
    {{
      "contradictions": [
        {{
          "severity": "CRITICAL",
          "claim": "Deklarata kontradiktore",
          "evidence": "Fakti që mospërputhet",
          "impact": "Shpjegimi ligjor"
        }}
      ]
    }}
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
    key = _get_api_key()
    if not key:
        return {"category": "Shpenzime", "amount": 0.0, "date": None, "description": "AI parsing disabled"}
    try:
        system_prompt = """
        Detyra: Ti je një asistent financiar i kujdesshëm për tregun e Kosovës. Analizo tekstin e faturës (Shqip, Anglisht, apo Gjermanisht) dhe nxirr JSON.
        Formatizo përgjigjen tënde saktësisht si kjo strukturë JSON:
        {
          "category": "Kategoria e shpenzimit",
          "amount": 12.50,
          "date": "YYYY-MM-DD",
          "description": "Emri i tregtarit"
        }
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
    return text.strip() if text else ""

def translate_for_client(t): 
    return t

def extract_deadlines(text): 
    return {"deadlines": []}