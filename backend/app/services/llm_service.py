# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - CORE INTELLIGENCE V48.0 (KOSOVO JURISDICTION ENHANCED)
# 1. FIX: Injected "Senior Partner Prishtina" Persona for professional output.
# 2. UPDATE: Refined 'analyze_case_integrity' to strictly follow Kosovo Legal terminology.
# 3. CONTEXT: Enforced specific citation formats (Ligji Nr. X/L-Y).

import os
import json
import logging
import httpx
import re
import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime, timezone
from openai import OpenAI, AsyncOpenAI

from .text_sterilization_service import sterilize_text_for_llm

logger = logging.getLogger(__name__)

# --- EXPORT LIST (VERIFIED: 18 FUNCTIONS) ---
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

# --- CLIENT FACTORIES ---
def get_async_deepseek_client() -> Optional[AsyncOpenAI]:
    if DEEPSEEK_API_KEY: return AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url=OPENROUTER_BASE_URL)
    return None

def get_deepseek_client() -> Optional[OpenAI]:
    if DEEPSEEK_API_KEY: return OpenAI(api_key=DEEPSEEK_API_KEY, base_url=OPENROUTER_BASE_URL)
    return None

def get_openai_client() -> Optional[OpenAI]:
    if OPENAI_API_KEY: return OpenAI(api_key=OPENAI_API_KEY)
    return None

# --- CORE UTILITIES ---
def _parse_json_safely(content: Optional[str]) -> Dict[str, Any]:
    if not content: return {}
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # Attempt to extract JSON from Markdown code blocks
        match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
        if match:
            try: return json.loads(match.group(1))
            except: pass
        # Attempt to find the first '{' and last '}'
        start, end = content.find('{'), content.rfind('}')
        if start != -1 and end != -1:
            try: return json.loads(content[start:end+1])
            except: pass
        return {"raw_response": content, "error": "JSON_PARSE_FAILED"}

def _call_llm(system_prompt: str, user_prompt: str, json_mode: bool = False, temp: float = 0.1) -> Optional[str]:
    client = get_deepseek_client()
    if not client: return None
    try:
        kwargs = {
            "model": OPENROUTER_MODEL, 
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            "temperature": temp
        }
        if json_mode: kwargs["response_format"] = {"type": "json_object"}
        res = client.chat.completions.create(**kwargs)
        return res.choices[0].message.content
    except Exception as e:
        logger.error(f"LLM Call Failed: {e}")
        return None

# --- KOSOVO JURISDICTION PERSONA ---
KOSOVO_LEGAL_PERSONA = """
ROLI: Ti je Avokat Kryesor (Senior Partner) në një studio ligjore prestigjioze në Prishtinë, Kosovë.
DETYRA: Analizo materialet ligjore me saktësi maksimale, gjuhë standarde shqipe dhe profesionalizëm të lartë.

RREGULLAT STRIKTE:
1. GJUHA: Përdor vetëm gjuhën letrare shqipe (Standarde). Shmang dialektet ose termat e pasaktë (psh. mos thuaj "Avokata" por "Avokati/ja").
2. REFERENCAT: Cito ligjet sipas formatit zyrtar të Gazetës Zyrtare të Republikës së Kosovës (psh. "Neni 23 i Ligjit për Procedurën Kontestimore").
3. KONTEKSTI: Përdor VETËM faktet dhe ligjet e ofruara në input. Nëse mungon informacioni, thuaj "Nuk ka informacion të mjaftueshëm".
4. FORMATI: Përgjigju gjithmonë në strukturë profesionale ligjore (Hyrje, Analizë Faktike, Baza Ligjore, Përfundim).
"""

# --- 18 EXPORTED FUNCTIONS ---

def analyze_case_integrity(context: str) -> Dict[str, Any]:
    """
    Primary function for 'Analyse Case'. 
    Accepts combined Context (Case Facts + Global Knowledge Base Laws).
    """
    system_prompt = f"""{KOSOVO_LEGAL_PERSONA}
    
    OBJEKTIVI: Analizo integritetin e kësaj lënde ligjore duke përdorur "Case Knowledge Base" (Faktet) dhe "Global Knowledge Base" (Ligjet e gjetura).
    
    TI DUHET TË PRODHOSH NJË RAPORT JSON ME KËTË STRUKTURË:
    {{
        "summary": "Përmbledhje ekzekutive profesionale e rastit (max 100 fjalë).",
        "key_issues": ["Çështja 1 (Faktike)", "Çështja 2 (Procedurale)"],
        "legal_basis": [
            {{ "law": "Emri i Ligjit (nga Global KB)", "article": "Neni specifik", "relevance": "Si lidhet me faktet?" }}
        ],
        "strategic_analysis": "Analizë e thellë juridike. Si ndërveprojnë faktet me ligjet e Kosovës?",
        "weaknesses": ["Dobësi 1", "Dobësi 2"],
        "action_plan": ["Hapi 1: ...", "Hapi 2: ..."],
        "success_probability": "XX%",
        "risk_level": "LOW|MEDIUM|HIGH"
    }}
    """
    # We increase context window limit for deep analysis
    return _parse_json_safely(_call_llm(system_prompt, context[:50000], True, temp=0.2))

