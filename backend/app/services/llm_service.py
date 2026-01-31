# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - CORE INTELLIGENCE V56.0 (TOTAL SUBSTANCE & ATTRIBUTE FIX)
# 1. FIX: Restored top-level function visibility to resolve Pylance Attribute errors.
# 2. FIX: Mandated "Substanca e Nenit" (Textual content) in legal citations.
# 3. FIX: Total removal of "Issue/Gap" terminology in favor of "Çështja/Mangësia".
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

# --- EXPORT LIST (VERIFIED: 18 FUNCTIONS FOR PYLANCE) ---
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
def get_deepseek_client() -> Optional[OpenAI]:
    if not DEEPSEEK_API_KEY: return None
    return OpenAI(api_key=DEEPSEEK_API_KEY, base_url=OPENROUTER_BASE_URL)

def get_openai_client() -> Optional[OpenAI]:
    if not OPENAI_API_KEY: return None
    return OpenAI(api_key=OPENAI_API_KEY)

def get_async_deepseek_client() -> Optional[AsyncOpenAI]:
    if not DEEPSEEK_API_KEY: return None
    return AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url=OPENROUTER_BASE_URL)

# --- CORE UTILITIES ---
def _parse_json_safely(content: Optional[str]) -> Dict[str, Any]:
    if not content: return {}
    try:
        return json.loads(content)
    except Exception:
        match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
        if match:
            try: return json.loads(match.group(1))
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
ROLI: Ti je Avokat i Lartë (Senior Partner) në një studio prestigjioze në Prishtinë.
GJUHA: Shqipe Letrare Juridike. Ndalohet çdo fjalë angleze (Issue, Gap, Summary, Plan).
TERMINOLOGJIA: Përdor "Kontributi për mbajtje" (jo alimentacion), "Mangësitë" (jo gaps), "Çështjet" (jo issues).

RREGULLAT E CITIMIT (MANDATORE):
1. Te fusha 'relevance', DUHET të citosh fillimisht përmbajtjen tekstuale ose substancën e nenit (psh: "Ky nen parashikon detyrimin e prindit që...") para se të bësh lidhjen me rastin.
2. FORMATI: "Neni [X] i Ligjit Nr. [Y] për [Emri i Plotë i Ligjit] i Republikës së Kosovës".
"""

# --- 18 CORE FUNCTIONS ---

def analyze_case_integrity(context: str) -> Dict[str, Any]:
    """Provides the dual-persona legal audit."""
    system_prompt = f"""{KOSOVO_LEGAL_PERSONA}
    OBJEKTIVI: Auditimi i plotë i integritetit të lëndës.
    
    UDHËZIME:
    - PËRMBLEDHJA: Shpjego thelbin e rastit thjeshtë për klientin.
    - BARRA E PROVËS: Përcakto saktë detyrimin sipas Nenit 319 të LPK-së.
    - BAZA LIGJORE: Shkruaj saktë përmbajtjen e nenit.
    
    JSON:
    {{
        "summary": "Përmbledhja faktike...",
        "key_issues": ["Çështja 1 (Juridike)", "Çështja 2 (Procedurale)"],
        "burden_of_proof": "Auditimi i detajuar i detyrimit për të provuar faktet...",
        "legal_basis": [{{ "law": "...", "article": "...", "relevance": "Përmbajtja e nenit: [Teksti]. Lidhja me rastin: [Analiza]." }}],
        "strategic_analysis": "Analiza strategjike...",
        "missing_evidence": ["Mangësia 1 (Dokumenti)", "Mangësia 2 (Prova)"],
        "action_plan": ["Veprimi 1", "Veprimi 2"],
        "success_probability": "XX%",
        "risk_level": "I ULËT|I MESËM|I LARTË"
    }}"""
    return _parse_json_safely(_call_llm(system_prompt, context[:50000], True, temp=0.2))

def extract_graph_data(text: str) -> Dict[str, Any]:
    """Generates nodes and edges for the AI Evidence Map."""
    system_prompt = f"""{KOSOVO_LEGAL_PERSONA}
    DETYRA: Shndërro tekstin në Hartë Logjike: Pretendim (Claim), Fakt (Fact), Provë (Evidence), Ligj (Law).
    JSON: {{"nodes": [{{"id": "...", "name": "...", "type": "..."}}], "edges": [{{"source": "...", "relation": "...", "target": "..."}}]}}"""
    return _parse_json_safely(_call_llm(system_prompt, text[:30000], True))

def generate_adversarial_simulation(context: str) -> Dict[str, Any]:
    """The 'Devil's Advocate' simulation."""
    system_prompt = f"""{KOSOVO_LEGAL_PERSONA}
    ROLI: Avokati Kundërshtar. Gjej dobësitë tona (Parashkrimi, Kompetenca, Mungesa e legjitimitetit).
    JSON: {{ 'opponent_strategy': '...', 'weakness_attacks': [], 'counter_claims': [] }}"""
    return _parse_json_safely(_call_llm(system_prompt, context[:30000], True, temp=0.4))

def build_case_chronology(text: str) -> Dict[str, Any]:
    """Creates a legal timeline of events."""
    system_prompt = f"""{KOSOVO_LEGAL_PERSONA}
    DETYRA: Kronologjia e fakteve juridike relevante. JSON: {{'timeline': [{{'date': 'YYYY-MM-DD', 'event': '...', 'source': '...'}}]}}"""
    return _parse_json_safely(_call_llm(system_prompt, text[:40000], True))

