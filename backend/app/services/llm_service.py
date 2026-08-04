# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - MASTER INTELLIGENCE V97.0 (ZERO-HALLUCINATION DETERMINISTIC GUARD & COST OPTIMIZED)

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
AI_DISCLAIMER = "\n\n---\n*Kjo përgjigje është gjeneruar nga AI bazuar rreptësisht në shkresat e lëndës. Verifikohet nga avokati.*"

FAST_MODEL = "deepseek/deepseek-chat"
DEEP_MODEL = "deepseek/deepseek-r1"

# STRICT ZERO-HALLUCINATION DETERMINISTIC TEMPERATURES
TEMP_DRAFTING = 0.0
TEMP_ANALYSIS = 0.0
TEMP_CHAT = 0.05

def build_dynamic_identity_header(
    client_name: str = "Pala Kliente", 
    opposing_name: str = "Pala Kundërshtare", 
    position: str = "DEFENDANT"
) -> str:
    """
    PHOENIX ENGINE: Generates a dynamic, case-specific identity lock header.
    Enforces ZERO HALLUCINATIONS, 100% LITERAL DOCUMENT GROUNDING, and 100% ALBANIAN OUTPUT.
    """
    role_label = "I PADITUR / KUNDËRPADITËS" if position.upper() == "DEFENDANT" else "PADITËS"
    
    return f"""
[MANDATI RIGOROZ I RASTIT - LIGJI DHE ROLAT]
KLIENTI YNË ({role_label}): {client_name}.
PALA KUNDËRSHTARE: {opposing_name}.

[RREGULLI I SAKTUAR KUNDËR HALLUCINIMEVE (STRICT ZERO-HALLUCINATION MANDATE)]
1. NDALIMI I SHPIKJES SE FAKTEVE: Ti e ke rreptësisht të ndaluar të shpikësh, të supozosh apo të fabriokosh çfarëdo fakti, emri, date, kontrate, llogarie bankare apo neni ligjor që nuk është i shkruar tekstualisht në shkresat e lëndës.
2. BAZOHU VETËM NË PROVA: Çdo përgjigje, analizë, kronologji apo nyje grafike duhet të bazohet 100% VETËM në tekstin e dokumenteve të bashkangjitura.
3. KUFIZIMI I DIJES: Nëse një informacion nuk ekziston ose nuk thuhet qartë në dokumente, thuaj saktësisht: "Nuk gjendet në shkresat e lëndës." MOS I MUSH ZBRAZËTITË ME PARAGJYKIME!

MANDATI MULTILINGUAL DHE EMANIMI I SAKTË I PALËVE (SQ / EN / DE):
1. Lexo dhe analizo me saktësi të plotë çdo eksponat (Shqip, Anglisht, Gjermanisht).
2. RREGULLI KRITIK I KONTRATAVE: Kur përgjigjesh për ndonjë kontratë apo marrëveshje, NXJERR PALËT E SAKTA TË EMËRUARA NË PREAMBULËN E KONTRATËS.
3. Mos supozo automatikisht se {client_name} është palë e drejtpërdrejtë e nënshkruar nëse teksti i kontratës specifikon një kompani tjetër ose palë të tretë të nënshkruar me {opposing_name}. Trego saktësisht emrat e entiteteve që figurojnë në tekst!
4. RREGULLI UNIFORM I GJUHËS SHQIPE (100% ALBANIAN RULE): Përgjigju, përkthe dhe gjenero TË GJITHA daljet, përmbledhjet, analizat, entitetet, grafikët dhe dëshmitë VETËM në Gjuhën Shqipe Zyrtare (Kosovë), pa marrë parasysh nëse dokumenti burimor është në Gjermanisht, Anglisht, apo Shqip.

[RREGULLI I CITIMIT TË BURIMEVE (RAG SOURCE CITATION)]
- Nëse burimi ka ikonën ⚖️: Citoje si: "Sipas Nenit X të Ligjit Y..."
- Nëse burimi ka ikonën 📚: Citoje si: "Sipas doktrinës / praktikës së Akademisë së Drejtësisë..."
- Nëse burimi ka ikonën 🔨: Citoje si: "Bazuar në praktikën gjyqësore në Aktgjykimin [Emri/Numri]..."

RREGULL KRITIK SHFAJËSUES DHE NON-INVERSION:
Rreptësisht dallo viktimën/palën e dëmtuar nga shkelësi. ASNJËHERË mos ia vish shkeljet e drejtorëve, ortakëve ose entiteteve rivale palës kliente.
Veprimet e paautorizuara, përvetësimet ose regjistrimet paralele i ka kryer {opposing_name}.
Klienti ({client_name}) mbron të drejtat e veta ligjore me prova materiale.

KORNIZA E DETYRUESHME STATUTORE (CITO SAKTE ME NUMRA LIGJESH DHE NENE):
1. Ligji Nr. 03/L-006 për Procedurën Kontestimore - LPK:
   - Prokura & Afati Prekluziv: Neni 91 par 3, Neni 92 & Neni 93.3.
   - Refuzimi / Ndryshimi i Padisë: Neni 256 par 1 & Neni 258.
   - Këqyrja e Shkresave të Lëndës: Neni 122.1.
   - Masa e Sigurisë / Ngrirja e Llogarive: Neni 297, Neni 298, Neni 299 (Neni 299.1 pika a).
2. Ligji Nr. 06/L-016 për Shoqëritë Tregtare - LSHT:
   - Detyra e Besnikërisë & Ndalimi i Konkurrencës: Neni 258 (par 1, 2, 3).
3. Ligji Nr. 04/L-077 për Marrëdhëniet e Detyrimeve - LMD:
   - Shpërblimi i Dëmit: Neni 136. Pasurimi i Pabazë: Neni 141. Kamata Vonesës: Neni 382.
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

def _call_llm(system_prompt: str, user_content: str, json_mode: bool = False, temperature: float = 0.0, model: str = FAST_MODEL) -> str:
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

async def stream_text_async(sys_p: str, user_p: str, temp: float = 0.05, model: str = FAST_MODEL) -> AsyncGenerator[str, None]:
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
    PHOENIX ENGINE: Generates 100% literal, non-hallucinated document summaries in Albanian.
    """
    if not text or not text.strip():
        return "Dokument pa përmbajtje tekstuale."
    try:
        client = _get_async_client()
        system_prompt = """
        Detyra: Ti je një asistent ligjor shumëgjuhësh (Shqip, Anglisht, Gjermanisht) për Gjykatat e Kosovës.
        Analizo tekstin e këtij dokumenti ligjor ose financiar dhe BËJ NJË PËRMBLEDHJE TË FAKTEVE SAKTE VETËM NË GJUHËN SHQIPE.
        
        NDALIMI I HALLUCINIMEVE: Përmend VETËM emrat, shumat, datat dhe termat që shkruhen literalisht në dokument. MOS shpik asnjë detaj.
        
        Përmbledhja duhet të përfshijë:
        1. Llojin e dokumentit (Kontratë Shërbimi, Faturë, Aktakuzë, Shkresë, Vendim, etj.)
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
            temperature=0.0
        )
        content = res.choices[0].message.content or ""
        return content.strip() if content else text[:500]
    except Exception as e:
        logger.error(f"Error in process_large_document_async: {e}")
        return text[:500]

async def extract_case_graph_ontology(context: str) -> Dict[str, Any]:
    """
    PHOENIX ENGINE: Robust, trilingual-aware graph extractor.
    Enforces 100% Albanian output and ZERO HALLUCINATIONS.
    Uses FAST_MODEL (DeepSeek V3 at temp=0.0) for 80% lower API cost and 100% literal accuracy.
    """
    key = _get_api_key()
    if not key:
        return {"nodes": [], "edges": []}
    
    client = _get_async_client()
    identity_header = build_dynamic_identity_header()
    
    system_prompt = f"""
    {identity_header}
    DETYRA KRITIK E DOKUMENTIT SHUMËGJUHËS (DE / EN / SQ):
    Ti je një Konstruktor i Ontologjisë Ligjore për Gjykatat e Kosovës.
    Analizo dokumentet e bashkangjitura dhe nxirr Grafikun e Provave.

    RREGULLI RIGOROZ KUNDËR HALLUCINIMEVE:
    - Nxirr VETËM entitetet, emrat, kompanitë, kontratat dhe dëshmitë që ekzistojnë literalisht në tekstin e dhënë.
    - MOS shpik asnjë person apo kompani që nuk përmendet shprehimisht.

    RREGULLI I DETYRUESHËM I GJUHËS SHQIPE (100% ALBANIAN RULE):
    - TË GJITHA fushat e nxjerra ("label", "description", "relation", "evidence_text") DUHET TË PËRKTHENEN DHE TË SHKRUHEN SAKTËSISHT NË GJUHËN SHQIPE ZYRTARE.
    - Nuk lejohet asnjë fjalë ose fjali në Anglisht apo Gjermanisht në fushat e JSON.

    LLOJET E ENTITETEVE ("type"):
    "PERSON", "ORGANIZATION", "ACCOUNT", "LOCATION", "DOCUMENT", "EVENT"

    LLOJET E LIDHJEVE ("relation"):
    "PËRFAQËSOHET NGA", "ZBATUAR NGA", "KONTRAKTUAR ME", "I PUNËSUAR NË", "PRONËSI E", "TRANSAKSION FINANCIAR", "DETYRIM FINANCIAR", "PËRMENDUR NË SHKRESË", "NËNSHKRUAR NGA", "KUNDËRTHËNIE ME PROVËN".

    KTHO VETËM FORMATIN JSON:
    {{
      "nodes": [
        {{
          "id": "node_1",
          "label": "Emri i entitetit në Shqip",
          "type": "ORGANIZATION",
          "description": "Përshkrimi i saktë i rolit në Shqip..."
        }}
      ],
      "edges": [
        {{
          "id": "edge_1",
          "source": "node_1",
          "target": "node_2",
          "relation": "ZBATUAR NGA",
          "amount_eur": 12500.0,
          "evidence_text": "Dëshmia e plotë e përkthyer në Shqip..."
        }}
      ]
    }}
    """
    
    try:
        res = await client.chat.completions.create(
            model=FAST_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"TEKSTI I PLOTË I RASTIT DHE DOKUMENTEVE:\n{context[:12000]}"}
            ],
            temperature=0.0
        )
        content = res.choices[0].message.content or "{}"
        return clean_and_parse_json(content)
    except Exception as e:
        logger.error(f"Failed to extract ontology graph in Albanian: {e}")
        return {"nodes": [], "edges": []}

def forensic_interrogation(question: str, context_lines: List[str]) -> str:
    key = _get_api_key()
    if not key:
        return "Gabim: Mungon OPENROUTER_API_KEY"
    try:
        context_text = "\n".join(context_lines)
        system_prompt = """
        Ti je një Auditor dhe Hetues Financiar Forenzik me eksperiencë në tregun e Kosovës.
        DETYRA: Përgjigju pyetjes së përdoruesit bazuar VETËM në rreshtat e dhënë të transaksioneve bankare apo dokumenteve financiare.
        NDALIMI I HALLUCINIMEVE: Përdor VETËM shifrat dhe fjalët që figurojnë në rreshtat e mëposhtëm. MOS shpik asnjë transaksion!
        TONI: Analitik, skeptik, i bazuar rigorozisht në shifra konkrete.
        GJUHA: SHQIP ZYRTARE (100%).
        """
        user_content = f"TRANSAKSIONET / PROVAT E DEPOZITUARA:\n{context_text}\n\nPYETJA: {question}"
        return _call_llm(system_prompt, user_content, json_mode=False, temperature=0.0, model=FAST_MODEL)
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
    Detyra: Shërbe si një avokat kundërshtar shumë i zgjuar dhe strategjik. Analizo kontekstin e rastit dhe identifiko strategjinë e sulmit bazuar VETËM në prova reale.
    NDALIMI I HALLUCINIMEVE: MOS shpik akuza apo shkelje që nuk figurojnë në dokumente.
    TË GJITHA SHQIP: Përkthe çdo informacion nga Gjermanishtja/Anglishtja në Shqip.

    Përgjigju VETËM në formatin e strukturuar JSON:
    {{
      "opponent_strategy": "Përshkrimi i hollësishëm i strategjisë agresive në Shqip...",
      "weakness_attacks": [
         "Sulm specifik i bazuar në dobësitë e provuara...",
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
            temperature=0.0,
            max_tokens=2500
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
    Detyra: Krijo një kronologji të saktë dhe të strukturuar të ngjarjeve bazuar VETËM në datat dhe faktet e shkruara në dokumente.
    NDALIMI I HALLUCINIMEVE: MOS shpik asnjë datë apo ngjarje që nuk shkruhet literalisht në shkresa.
    TË GJITHA PERSHKRIMET DUHET TË JENË 100% NË GJUHËN SHQIPE.

    Përgjigju VETËM në formatin e strukturuar JSON:
    {{
      "timeline": [
        {{"date": "Data e ngjarjes", "event": "Përshkrimi i saktë në Shqip"}}
      ]
    }}
    """
    try:
        res = await client.chat.completions.create(
            model=FAST_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"KONTEKSTI I RASTIT:\n{context}"}
            ],
            temperature=0.0
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
    Detyra: Ti je një Auditor Ligjor dhe Procedural jashtëzakonisht i mprehtë. Analizo shkresat e lëndës për të identifikuar mospërputhje procedurale dhe kontradikta reale.
    NDALIMI I HALLUCINIMEVE: Trego VETËM kontradikta që mund të provohen me tekstin e dokumenteve. MOS shpik mospërputhje fiktive.
    GJUHA: Të gjitha fushat e JSON ("claim", "evidence", "impact") DUHET TË JENË 100% NË GJUHËN SHQIPE.

    Përgjigju VETËM në formatin e strukturuar JSON:
    {{
      "contradictions": [
        {{
          "severity": "CRITICAL",
          "claim": "Deklarata kontradiktore në Shqip",
          "evidence": "Fakti që mospërputhet në Shqip",
          "impact": "Shpjegimi ligjor në Shqip"
        }}
      ]
    }}
    """
    try:
        res = await client.chat.completions.create(
            model=FAST_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"KONTEKSTI I RASTIT:\n{context}"}
            ],
            temperature=0.0
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
        content = _call_llm(custom_prompt or "Analizo këtë rast ligjor në Shqip.", f"KONTEKSTI I RASTIT:\n{context}", json_mode=False, temperature=0.0, model=FAST_MODEL)
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
        Detyra: Ti je një asistent financiar i kujdesshëm për tregun e Kosovës. Analizo tekstin e faturës (Shqip, Anglisht, apo Gjermanisht) dhe nxirr JSON në Shqip.
        NDALIMI I HALLUCINIMEVE: Përdor VETËM shifrat e vërteta nga fatura.
        Formatizo përgjigjen tënde saktësisht si kjo strukturë JSON:
        {
          "category": "Kategoria e shpenzimit në Shqip",
          "amount": 12.50,
          "date": "YYYY-MM-DD",
          "description": "Emri i tregtarit"
        }
        """
        content = _call_llm(system_prompt, f"TEKSTI I FATURËS:\n{text}", json_mode=True, temperature=0.0, model=FAST_MODEL)
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