# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - CORE INTELLIGENCE V64.0 (HIGH-AUTHORITY STYLE)
# 1. FIX: "Legal Basis" now follows the User's "Sample Output" structure exactly.
# 2. FEAT: Enforced 3-Part Argumentation (Principle -> Application -> Citation).
# 3. FIX: Corrected Law Numbers (Family Law 2004/32 vs Obligations 04/L-077).

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
ROLI: Ti je 'Senior Legal Partner' në Kosovë.
DETYRA: Të prodhosh analiza ligjore të nivelit 'Supreme Court'.
GJUHA: VETËM SHQIP.

STRUKTURA E ARGUMENTIMIT (Baza Ligjore):
Kur citon një ligj, ndiq KËTË STRUKTURË FIKSE (jo shkurtime):
1. **PARIMI:** Shpjego çka thotë neni (jo vetëm numrin). Psh: "Ky nen parashikon..."
2. **LIDHJA ME RASTIN:** Apliko parimin te faktet. Psh: "Në këtë rast, paditësi dështoi..."
3. **CITIM:** Formati zyrtar. Psh: [Ligji Nr. 2004/32 për Familjen, Neni 15]

LOGJIKA E DOMINIT (Rulebook):
1. RASTE FAMILJARE (Ligji Nr. 2004/32):
   - Fokusi: "Interesi më i lartë i fëmijës".
   - Dokumente Kyçe: Raporti i QPS, Vërtetimi i Pagave, Shpenzimet e fëmijës.
2. RASTE DETYRIMESH (Ligji Nr. 04/L-077):
   - Fokusi: "Pacta Sunt Servanda" (Kontrata duhet respektuar).
   - Dokumente Kyçe: Faturat, Kontrata Bazë, Librat Kontabël.
3. RASTE PROCEDURALE (Ligji Nr. 03/L-006 - LPK):
   - Fokusi: "Barra e Provës" (Neni 7, 319).

FORMATI JSON (DALJA E KËRKUAR):

"summary":
- Një tekst narrativ profesional.
- Shpjego konfliktin sikur t'ia prezantoje Gjyqtarit në fjalën hyrëse.

"burden_of_proof":
- Auditimi "Forensic".
- Cito Nenet 7 & 319 LPK.
- Identifiko saktësisht kush dështoi të sjellë prova.
- Përdor shprehje si "Vakuum provues", "Pretendim i pa mbështetur".

"missing_evidence":
- "Checklist" për asistentin.
- Të jenë dokumente reale të sistemit të Kosovës (ATK, QPS, Kadastër, Trusti).

"strategic_analysis":
- Këshilla përfundimtare. A të shkojmë në gjyq apo në pajtim?
"""

def analyze_case_integrity(context: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_BRAIN}
    
    DETYRA: KRYEJ ANALIZËN E PLOTË LIGJORE.
    
    UDHËZIM SPECIFIK PËR 'LEGAL_BASIS':
    Te fusha 'relevance', MOS shkruaj vetëm një fjali. Shkruaj një paragraf të plotë që përmban:
    (1) Përmbajtjen e Nenit dhe (2) Analizën e Rastit.
    
    OUTPUT JSON:
    {{
        "summary": "Teksti narrative...",
        "key_issues": ["Çështja 1...", "Çështja 2..."],
        "burden_of_proof": "Auditimi kritik...",
        "legal_basis": [
            {{ 
                "law": "Emri i Ligjit (psh: Ligji Nr. 2004/32 për Familjen)", 
                "article": "Neni X", 
                "relevance": "PARIMI: [Shpjego ligjin]... LIDHJA ME RASTIN: [Analizo faktet]... CITIM: [Formati Zyrtar]"
            }}
        ],
        "strategic_analysis": "Rekomandimi strategjik...",
        "missing_evidence": ["Dokumenti 1...", "Dokumenti 2..."],
        "action_plan": ["Hapi 1...", "Hapi 2..."],
        "success_probability": "XX%",
        "risk_level": "I ULËT | I MESËM | I LARTË"
    }}
    """
    
    safe_context = context[:45000] if context else "Nuk ka tekst."
    return _parse_json_safely(_call_llm(system_prompt, safe_context, json_mode=True, temp=0.2))

# --- WAR ROOM & SIMULATION FUNCTIONS ---

