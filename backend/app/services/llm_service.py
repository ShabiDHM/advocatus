# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - CORE INTELLIGENCE V67.0 (MULTI-DOMAIN SUBSTANTIVE LOGIC)
# 1. FIX: Eliminated Procedural Bias. AI now prioritizes Substantive Law (Material) over LPK.
# 2. FEAT: Enhanced Multi-Domain Intelligence (Family, Labor, Obligations, Property).
# 3. INTEGRITY: Preserved 100% of V65.0 structure, Persona-Driven JSON, and all Utility functions.
# 4. STATUS: Unabridged. No truncation. Clean replacement.

import os
import json
import logging
import re
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime
from openai import OpenAI, AsyncOpenAI

from .text_sterilization_service import sterilize_text_for_llm

logger = logging.getLogger(__name__)

# --- EXPORT LIST ---
__all__ = [
    "analyze_financial_portfolio", "analyze_case_integrity", "generate_adversarial_simulation",
    "build_case_chronology", "translate_for_client", "detect_contradictions",
    "extract_deadlines", "perform_litigation_cross_examination", "generate_summary",
    "extract_graph_data", "get_embedding", "forensic_interrogation",
    "categorize_document_text", "sterilize_legal_text", "extract_expense_details_from_text",
    "query_global_rag_for_claims", "process_large_document_async", "stream_text_async"
]

# --- CONFIGURATION ---
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat"
EMBEDDING_MODEL = "text-embedding-3-small"

def get_deepseek_client():
    return OpenAI(api_key=DEEPSEEK_API_KEY, base_url=OPENROUTER_BASE_URL) if DEEPSEEK_API_KEY else None

def get_openai_client():
    return OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

def get_async_deepseek_client():
    return AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url=OPENROUTER_BASE_URL) if DEEPSEEK_API_KEY else None

def _parse_json_safely(content: Optional[str]) -> Dict[str, Any]:
    if not content: return {}
    try:
        return json.loads(content)
    except:
        match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
        if match:
            try: return json.loads(match.group(1))
            except: pass
        try:
            match_loose = re.search(r'(\{.*\})', content, re.DOTALL)
            if match_loose: return json.loads(match_loose.group(1))
        except: pass

        logger.error(f"Failed to parse JSON content: {content[:100]}...")
        return {"raw_response": content, "error": "JSON_PARSE_FAILED"}

