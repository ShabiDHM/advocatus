# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - CORE INTELLIGENCE V63.0 (NATIVE ALBANIAN ENFORCEMENT)
# 1. FIX: System Prompt rewritten entirely in Albanian to force language compliance.
# 2. FEAT: "Logjika e Dominit" (Domain Logic) adapted to local context (Familjar, Penal, Civil).
# 3. FEAT: "Lista e Pazarit" (Shopping List) specifically asks for Kosovo documents (Trusti, ATK, QPS).
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

# --- INTELLIGENCE CORE: PERSONA E KOSOVËS (NATIVE) ---
# Kjo është "Truri" i sistemit. Është shkruar shqip për të garantuar output shqip.

KOSOVO_LEGAL_BRAIN = """
ROLI: Ti je "Partner Strategjik" në një studio ligjore elitare në Prishtinë.
QËLLIMI: Të bësh Auditim Ligjor, Përmbledhje Ekzekutive dhe Strategji për avokatët.

GJUHA E DALJES: VETËM SHQIP (ALBANIAN). Ndalohet anglishtja.

LOGJIKA E BRENDSHME (SI TË MENDOSH):
1. **IDENTIFIKO LLOJIN E RASTIT:**
   - A është *Familjar*? (Shkurorëzim, Alimentacion, Besim i fëmijës).
   - A është *Civil/Borxh*? (Fatura, Kontrata, Dëmshpërblim).
   - A është *Pronësor*? (Vërtetim pronësie, Pengim posedimi).
   - A është *Penal*? (Aktakuzë, Paraburgim).

2. **APLIKO RREGULLAT E FUSHËS:**
   - *NËSE FAMILJAR:* Kërko raportin e QPS (Qendrës për Punë Sociale). Kërko prova për shpenzimet e fëmijës (shkolla, mjeku). Parimi kyç: "Interesi më i lartë i fëmijës".
   - *NËSE CIVIL:* Kërko fatura të nënshkruara, libra kontabël, vërtetim nga ATK. Kërko "Parashkrimin" (Afatin e vjetërsimit).
   - *NËSE PRONËSOR:* Kërko Fletën Poseduese, Kopjen e Planit.

UDHËZIME PËR FORMATIN JSON (STRIKTE):

1. "summary" (Për Klientin/Biznesin):
   - Një përmbledhje "Narrative" e qartë.
   - Struktura: "Kush janë palët?" -> "Çka kërkohet (Objekti)?" -> "Cili është statusi aktual?".
   - Pa terma latinë të panevojshëm. Thjesht dhe pastër.

2. "burden_of_proof" (Për Avokatin - Auditimi Teknik):
   - Këtu duhet të jesh kritik.
   - Cito Nenin 7 dhe 319 të LPK (Barra e Provës).
   - Analizo: "Paditësi pretendon X, por nuk ka sjellë provën Y".
   - Përdor terma si: "Vakuum provues", "Dështim në argumentim".

3. "missing_evidence" (Për Paralegalin - Lista e Detyrave):
   - LISTO DOKUMENTET SPECIFIKE QË MUNGOJNË.
   - Mos thuaj "Prova financiare". Thuaj: "Pasqyra e llogarisë bankare (12 muaj)", "Vërtetimi i ATK-së", "Raporti i QPS-së", "Fleta Poseduese e Pronës".
   - Kjo shërben si "Checklist" për ekipin.

4. "legal_basis" (Baza Ligjore):
   - Lidh Nenin me Faktin.
   - Shembull: "Sipas Nenit 171 të LFK, ndryshimi i rrethanave duhet të provohet, gjë që nuk ka ndodhur."

5. "strategic_analysis" (Dhoma e Luftës):
   - Cila është lëvizja e radhës?
   - Shembull: "Të kërkohet hedhja e padisë për shkak të parashkrimit", "Të propozohet pajtim gjyqësor", "Të kërkohet ekspertizë financiare".

"risk_level": "I ULËT | I MESËM | I LARTË"
"success_probability": "Përqindje (psh: 60%)"
"""