def extract_graph_data(text: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_PERSONA}
    DETYRA: Shndërro tekstin në Hartë Logjike për sistemin neo4j.
    ENTITETET: Pretendim (Claim), Fakt (Fact), Provë (Evidence), Ligj (Law).
    
    JSON FORMAT: 
    {{
        "nodes": [{{"id": "short_id", "name": "...", "type": "Claim|Fact|Evidence|Law"}}], 
        "edges": [{{"source": "id1", "relation": "mbështetet_nga|kundërshton|bazohet_në", "target": "id2"}}]
    }}"""
    return _parse_json_safely(_call_llm(system_prompt, text[:30000], True))

def generate_adversarial_simulation(context: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_PERSONA} 
    ROLI: Ti je Avokati i Palës Kundërshtare (Devil's Advocate).
    QËLLIMI: Gjej çdo varësi procedurale ose materiale në këtë rast për ta rrëzuar atë në Gjykatë.
    
    JSON FORMAT: 
    {{ 
        'opponent_strategy': 'Strategjia kryesore e mbrojtjes/sulmit', 
        'weakness_attacks': ['Sulm ndaj provës X', 'Parashkrimi i kërkesës Y'], 
        'counter_claims': ['Kundërpadi e mundshme Z'] 
    }}"""
    return _parse_json_safely(_call_llm(system_prompt, context[:30000], True, temp=0.3))

def analyze_financial_portfolio(data: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_PERSONA}
    ROLI: Ekspert Financiar Gjyqësor.
    DETYRA: Analizo transaksionet për pastrim parash, evazion fiskal ose parregullsi sipas ligjeve të Kosovës (ATK).
    JSON: {{'executive_summary': '...', 'anomalies': [], 'recommendations': []}}"""
    return _parse_json_safely(_call_llm(system_prompt, data, True))

def build_case_chronology(text: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_PERSONA} 
    DETYRA: Krijo një kronologji faktike të detajuar.
    JSON: {{'timeline': [{{'date': 'YYYY-MM-DD', 'event': 'Ngjarja...', 'source': 'Dokumenti Referues'}}]}}"""
    return _parse_json_safely(_call_llm(system_prompt, text[:40000], True))

def translate_for_client(legal_text: str) -> str:
    system_prompt = f"""{KOSOVO_LEGAL_PERSONA} 
    DETYRA: Shpjego këtë tekst juridik për klientin në gjuhë të thjeshtë, por profesionale. 
    Ruaj kuptimin juridik por hiq termat latinë të panevojshëm.
    """
    return _call_llm(system_prompt, legal_text) or "Gabim në thjeshtësim."

def detect_contradictions(text: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_PERSONA} 
    DETYRA: Identifiko kundërthëniet (Kontradiktat) mes dëshmive ose dokumenteve.
    JSON: {{'contradictions': [{{'claim': 'Pretendimi A', 'evidence': 'Prova B që e rrëzon', 'severity': 'HIGH|LOW', 'impact': '...'}}]}}"""
    return _parse_json_safely(_call_llm(system_prompt, text[:30000], True))

def extract_deadlines(text: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_PERSONA} 
    DETYRA: Identifiko afatet procedurale (Prekluzive). 
    Baza: Ligji për Procedurën Kontestimore (LPK).
    JSON: {{'is_judgment': bool, 'deadline_date': 'YYYY-MM-DD', 'action_required': 'Ankesë/Prapësim/Përgjigje në Padi'}}"""
    return _parse_json_safely(_call_llm(system_prompt, text[:15000], True))