def _call_llm(system_prompt: str, user_prompt: str, json_mode: bool = False, temp: float = 0.1) -> Optional[str]:
    client = get_deepseek_client()
    if not client: return None
    try:
        kwargs = {
            "model": OPENROUTER_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temp
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        res = client.chat.completions.create(**kwargs)
        return res.choices[0].message.content
    except Exception as e:
        logger.error(f"LLM Call Failed: {e}")
        return None

# --- INTELLIGENCE CORE: PARTNERI EKZEKUTIV (SHQIP) ---

KOSOVO_LEGAL_BRAIN = """
ROLI: Ti je 'Senior Legal Partner' në një firmë ligjore prestigjioze në Kosovë. Ekspert i të Drejtës Civile, Familjare, të Punës dhe Detyrimeve.
DETYRA: Të prodhosh analiza ligjore të nivelit të Gjykatës Supreme: të sakta, të bazuara në fakte dhe strategjike.
GJUHA: VETËM SHQIP.

RREGULLI I PRIORITETIT (HIERARKIA E LIGJIT):
1. LIGJI MATERIAL (SUBSTANTIV): Gjithmonë jep përparësi Ligjit Material që rregullon thelbin e çështjes (p.sh. Ligji për Familjen, Ligji i Punës, Ligji për Detyrimet).
2. LIGJI PROCEDURAL (LPK): Përdor LPK-në (03/L-006) vetëm për të mbështetur procedurën, afatet dhe barrën e provës. 
3. ANALIZA MULTI-DOMAIN: Identifiko fushën e rastit nga faktet dhe gjej nenet përkatëse në bazën ligjore të ofruar. Mos u mjafto vetëm me nene procedurale.

STRUKTURA E ARGUMENTIMIT (Për BAZËN LIGJORE):
1. **PARIMI:** Shpjego qartë parimin material ose procedural.
2. **LIDHJA ME RASTIN:** Apliko parimin drejtpërdrejt te faktet e rastit nga dokumentet.
3. **CITIM:** Formati zyrtar [Emri i Ligjit, Neni X].
"""

def analyze_case_integrity(context: str) -> Dict[str, Any]:
    """
    Performs a Persona-Driven, Zero-Trust RAG analysis. 
    Updated V67.0: Enforces Substantive Law Priority.
    """
    system_prompt = f"""{KOSOVO_LEGAL_BRAIN}

    --- URDHËR I PADISKUTUESHËM: ZERO-TRUST RAG ---
    1. ANALIZA JOTE DUHET TË BAZOHET **VETËM DHE EKSKLUZIVISHT** NË KONTEKSTIN NËN TITUJT `=== KONTEKSTI I RASTIT ===` DHE `=== BAZA LIGJORE ===`.
    2. PRIORITETI I LIGJIT: Skano bazën ligjore për ligjin material që rregullon subjektin e rastit (p.sh. nëse rasti është për alimentacion, përdor Ligjin për Familjen). Mos u bazo vetëm te LPK.
    3. NËSE KONTEKSTI NUK KA INFORMACION, shkruaj: "Konteksti i ofruar është i pamjaftueshëm."
    
    --- DETYRA: KRIJO ANALIZËN JSON ---
    
    {{
      "executive_summary": "...", // PËR BIZNESIN: Përmbledhje e thjeshtë, jo-teknike.
      "paralegal_checklist": {{
        "missing_evidence": ["...", "..."], // PËR PARALEGALIN: Dokumente reale (ATK, QPS, etj).
        "action_plan": ["...", "..."] 
      }},
      "legal_audit": {{
        "burden_of_proof": "...", // PËR AVOKATIN: Analiza forensic (Neni 7 & 319 LPK).
        "legal_basis": [ // PËR AVOKATIN: MINIMUMI 2 NENE NGA LIGJI MATERIAL (p.sh. Familja/Detyrimet).
          {{
            "law": "Emri i Ligjit Material",
            "article": "Neni X",
            "relevance": "PARIMI: ... LIDHJA ME RASTIN: ... CITIM: ..."
          }}
        ]
      }},
      "strategic_recommendation": {{ 
        "recommendation_text": "...", 
        "success_probability": "XX%", 
        "risk_level": "I ULËT | I MESËM | I LARTË" 
      }}
    }}
    """
    
    safe_context = context[:100000] if context else "Konteksti nuk u ofrua."
    new_analysis = _parse_json_safely(_call_llm(system_prompt, safe_context, json_mode=True, temp=0.2))

    if not new_analysis or "executive_summary" not in new_analysis:
        return {
            "summary": "Analiza dështoi. Provoni përsëri.",
            "key_issues": [], "legal_basis": [], "strategic_analysis": "Nuk ka.", "burden_of_proof": "Nuk ka.",
            "missing_evidence": [], "action_plan": [], "risk_level": "I LARTË", "success_probability": "0%"
        }

    # Adapter to maintain frontend mapping from V65.0
    legal_audit = new_analysis.get("legal_audit", {})
    paralegal_checklist = new_analysis.get("paralegal_checklist", {})
    strategic_rec = new_analysis.get("strategic_recommendation", {})

    return {
        "summary": new_analysis.get("executive_summary", "Përmbledhja nuk u gjenerua."),
        "key_issues": [], 
        "burden_of_proof": legal_audit.get("burden_of_proof", "Analiza e barrës nuk u gjenerua."),
        "legal_basis": legal_audit.get("legal_basis", []),
        "strategic_analysis": strategic_rec.get("recommendation_text", "Rekomandimi nuk u gjenerua."),
        "missing_evidence": paralegal_checklist.get("missing_evidence", []),
        "action_plan": paralegal_checklist.get("action_plan", []),
        "success_probability": strategic_rec.get("success_probability", "N/A"),
        "risk_level": strategic_rec.get("risk_level", "I MESËM")
    }

# --- WAR ROOM & SIMULATION FUNCTIONS (RESTORED FROM V65.0) ---

def generate_adversarial_simulation(context: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_BRAIN}
    ROLI: Ti je Avokati i Palës Kundërshtare. Gjej pikat tona më të dobëta materiale.
    DETYRA: Bazoje analizën tënde VETËM në kontekstin e ofruar.
    OUTPUT JSON: {{ "opponent_strategy": "...", "weakness_attacks": ["..."], "counter_claims": ["..."] }}"""
    return _parse_json_safely(_call_llm(system_prompt, context[:30000], True, temp=0.4))

def build_case_chronology(text: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_BRAIN}
    DETYRA: Ekstrakto një kronologji të verifikuar (Data, Ngjarja, Burimi).
    JSON: {{ "timeline": [{{ "date": "YYYY-MM-DD", "event": "...", "source": "..." }}] }}"""
    return _parse_json_safely(_call_llm(system_prompt, text[:40000], True))

def detect_contradictions(text: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_BRAIN}
    DETYRA: Vepro si hetues. Gjej mospërputhje mes dëshmive dhe provave.
    JSON: {{ "contradictions": [{{ "claim": "...", "evidence": "...", "severity": "...", "impact": "..." }}] }}"""
    return _parse_json_safely(_call_llm(system_prompt, text[:30000], True))

# --- UTILITY & HELPER FUNCTIONS (RESTORED FROM V65.0) ---

def extract_graph_data(text: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_BRAIN} Nxjerr Entitetet dhe Lidhjet mes tyre. JSON: {{'nodes':[], 'edges':[]}}."""
    return _parse_json_safely(_call_llm(system_prompt, text[:30000], True))

def analyze_financial_portfolio(data: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_BRAIN} Analizo të dhënat financiare. JSON."""
    return _parse_json_safely(_call_llm(system_prompt, data, True))

def translate_for_client(legal_text: str) -> str:
    system_prompt = f"{KOSOVO_LEGAL_BRAIN} Përkthe këtë tekst ligjor në gjuhë të thjeshtë popullore."
    return _call_llm(system_prompt, legal_text) or "Përkthimi dështoi."

def extract_deadlines(text: str) -> Dict[str, Any]:
    system_prompt = f"{KOSOVO_LEGAL_BRAIN} Gjej të gjitha Afatet Ligjore. JSON: {{'deadlines':[]}}."
    return _parse_json_safely(_call_llm(system_prompt, text[:20000], True))

def perform_litigation_cross_examination(target: str, context: List[str]) -> Dict[str, Any]:
    context_str = "\n".join(context)
    system_prompt = f"{KOSOVO_LEGAL_BRAIN} Përgatit pyetje kryqëzuese për: {target}. JSON: {{'questions':[]}}."
    return _parse_json_safely(_call_llm(system_prompt, context_str[:40000], True))

def generate_summary(text: str) -> str:
    return _call_llm(f"{KOSOVO_LEGAL_BRAIN} Krijo një përmbledhje ekzekutive në 3 pika.", text[:20000]) or ""

def get_embedding(text: str) -> List[float]:
    client = get_openai_client()
    if not client: return [0.0] * 1536
    try:
        res = client.embeddings.create(input=[text.replace("\n", " ")], model=EMBEDDING_MODEL)
        return res.data[0].embedding
    except Exception as e:
        logger.error(f"Embedding failed: {e}")
        return [0.0] * 1536

def forensic_interrogation(question: str, context_rows: List[str]) -> str:
    context_block = "\n---\n".join(context_rows)
    prompt = f"""{KOSOVO_LEGAL_BRAIN}
    Përgjigju VETËM duke përdorur informacionin nga dokumentet:
    {context_block}
    """
    return _call_llm(prompt, question, temp=0.0) or "Nuk ka informacion."

def categorize_document_text(text: str) -> str:
    res = _call_llm("Kategorizo këtë tekst (Padi, Kontratë, etj). Kthe JSON {'category': '...'}.", text[:5000], True)
    return _parse_json_safely(res).get("category", "Të tjera")

def sterilize_legal_text(text: str) -> str:
    return sterilize_text_for_llm(text)

def extract_expense_details_from_text(raw_text: str) -> Dict[str, Any]:
    prompt = "Nxirr shpenzimin JSON: {'amount': float, 'date': 'YYYY-MM-DD', 'merchant': 'emri', 'category': 'kategoria'}."
    res = _parse_json_safely(_call_llm(prompt, raw_text[:3000], True))
    return {
        "category": res.get("category", "Shpenzime"),
        "amount": float(res.get("amount", 0.0)),
        "date": res.get("date", datetime.now().strftime("%Y-%m-%d")),
        "description": res.get("merchant", "")
    }

def query_global_rag_for_claims(rag_results: str, user_query: str) -> Dict[str, Any]:
    system_prompt = f"{KOSOVO_LEGAL_BRAIN} Sugjero argumente shtesë nga praktika gjyqësore. JSON: {{'suggestions':[]}}."
    return _parse_json_safely(_call_llm(system_prompt, f"RAG Results: {rag_results}\nQuery: {user_query}", True))

async def process_large_document_async(text: str, task_type: str = "SUMMARY") -> str:
    return generate_summary(text)

async def stream_text_async(system_prompt: str, user_prompt: str, temp: float = 0.2) -> AsyncGenerator[str, None]:
    client = get_async_deepseek_client()
    if not client: yield "[SISTEMI OFFLINE]"; return
    full_system = f"{KOSOVO_LEGAL_BRAIN}\n{system_prompt}"
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
        yield f"[GABIM NË SISTEM: {str(e)}]"

# --- END OF FILE ---