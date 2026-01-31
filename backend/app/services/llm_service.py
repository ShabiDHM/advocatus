# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - CORE INTELLIGENCE V62.0 (HIGH-VALUE AUDITOR)
# 1. FEAT: Domain-Specific Intelligence (Family, Commercial, Property, Criminal).
# 2. FEAT: "The Shopping List" - Actionable Missing Evidence generation.
# 3. FEAT: Strategic "Winning Move" calculation.
# 4. STATUS: Unabridged replacement.

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
    """Robust JSON extraction handling markdown blocks and raw text."""
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
        
        logger.error(f"Failed to parse JSON content. Raw length: {len(content)}")
        return {"raw_response": content, "error": "JSON_PARSE_FAILED"}

def _call_llm(system_prompt: str, user_prompt: str, json_mode: bool = False, temp: float = 0.1) -> Optional[str]:
    """Centralized LLM execution with error handling."""
    client = get_deepseek_client()
    if not client: 
        logger.error("LLM Client Missing (Check API Keys).")
        return None
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

# --- INTELLIGENCE CORE: The "High-Value" Persona ---
# This prompt uses "Chain of Thought" to identify the domain first, then audits.

KOSOVO_LEGAL_BRAIN = """
You are the "Senior Strategic Partner" of a top law firm in Kosovo.
Your goal is to save the lawyer time and catch fatal mistakes before the judge does.

INTERNAL LOGIC (HOW TO THINK):
1. **IDENTIFY DOMAIN:** Is this Family (Divorce/Custody), Commercial (Contract/Debt), Property, or Criminal?
2. **APPLY DOMAIN RULES:**
   - *FAMILY:* Look for QPS Reports, School Records, Bank Statements for Alimony. Focus on "Best Interest of Child".
   - *COMMERCIAL:* Look for Signed Invoices, Contracts, VAT (ATK) Certificates. Check Statute of Limitations (Parashkrimi).
   - *PROPERTY:* Look for Possession Lists (Fleta Poseduese), Cadastral Maps.
   - *CRIMINAL:* Look for Indictment specifics, Alibi evidence, Procedural violations.
3. **GENERATE VALUE:** Don't just summarize. Tell the user what they *don't* know.

JSON OUTPUT GUIDELINES (STRICT):

"summary" (For the Client/Business):
- A 3-sentence "Elevator Pitch" of the case.
- Format: "The Dispute" -> "The Stakes (Money/Liberty)" -> "Current Status".
- Language: Professional, Clear, No Legalese.

"burden_of_proof" (For the Lawyer - The Audit):
- This is where you earn the money.
- AUDIT the evidence. "Plaintiff claims X, but provided no Y."
- Cite Article 319 LPK (Burden of Proof) aggressively.
- Point out contradictions.

"missing_evidence" (For the Paralegal - The Shopping List):
- BE SPECIFIC. Do not say "Financial proofs".
- Say: "Bank Statements (Last 12 Months)", "ATK Certificate", "QPS Report", "Original Contract".
- This acts as a checklist for the team.

"strategic_analysis" (The Winning Move):
- Recommend the next step.
- Examples: "File Motion to Dismiss due to Statute of Limitations", "Request Expert Financial Witness", "Seek Settlement".

"risk_level": "LOW | MEDIUM | HIGH"
"success_probability": "Percentage estimate (e.g. 65%)"
"""

def analyze_case_integrity(context: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_BRAIN}
    
    TASK: AUDIT THIS CASE FILE.
    
    REQUIRED JSON OUTPUT:
    {{
        "summary": "String (Executive Summary)",
        "key_issues": ["String (Issue 1)", "String (Issue 2)"],
        "burden_of_proof": "String (Deep Legal Audit)",
        "legal_basis": [
            {{ "law": "String (Law Name)", "article": "String (Article)", "relevance": "String (Argument)" }}
        ],
        "strategic_analysis": "String (Actionable Strategy)",
        "missing_evidence": ["String (Specific Doc 1)", "String (Specific Doc 2)"],
        "action_plan": ["String (Step 1)", "String (Step 2)"],
        "success_probability": "String",
        "risk_level": "LOW | MEDIUM | HIGH"
    }}
    """
    
    # Safe context limit
    safe_context = context[:45000] if context else "No text provided."
    return _parse_json_safely(_call_llm(system_prompt, safe_context, json_mode=True, temp=0.2))

# --- WAR ROOM & SIMULATION FUNCTIONS ---

def generate_adversarial_simulation(context: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_BRAIN}
    ROLE: The Opposing Counsel.
    TASK: Destroy our case. Find the weakest link.
    JSON: {{ 
        'opponent_strategy': 'Main attack line...', 
        'weakness_attacks': ['Attack 1', 'Attack 2'], 
        'counter_claims': ['Counter Claim...'] 
    }}"""
    return _parse_json_safely(_call_llm(system_prompt, context[:30000], True, temp=0.4))