def analyze_case_integrity(context: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_BRAIN}
    
    DETYRA: KRYEJ NJË AUDITIM TË PLOTË TË KËTIJ RASTI.
    
    OUTPUT I KËRKUAR (JSON):
    {{
        "summary": "String (Përmbledhja narrative në Shqip)",
        "key_issues": ["String (Çështja 1)", "String (Çështja 2)"],
        "burden_of_proof": "String (Auditimi kritik ligjor)",
        "legal_basis": [
            {{ "law": "String (Emri i Ligjit)", "article": "String (Neni)", "relevance": "String (Argumentimi)" }}
        ],
        "strategic_analysis": "String (Rekomandimi strategjik)",
        "missing_evidence": ["String (Dokumenti 1 që duhet kërkuar)", "String (Dokumenti 2)"],
        "action_plan": ["String (Hapi 1)", "String (Hapi 2)"],
        "success_probability": "String",
        "risk_level": "I ULËT | I MESËM | I LARTË"
    }}
    """
    
    safe_context = context[:45000] if context else "Nuk ka tekst."
    return _parse_json_safely(_call_llm(system_prompt, safe_context, json_mode=True, temp=0.2))

# --- WAR ROOM & SIMULATION FUNCTIONS ---

def generate_adversarial_simulation(context: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_BRAIN}
    ROLI: Avokati Kundërshtar (Djalli i Avokatit).
    DETYRA: Gjej pikat e dobëta të rastit tonë.
    JSON: {{ 
        'opponent_strategy': 'Strategjia e sulmit...', 
        'weakness_attacks': ['Pika e dobët 1', 'Pika e dobët 2'], 
        'counter_claims': ['Kundërpadia ose Pretendimi...'] 
    }}"""
    return _parse_json_safely(_call_llm(system_prompt, context[:30000], True, temp=0.4))

def build_case_chronology(text: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_BRAIN}
    DETYRA: Ndërto Kronologjinë e verifikuar (Datat, Ngjarjet, Burimi).
    JSON: {{'timeline': [{{'date': 'YYYY-MM-DD', 'event': 'Përshkrimi', 'source': 'Dokumenti'}}]}}"""
    return _parse_json_safely(_call_llm(system_prompt, text[:40000], True))

def detect_contradictions(text: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_BRAIN}
    DETYRA: Gjej Gënjeshtrat/Mospërputhjet (Impeachment).
    JSON: {{'contradictions': [{{'claim': 'Çka u tha', 'evidence': 'Çka tregon prova', 'severity': 'I LARTË', 'impact': 'Pasoja ligjore'}}]}}"""
    return _parse_json_safely(_call_llm(system_prompt, text[:30000], True))

# --- UTILITY & HELPER FUNCTIONS ---

def extract_graph_data(text: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_BRAIN} Nxjerr Entitetet dhe Lidhjet për Grafikun. JSON."""
    return _parse_json_safely(_call_llm(system_prompt, text[:30000], True))

def analyze_financial_portfolio(data: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_BRAIN} Analizo Financat (Forensic). JSON."""
    return _parse_json_safely(_call_llm(system_prompt, data, True))

def translate_for_client(legal_text: str) -> str:
    system_prompt = f"{KOSOVO_LEGAL_BRAIN} Përkthe në gjuhë të thjeshtë për klientin. Shpjego rrezikun qartë."
    return _call_llm(system_prompt, legal_text) or "Përkthimi dështoi."

def extract_deadlines(text: str) -> Dict[str, Any]:
    system_prompt = f"{KOSOVO_LEGAL_BRAIN} Gjej Afatet Ligjore (Ankesat, Parashtresat). JSON."
    return _parse_json_safely(_call_llm(system_prompt, text[:20000], True))

def perform_litigation_cross_examination(target: str, context: List[str]) -> Dict[str, Any]:
    context_str = "\n".join(context)
    system_prompt = f"{KOSOVO_LEGAL_BRAIN} Përgatit pyetje kryqëzuese për dëshmitarin: {target}."
    return _parse_json_safely(_call_llm(system_prompt, context_str[:40000], True))

def generate_summary(text: str) -> str:
    return _call_llm(f"{KOSOVO_LEGAL_BRAIN} Përmblidh në 3 pika esenciale.", text[:20000]) or ""

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
    Përgjigju VETËM bazuar në tekstin e mëposhtëm.
    DOKUMENTET:
    {context_block}
    """
    return _call_llm(prompt, question, temp=0.0) or "Nuk ka informacion."

def categorize_document_text(text: str) -> str:
    res = _call_llm("Kategorizo: (Padi, Aktgjykim, Provë, Kontratë). JSON {'category': '...'}.", text[:5000], True)
    return _parse_json_safely(res).get("category", "Të tjera")

def sterilize_legal_text(text: str) -> str:
    return sterilize_text_for_llm(text)

def extract_expense_details_from_text(raw_text: str) -> Dict[str, Any]:
    prompt = "Nxjerr të dhënat e shpenzimit: {'amount': float, 'date': 'YYYY-MM-DD', 'merchant': '...', 'category': '...'}."
    res = _parse_json_safely(_call_llm(prompt, raw_text[:3000], True))
    return {
        "category": res.get("category", "Shpenzime"),
        "amount": float(res.get("amount", 0.0)),
        "date": res.get("date", datetime.now().strftime("%Y-%m-%d")),
        "description": res.get("merchant", "")
    }

def query_global_rag_for_claims(rag_results: str, user_query: str) -> Dict[str, Any]:
    system_prompt = f"{KOSOVO_LEGAL_BRAIN} Përdor njohuri globale për të sugjeruar argumente kreative. JSON."
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