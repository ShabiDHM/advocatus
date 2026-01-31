# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - CORE INTELLIGENCE V52.0 (TOTAL ANALYSIS HARDENING)
# 1. FIX: Hardened prompts for Adversarial, Chronology, and Contradiction functions.
# 2. FIX: Mandated evidentiary weighing (Public vs. Private documents).
# 3. FIX: Integrated Procedural Roadblocks (Parashkrimi, Kompetenca) into Strategy.
# 4. STATUS: Unabridged replacement.

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
        match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
        if match:
            try: return json.loads(match.group(1))
            except: pass
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
ROLI: Ti je Avokat i Lartë (Senior Partner) në Prishtinë.
STANDARTI: IRAC (Issue, Rule, Analysis, Conclusion). Profesionalizëm i nivelit të lartë akademik dhe gjyqësor.
RREGULLAT E CITIMIT: "Neni [X] i Ligjit Nr. [Y/L-Z] për [Emri i Plotë]".
GJUHA: Shqipe Standarde Juridike.
"""

# --- 18 EXPORTED FUNCTIONS ---

def analyze_case_integrity(context: str) -> Dict[str, Any]:
    """
    Primary hub for the 'Analyze Case' UI. 
    Provides the dual-persona summary and deep procedural audit.
    """
    system_prompt = f"""{KOSOVO_LEGAL_PERSONA}
    OBJEKTIVI: Kryej auditimin fillestar të integritetit të lëndës.
    
    UDHËZIME:
    1. SUMMARY: Përmbledhje faktike për klientin/paralegalin.
    2. BURDEN OF PROOF: Analizo barrën e provës sipas Neneve 7 dhe 319 të LPK-së.
    3. GAP ANALYSIS: Identifiko dëshmitë që mungojnë (psh. Fleta poseduese, Certifikata e martesës, etj).
    
    JSON:
    {{
        "summary": "...",
        "key_issues": ["..."],
        "burden_of_proof": "Auditimi i detajuar i barrës së provës...",
        "legal_basis": [{{ "law": "...", "article": "...", "relevance": "..." }}],
        "strategic_analysis": "Analizë e rreziqeve procedurale (Kompetenca, Parashkrimi)...",
        "missing_evidence": ["..."],
        "action_plan": ["..."],
        "success_probability": "XX%",
        "risk_level": "LOW|MEDIUM|HIGH"
    }}
    """
    return _parse_json_safely(_call_llm(system_prompt, context[:50000], True, temp=0.2))

def generate_adversarial_simulation(context: str) -> Dict[str, Any]:
    """
    The 'War Room' Adversarial Tab.
    """
    system_prompt = f"""{KOSOVO_LEGAL_PERSONA}
    ROLI: Ti je Avokati Kundërshtar ( Devil's Advocate).
    MISIONI: Gjej "vrimat" në mbrojtjen tonë. Fokusohu te:
    1. Parashkrimi (Statute of limitations).
    2. Mungesa e legjitimitetit aktiv/pasiv.
    3. Shkeljet procedurale në sigurimin e provave.
    
    JSON:
    {{
        "opponent_strategy": "Strategjia kryesore që do të përdorte kundërshtari...",
        "weakness_attacks": ["Si do t'i sulmojë provat tona?", "Cilat afate mund të pretendojë se kanë kaluar?"],
        "counter_claims": ["Kundërpaditë e mundshme..."]
    }}
    """
    return _parse_json_safely(_call_llm(system_prompt, context[:30000], True, temp=0.4))

def build_case_chronology(text: str) -> Dict[str, Any]:
    """
    The 'War Room' Chronology Tab.
    """
    system_prompt = f"""{KOSOVO_LEGAL_PERSONA}
    DETYRA: Krijo kronologjinë e lëndës. 
    KUJDES: Vetëm ngjarjet me rëndësi JURIDIKE (psh. dorëzimi i padisë, njoftimi, data e kontratës). 
    Injoro bisedat e parëndësishme.
    
    JSON:
    {{
        "timeline": [
            {{ "date": "YYYY-MM-DD", "event": "Përshkrimi i shkurtër juridik", "source": "Dokumenti referues" }}
        ]
    }}
    """
    return _parse_json_safely(_call_llm(system_prompt, text[:40000], True))

def detect_contradictions(text: str) -> Dict[str, Any]:
    """
    The 'War Room' Contradictions Tab.
    """
    system_prompt = f"""{KOSOVO_LEGAL_PERSONA}
    DETYRA: Analizo mospërputhjet në dëshmi dhe dokumente.
    PESHIMI I PROVAVE: Dokumenti publik (Akt Publik) ka përparësi ndaj dëshmisë verbale.
    
    JSON:
    {{
        "contradictions": [
            {{ 
                "claim": "Deklarata A", 
                "evidence": "Prova B që e kundërshton", 
                "severity": "HIGH|MEDIUM|LOW", 
                "impact": "Si ndikon kjo në besueshmërinë e palës?" 
            }}
        ]
    }}
    """
    return _parse_json_safely(_call_llm(system_prompt, text[:30000], True))

def extract_graph_data(text: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_PERSONA}
    DETYRA: Shndërro lëndën në Hartë Logjike: Claim -> Fact -> Evidence -> Law.
    JSON: {{"nodes": [{{"id": "id", "name": "...", "type": "..."}}], "edges": [{{"source": "id1", "relation": "...", "target": "id2"}}]}}"""
    return _parse_json_safely(_call_llm(system_prompt, text[:30000], True))

def analyze_financial_portfolio(data: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_PERSONA}
    ROLI: Ekspert Financiar Gjyqësor. Analizo për parregullsi dhe evazion sipas standardeve të Kosovës.
    JSON: {{'executive_summary': '...', 'anomalies': [], 'recommendations': []}}"""
    return _parse_json_safely(_call_llm(system_prompt, data, True))

def translate_for_client(legal_text: str) -> str:
    system_prompt = f"""{KOSOVO_LEGAL_PERSONA} 
    DETYRA: Shpjego këtë tekst për klientin sikur po i flet në zyre, thjeshtë por me autoritet."""
    return _call_llm(system_prompt, legal_text) or "Gabim."

def extract_deadlines(text: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_PERSONA} 
    DETYRA: Gjej afatet prekluzive sipas LPK/LPP të Kosovës.
    JSON: {{'is_judgment': bool, 'deadline_date': 'YYYY-MM-DD', 'action_required': '...'}}"""
    return _parse_json_safely(_call_llm(system_prompt, text[:15000], True))

def perform_litigation_cross_examination(target_text: str, context_summaries: List[str]) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_PERSONA} 
    DETYRA: Kryqëzo dokumentin e ri me krejt dosjen. A po gënjen dikush?
    JSON: {{'consistency_check': '...', 'contradictions': [], 'corroborations': []}}"""
    user_prompt = f"TARGET: {target_text[:15000]}\nCONTEXT: {' '.join(context_summaries)}"
    return _parse_json_safely(_call_llm(system_prompt, user_prompt, True))

def generate_summary(text: str) -> str:
    system_prompt = f"{KOSOVO_LEGAL_PERSONA} Përmblidh dokumentin në 3 pika kyçe juridike."
    return _call_llm(system_prompt, text[:20000]) or ""

def get_embedding(text: str) -> List[float]:
    client = get_openai_client()
    if client:
        try: return client.embeddings.create(input=[text.replace("\n", " ")], model=EMBEDDING_MODEL).data[0].embedding
        except: pass
    return [0.0] * 1536 

def forensic_interrogation(question: str, context_rows: List[str]) -> str:
    prompt = f"""{KOSOVO_LEGAL_PERSONA}
    Përgjigju VETËM nga provat: {' '.join(context_rows)}"""
    return _call_llm(prompt, question) or "Nuk ka informacion."

def categorize_document_text(text: str) -> str:
    system_prompt = "Kategorizo: Padi, Aktgjykim, Vendim, Kontratë, Parashtresë."
    res = _call_llm(system_prompt, text[:5000], True)
    return _parse_json_safely(res).get("category", "Të tjera")

def sterilize_legal_text(text: str) -> str:
    return sterilize_text_for_llm(text)

def extract_expense_details_from_text(raw_text: str) -> Dict[str, Any]:
    current_date = datetime.now().strftime("%Y-%m-%d")
    prompt = f"Nxjerr faturën JSON: {{'merchant': '...', 'amount': 0.0, 'date': '...', 'category': '...'}}"
    result = _parse_json_safely(_call_llm(prompt, raw_text[:3000], True))
    amount = float(result.get("amount", 0.0))
    return {"category": result.get("category", "Të tjera"), "amount": round(amount, 2), "date": result.get("date", current_date), "description": result.get("merchant", "")}

def query_global_rag_for_claims(rag_results: str, user_query: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_PERSONA}
    DETYRA: Bazuar në ligjet e Kosovës, sugjero pretendime ligjore.
    JSON: {{ 'suggested_claims': [ {{ "title": "...", "legal_basis": "...", "argument": "..." }} ] }}"""
    user_prompt = f"RAG: {rag_results}\nQUERY: {user_query}"
    return _parse_json_safely(_call_llm(system_prompt, user_prompt, True))

async def process_large_document_async(text: str, task_type: str = "SUMMARY") -> str:
    return generate_summary(text)

async def stream_text_async(system_prompt: str, user_prompt: str, temp: float = 0.2) -> AsyncGenerator[str, None]:
    client = get_async_deepseek_client()
    if not client: yield "[AI Offline]"; return
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
        yield f"[Gabim: {str(e)}]"

# --- END OF FILE ---