def build_case_chronology(text: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_BRAIN}
    TASK: Build a verified Timeline.
    JSON: {{'timeline': [{{'date': 'YYYY-MM-DD', 'event': 'Description', 'source': 'Source Doc'}}]}}"""
    return _parse_json_safely(_call_llm(system_prompt, text[:40000], True))

def detect_contradictions(text: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_BRAIN}
    TASK: Find lies or mistakes.
    JSON: {{'contradictions': [{{'claim': 'Said...', 'evidence': 'Fact is...', 'severity': 'HIGH', 'impact': 'Result...'}}]}}"""
    return _parse_json_safely(_call_llm(system_prompt, text[:30000], True))

# --- UTILITY & HELPER FUNCTIONS ---

def extract_graph_data(text: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_BRAIN} Extract Entities/Relations for Graph. JSON."""
    return _parse_json_safely(_call_llm(system_prompt, text[:30000], True))

def analyze_financial_portfolio(data: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_BRAIN} Financial Forensic Audit. JSON."""
    return _parse_json_safely(_call_llm(system_prompt, data, True))

def translate_for_client(legal_text: str) -> str:
    system_prompt = f"{KOSOVO_LEGAL_BRAIN} Translate to simple Albanian for client. Explain risks clearly."
    return _call_llm(system_prompt, legal_text) or "Translation failed."

def extract_deadlines(text: str) -> Dict[str, Any]:
    system_prompt = f"{KOSOVO_LEGAL_BRAIN} Extract Deadlines (Afatet). JSON."
    return _parse_json_safely(_call_llm(system_prompt, text[:20000], True))

def perform_litigation_cross_examination(target: str, context: List[str]) -> Dict[str, Any]:
    context_str = "\n".join(context)
    system_prompt = f"{KOSOVO_LEGAL_BRAIN} Create Cross-Exam questions for {target}. Focus on credibility gaps."
    return _parse_json_safely(_call_llm(system_prompt, context_str[:40000], True))

def generate_summary(text: str) -> str:
    return _call_llm(f"{KOSOVO_LEGAL_BRAIN} 3-point Executive Summary.", text[:20000]) or ""

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
    Answer using ONLY the provided files.
    FILES:
    {context_block}
    """
    return _call_llm(prompt, question, temp=0.0) or "Nuk ka informacion."

def categorize_document_text(text: str) -> str:
    res = _call_llm("Categorize: (Padi, Aktgjykim, Provë, Kontratë). JSON {'category': '...'}.", text[:5000], True)
    return _parse_json_safely(res).get("category", "Të tjera")

def sterilize_legal_text(text: str) -> str:
    return sterilize_text_for_llm(text)

def extract_expense_details_from_text(raw_text: str) -> Dict[str, Any]:
    prompt = "Extract expense: {'amount': float, 'date': 'YYYY-MM-DD', 'merchant': '...', 'category': '...'}."
    res = _parse_json_safely(_call_llm(prompt, raw_text[:3000], True))
    return {
        "category": res.get("category", "Shpenzime"),
        "amount": float(res.get("amount", 0.0)),
        "date": res.get("date", datetime.now().strftime("%Y-%m-%d")),
        "description": res.get("merchant", "")
    }

def query_global_rag_for_claims(rag_results: str, user_query: str) -> Dict[str, Any]:
    system_prompt = f"{KOSOVO_LEGAL_BRAIN} Suggest creative legal arguments based on global jurisprudence. JSON."
    return _parse_json_safely(_call_llm(system_prompt, f"RAG: {rag_results}\nQuery: {user_query}", True))

async def process_large_document_async(text: str, task_type: str = "SUMMARY") -> str:
    return generate_summary(text)

async def stream_text_async(system_prompt: str, user_prompt: str, temp: float = 0.2) -> AsyncGenerator[str, None]:
    client = get_async_deepseek_client()
    if not client: yield "[Offline]"; return
    
    full_system = f"{KOSOVO_LEGAL_BRAIN}\n{system_prompt}"
    try:
        stream = await client.chat.completions.create(
            model=OPENROUTER_MODEL, 
            messages=[{"role": "system", "content": full_system}, {"role": "user", "content": user_prompt}], 
            temperature=temp, 
            stream=True
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content: 
                yield chunk.choices[0].delta.content
    except Exception as e:
        logger.error(f"Stream Error: {e}")
        yield f"[Error: {str(e)}]"

# --- END OF FILE ---