def generate_adversarial_simulation(context: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_BRAIN}
    ROLI: Avokati Kundërshtar.
    DETYRA: Zbulo dobësitë tona.
    JSON: {{ 'opponent_strategy': '...', 'weakness_attacks': ['...'], 'counter_claims': ['...'] }}"""
    return _parse_json_safely(_call_llm(system_prompt, context[:30000], True, temp=0.4))

def build_case_chronology(text: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_BRAIN}
    DETYRA: Kronologjia e verifikuar (Datat, Ngjarjet, Burimi).
    JSON: {{'timeline': [{{'date': 'YYYY-MM-DD', 'event': '...', 'source': '...'}}]}}"""
    return _parse_json_safely(_call_llm(system_prompt, text[:40000], True))

def detect_contradictions(text: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_BRAIN}
    DETYRA: Zbulo Gënjeshtrat (Impeachment).
    JSON: {{'contradictions': [{{'claim': '...', 'evidence': '...', 'severity': 'I LARTË', 'impact': '...'}}]}}"""
    return _parse_json_safely(_call_llm(system_prompt, text[:30000], True))

# --- UTILITY & HELPER FUNCTIONS ---

def extract_graph_data(text: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_BRAIN} Nxjerr Entitetet dhe Lidhjet. JSON."""
    return _parse_json_safely(_call_llm(system_prompt, text[:30000], True))

def analyze_financial_portfolio(data: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_BRAIN} Analizo Financat. JSON."""
    return _parse_json_safely(_call_llm(system_prompt, data, True))

def translate_for_client(legal_text: str) -> str:
    system_prompt = f"{KOSOVO_LEGAL_BRAIN} Përkthe ligjin në gjuhë të thjeshtë popullore."
    return _call_llm(system_prompt, legal_text) or "Përkthimi dështoi."

def extract_deadlines(text: str) -> Dict[str, Any]:
    system_prompt = f"{KOSOVO_LEGAL_BRAIN} Gjej Afatet (Ankesat, Përgjigjet). JSON."
    return _parse_json_safely(_call_llm(system_prompt, text[:20000], True))

def perform_litigation_cross_examination(target: str, context: List[str]) -> Dict[str, Any]:
    context_str = "\n".join(context)
    system_prompt = f"{KOSOVO_LEGAL_BRAIN} Përgatit pyetje kryqëzuese për: {target}."
    return _parse_json_safely(_call_llm(system_prompt, context_str[:40000], True))

def generate_summary(text: str) -> str:
    return _call_llm(f"{KOSOVO_LEGAL_BRAIN} Përmbledhje ekzekutive (3 pika).", text[:20000]) or ""

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
    Përgjigju VETËM nga dokumentet e mëposhtme:
    {context_block}
    """
    return _call_llm(prompt, question, temp=0.0) or "Nuk ka informacion."

def categorize_document_text(text: str) -> str:
    res = _call_llm("Kategorizo: (Padi, Aktgjykim, Provë, Kontratë). JSON {'category': '...'}.", text[:5000], True)
    return _parse_json_safely(res).get("category", "Të tjera")

def sterilize_legal_text(text: str) -> str:
    return sterilize_text_for_llm(text)

def extract_expense_details_from_text(raw_text: str) -> Dict[str, Any]:
    prompt = "Nxjerr shpenzimin: {'amount': float, 'date': 'YYYY-MM-DD', 'merchant': '...', 'category': '...'}."
    res = _parse_json_safely(_call_llm(prompt, raw_text[:3000], True))
    return {
        "category": res.get("category", "Shpenzime"),
        "amount": float(res.get("amount", 0.0)),
        "date": res.get("date", datetime.now().strftime("%Y-%m-%d")),
        "description": res.get("merchant", "")
    }

def query_global_rag_for_claims(rag_results: str, user_query: str) -> Dict[str, Any]:
    system_prompt = f"{KOSOVO_LEGAL_BRAIN} Sugjero argumente shtesë nga praktika gjyqësore. JSON."
    return _parse_json_safely(_call_llm(system_prompt, f"RAG: {rag_results}\nQuery: {user_query}", True))

async def process_large_document_async(text: str, task_type: str = "SUMMARY") -> str:
    return generate_summary(text)

async def stream_text_async(system_prompt: str, user_prompt: str, temp: float = 0.2) -> AsyncGenerator[str, None]:
    client = get_async_deepseek_client()
    if not client: yield "[Offline]"; return
    full_system = f"{KOSOVO_LEGAL_BRAIN}\n{system_prompt}"
    try:
        stream = await client.chat.completions.create(model=OPENROUTER_MODEL, messages=[{"role": "system", "content": full_system}, {"role": "user", "content": user_prompt}], temperature=temp, stream=True)
        async for chunk in stream:
            if chunk.choices[0].delta.content: yield chunk.choices[0].delta.content
    except Exception as e:
        logger.error(f"Stream Error: {e}")
        yield f"[Gabim: {str(e)}]"

# --- END OF FILE ---