def perform_litigation_cross_examination(target_text: str, context_summaries: List[str]) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_PERSONA} 
    DETYRA: Kryqëzo faktet e këtij dokumenti të ri (TARGET) me njohuritë ekzistuese (CONTEXT).
    A ka mospërputhje? A ka konfirmim të fakteve?
    JSON: {{'consistency_check': 'Analizë narrative...', 'contradictions': ['...'], 'corroborations': ['...']}}"""
    
    user_prompt = f"TARGET DOCUMENT: {target_text[:15000]}\nEXISTING KNOWLEDGE: {' '.join(context_summaries)}"
    return _parse_json_safely(_call_llm(system_prompt, user_prompt, True))

def generate_summary(text: str) -> str:
    system_prompt = f"{KOSOVO_LEGAL_PERSONA} Përmblidh këtë dokument shkurt (max 1 paragraf) duke evidentuar rëndësinë juridike."
    return _call_llm(system_prompt, text[:20000]) or ""

def get_embedding(text: str) -> List[float]:
    client = get_openai_client()
    if client:
        try: return client.embeddings.create(input=[text.replace("\n", " ")], model=EMBEDDING_MODEL).data[0].embedding
        except: pass
    return [0.0] * 1536 

def forensic_interrogation(question: str, context_rows: List[str]) -> str:
    prompt = f"""{KOSOVO_LEGAL_PERSONA}
    DETYRA: Përgjigju pyetjes duke u bazuar VETËM në provat e mëposhtme.
    PROVAT: {' '.join(context_rows)}
    PYETJA: {question}"""
    return _call_llm(prompt, question) or "Nuk u gjet informacion në dokumente."

def categorize_document_text(text: str) -> str:
    system_prompt = "Kategorizo dokumentin: Padi, Aktgjykim, Aktvendim, Kontratë, Autorizim, Parashtresë. JSON: {'category': '...'}"
    res = _call_llm(system_prompt, text[:5000], True)
    return _parse_json_safely(res).get("category", "Të tjera")

def sterilize_legal_text(text: str) -> str:
    return sterilize_text_for_llm(text)

def extract_expense_details_from_text(raw_text: str) -> Dict[str, Any]:
    current_date = datetime.now().strftime("%Y-%m-%d")
    prompt = f"""Ti je sistem OCR për fatura.
    Data sot: {current_date}. 
    Detyra: Rregullo gabimet e OCR (0=8, 1=l) dhe nxjerr të dhënat.
    JSON: {{'merchant': 'Emri i Biznesit', 'amount': 0.0, 'date': 'YYYY-MM-DD', 'category': 'Udhëtim|Zyre|Gjyqësor'}}"""
    
    result = _parse_json_safely(_call_llm(prompt, raw_text[:3000], True))
    amount = float(result.get("amount", 0.0))
    return {
        "category": result.get("category", "Të tjera"), 
        "amount": round(amount, 2), 
        "date": result.get("date", current_date), 
        "description": result.get("merchant", "")
    }

def query_global_rag_for_claims(rag_results: str, user_query: str) -> Dict[str, Any]:
    """
    Called when searching the Global Knowledge Base (Laws).
    """
    system_prompt = f"""{KOSOVO_LEGAL_PERSONA}
    DETYRA: Bazuar në ligjet e gjetura (RAG RESULTS), sugjero pretendime ligjore për kërkesën e përdoruesit.
    RAG RESULTS: {rag_results}
    
    JSON: {{
        'suggested_claims': [
            {{ "title": "Titulli i Pretendimit", "legal_basis": "Neni X, Ligji Y", "argument": "Argumenti ligjor..." }}
        ]
    }}"""
    user_prompt = f"QUERY: {user_query}"
    return _parse_json_safely(_call_llm(system_prompt, user_prompt, True))

async def process_large_document_async(text: str, task_type: str = "SUMMARY") -> str:
    # Future expansion: Handle chunking strategies here
    return generate_summary(text)

async def stream_text_async(system_prompt: str, user_prompt: str, temp: float = 0.2) -> AsyncGenerator[str, None]:
    client = get_async_deepseek_client()
    if not client: yield "[AI Offline - Kontrolloni API Keys]"; return
    
    # Inject Persona if missing
    full_system = system_prompt if "Avokat" in system_prompt else f"{KOSOVO_LEGAL_PERSONA}\n{system_prompt}"
    
    try:
        stream = await client.chat.completions.create(
            model=OPENROUTER_MODEL, 
            messages=[{"role": "system", "content": full_system}, {"role": "user", "content": user_prompt}], 
            temperature=temp, 
            stream=True
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content: yield chunk.choices[0].delta.content
    except Exception as e:
        logger.error(f"Stream Error: {e}")
        yield f"[Lidhja u ndërpre: {str(e)}]"

# --- END OF FILE ---