def detect_contradictions(text: str) -> Dict[str, Any]:
    """Identifies inconsistencies in evidence."""
    system_prompt = f"""{KOSOVO_LEGAL_PERSONA}
    DETYRA: Identifiko kontradiktat. Dokumentet publike kanë përparësi absolute.
    JSON: {{'contradictions': [{{'claim': '...', 'evidence': '...', 'severity': 'HIGH|LOW', 'impact': '...'}}]}}"""
    return _parse_json_safely(_call_llm(system_prompt, text[:30000], True))

def analyze_financial_portfolio(data: str) -> Dict[str, Any]:
    """Forensic financial analysis."""
    system_prompt = f"""{KOSOVO_LEGAL_PERSONA}
    ROLI: Ekspert Financiar. JSON: {{'executive_summary': '...', 'anomalies': [], 'recommendations': []}}"""
    return _parse_json_safely(_call_llm(system_prompt, data, True))

def translate_for_client(legal_text: str) -> str:
    """Simplifies legal jargon for the end client."""
    system_prompt = f"""{KOSOVO_LEGAL_PERSONA} DETYRA: Shpjego këtë tekst për klientin thjeshtë."""
    return _call_llm(system_prompt, legal_text) or "Gabim."

def extract_deadlines(text: str) -> Dict[str, Any]:
    """Identifies legal deadlines from court documents."""
    system_prompt = f"""{KOSOVO_LEGAL_PERSONA} DETYRA: Gjej afatet prekluzive. JSON: {{'is_judgment': bool, 'deadline_date': 'YYYY-MM-DD', 'action_required': '...'}}"""
    return _parse_json_safely(_call_llm(system_prompt, text[:15000], True))

def perform_litigation_cross_examination(target_text: str, context_summaries: List[str]) -> Dict[str, Any]:
    """Cross-checks new documents against existing case knowledge."""
    system_prompt = f"""{KOSOVO_LEGAL_PERSONA} DETYRA: Kryqëzo provat. JSON: {{'consistency_check': '...', 'contradictions': [], 'corroborations': []}}"""
    user_prompt = f"TARGET: {target_text[:15000]}\nCONTEXT: {' '.join(context_summaries)}"
    return _parse_json_safely(_call_llm(system_prompt, user_prompt, True))

def generate_summary(text: str) -> str:
    """Generates a brief legal summary."""
    system_prompt = f"{KOSOVO_LEGAL_PERSONA} Përmblidh dokumentin në 3 pika kyçe."
    return _call_llm(system_prompt, text[:20000]) or ""

def get_embedding(text: str) -> List[float]:
    """Generates vector embeddings for RAG."""
    client = get_openai_client()
    if not client: return [0.0] * 1536
    try:
        res = client.embeddings.create(input=[text.replace("\n", " ")], model=EMBEDDING_MODEL)
        return res.data[0].embedding
    except: return [0.0] * 1536

def forensic_interrogation(question: str, context_rows: List[str]) -> str:
    """Answering specific questions from case evidence."""
    prompt = f"{KOSOVO_LEGAL_PERSONA} Përgjigju nga provat: {' '.join(context_rows)}"
    return _call_llm(prompt, question) or "Nuk u gjet informacion."

def categorize_document_text(text: str) -> str:
    """Classifies the type of legal document."""
    system_prompt = "Kategorizo: Padi, Aktgjykim, Aktvendim, Kontratë, Parashtresë."
    res = _call_llm(system_prompt, text[:5000], True)
    return _parse_json_safely(res).get("category", "Të tjera")

def sterilize_legal_text(text: str) -> str:
    """Removes PII from legal text."""
    return sterilize_text_for_llm(text)

def extract_expense_details_from_text(raw_text: str) -> Dict[str, Any]:
    """Extracts financial data from OCR receipts."""
    current_date = datetime.now().strftime("%Y-%m-%d")
    prompt = f"Nxjerr faturën JSON: {{'merchant': '...', 'amount': 0.0, 'date': '...', 'category': '...'}}"
    result = _parse_json_safely(_call_llm(prompt, raw_text[:3000], True))
    amount = float(result.get("amount", 0.0))
    return {"category": result.get("category", "Të tjera"), "amount": round(amount, 2), "date": result.get("date", current_date), "description": result.get("merchant", "")}

def query_global_rag_for_claims(rag_results: str, user_query: str) -> Dict[str, Any]:
    """Suggests legal claims based on Global KB (Laws)."""
    system_prompt = f"""{KOSOVO_LEGAL_PERSONA} DETYRA: Sugjero pretendime nga ligjet. JSON: {{ 'suggested_claims': [ {{ "title": "...", "legal_basis": "...", "argument": "..." }} ] }}"""
    user_prompt = f"RAG: {rag_results}\nQUERY: {user_query}"
    return _parse_json_safely(_call_llm(system_prompt, user_prompt, True))

async def process_large_document_async(text: str, task_type: str = "SUMMARY") -> str:
    """Async wrapper for document processing."""
    return generate_summary(text)

async def stream_text_async(system_prompt: str, user_prompt: str, temp: float = 0.2) -> AsyncGenerator[str, None]:
    """Streams LLM output for real-time UI updates."""
    client = get_async_deepseek_client()
    if not client: yield "[Offline]"; return
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
        yield f"[Gabim: {str(e)}]"

# --- END OF FILE ---