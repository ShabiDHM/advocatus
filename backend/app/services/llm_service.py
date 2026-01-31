# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - CORE INTELLIGENCE V58.1 (JURISDICTIONAL ALIGNMENT)
# 1. FIX: "Robotic Tone" cured via 'Senior Legal Auditor' persona injection.
# 2. FIX: Citation logic split into 'Substance' (Abstract) and 'Application' (Concrete).
# 3. FIX: Strict Albanian Legal Terminology (e.g., "Paditësi" instead of "Ai").
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
    """Extracts JSON from LLM response, handling markdown code blocks."""
    if not content: return {}
    try: 
        return json.loads(content)
    except:
        # Regex to find JSON inside ```json ... ``` or just {...}
        match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
        if match:
            try: return json.loads(match.group(1))
            except: pass
        # Fallback for plain text that looks like JSON
        try:
            match_loose = re.search(r'(\{.*\})', content, re.DOTALL)
            if match_loose: return json.loads(match_loose.group(1))
        except: pass
        
        logger.error(f"Failed to parse JSON content: {content[:100]}...")
        return {"raw_response": content, "error": "JSON_PARSE_FAILED"}

def _call_llm(system_prompt: str, user_prompt: str, json_mode: bool = False, temp: float = 0.1) -> Optional[str]:
    """Standardized synchronous LLM call wrapper."""
    client = get_deepseek_client()
    if not client: 
        logger.error("DeepSeek Client not initialized (Missing Key).")
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

# --- KOSOVO LEGAL MASTER RULEBOOK (ENHANCED) ---
KOSOVO_LEGAL_PERSONA = """
ROLI: Ti je 'Senior Legal Auditor' (Auditues Ligjor i Lartë) me 20 vite përvojë në Gjykatat e Kosovës.
STILI I SHKRIMIT:
- Formal, Juridik, Autoritativ.
- Përdor 'Vetën e Tretë' (Gjykata, Paditësi, I Padituri). KURRË mos përdor "Unë" ose "Ne".
- Përdor terminologji standarde të LPK (Ligji i Procedurës Kontestimore).

TERMINOLOGJIA E DETYRUESHME (WHITELIST):
- Në vend të "Alimentacion" -> PËRDOR "Kontributi për mbajtje".
- Në vend të "Issue/Problem" -> PËRDOR "Çështja Kontestimore" ose "Objekti i Kontestit".
- Në vend të "Gap" -> PËRDOR "Mungesë materiale" ose "Vakuum provues".
- Në vend të "Summary" -> PËRDOR "Historiku Procedural dhe Faktik".

HIERARKIA LIGJORE (Baza për Referencë):
1. KUSHTETUTA E REPUBLIKËS SË KOSOVËS.
2. KONVENTAT NDËRKOMBËTARE (KEDNJ, Konventa për të Drejtat e Fëmijës).
3. LIGJET MATERIALE:
   - Ligji Nr. 2004/32 për Familjen (LFK).
   - Ligji Nr. 04/L-077 për Marrëdhëniet e Detyrimeve (LMD).
   - Ligji i Punës (për konteste pune).
4. LIGJET PROCEDURALE:
   - Ligji Nr. 03/L-006 për Procedurën Kontestimore (LPK).

OBJEKTIVI: Të prodhosh një analizë që mund të dorëzohet direkt në Gjykatë ose te Klienti si 'Legal Opinion'.
"""

def analyze_case_integrity(context: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_PERSONA}
    
    DETYRA: Kryej një Auditim të plotë juridik të tekstit të dhënë.
    
    UDHËZIME SPECIFIKE PËR FUSHAT E DALJES (JSON):
    
    1. "summary": 
       - Mos bëj përmbledhje shkollore. Ndërtoje si 'Hyrje e Ankesës/Padisë'.
       - Struktura: Identifikimi i Palëve -> Objekti i Kontestit (çka kërkohet) -> Baza Faktike Kryesore.
       
    2. "key_issues":
       - Identifiko saktësisht pikat ku palët nuk pajtohen.
       - Formati: "Çështja [X]: [Përshkrimi juridik]".
       
    3. "burden_of_proof" (AUDITIMI):
       - Cito Nenin 7 dhe 319 të LPK.
       - Analizo kush dështoi të sjellë prova për cilin fakt specifik.
       - Tono kritik: "Pala paditëse dështoi të provojë..." ose "Barra i kalon të paditurit sepse...".
       
    4. "legal_basis" (ARRAY):
       - Gjej nenin PRECIZ. Mos thuaj "Ligji për Familjen", thuaj "Neni 171, Paragrafi 2".
       - "relevance": Kjo fushë është kritike.
         * Pjesa 1 (SUBSTANCA): Shkruaj rregullin abstrakt (psh: 'Ndryshimi i rrethanave kërkon provë materiale...').
         * Pjesa 2 (ZBATIMI): Shpjego pse ky rregull e godet ose e mbron klientin në këtë rast specifik.
         
    5. "missing_evidence":
       - Listë e dokumenteve konkrete që mungojnë (psh: "Pasqyra bankare 12-mujore", "Vërtetimi i ATK-së").
       
    6. "strategic_analysis":
       - Jep një opinion strategjik. A duhet të shkojmë në pajtim gjyqësor apo në gjykim kryesor?
       
    JSON STRUCTURE EXPECTED:
    {{
        "summary": "Teksti i strukturuar...",
        "key_issues": ["Çështja 1...", "Çështja 2..."],
        "burden_of_proof": "Analiza e Nenit 319...",
        "legal_basis": [
            {{ "law": "Emri i Ligjit", "article": "Neni X", "relevance": "SUBSTANCA: ... ZBATIMI: ..." }}
        ],
        "strategic_analysis": "Teksti...",
        "missing_evidence": ["Dokumenti 1...", "Dokumenti 2..."],
        "action_plan": ["Hapi 1...", "Hapi 2..."],
        "success_probability": "XX% (Vlerësim i përafërt)",
        "risk_level": "I ULËT / I MESËM / I LARTË"
    }}
    """
    
    # Limiting context to prevent token overflow, generally 30-50k chars is safe for DeepSeek
    safe_context = context[:45000] if context else "Nuk ka tekst për analizë."
    
    return _parse_json_safely(_call_llm(system_prompt, safe_context, json_mode=True, temp=0.2))

# --- WAR ROOM FUNCTIONS ---

def generate_adversarial_simulation(context: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_PERSONA}
    ROLI: Avokati i Palës Kundërshtare (Djalli i Avokatit).
    QËLLIMI: Të shkatërrosh argumentet e rastit tonë.
    
    FOKUSI:
    1. A ka parashkrim (vjetërsim)?
    2. A ka mungesë legjitimiteti aktiv/pasiv?
    3. A ka kundërthënie në deklarata?
    
    JSON Output: {{ 'opponent_strategy': '...', 'weakness_attacks': ['...'], 'counter_claims': ['...'] }}"""
    return _parse_json_safely(_call_llm(system_prompt, context[:30000], True, temp=0.4))

def build_case_chronology(text: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_PERSONA}
    DETYRA: Krijo 'Kronologjinë Procesuale'.
    VETËM fakte juridike (Datat e padive, seancave, vendimeve, pagesave).
    Injoro opinionet ose ndjenjat.
    
    JSON: {{'timeline': [{{'date': 'YYYY-MM-DD (ose E panjohur)', 'event': 'Përshkrimi objektiv', 'source': 'Ku gjendet ky fakt'}}]}}"""
    return _parse_json_safely(_call_llm(system_prompt, text[:40000], True))

def detect_contradictions(text: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_PERSONA}
    DETYRA: 'Impeachment' i dëshmitarëve/palëve.
    Gjej çdo rast kur një palë ka thënë diçka ndryshe nga provat shkresore ose deklaratat e mëparshme.
    
    JSON: {{'contradictions': [{{'claim': 'Çka u tha', 'evidence': 'Çka tregon prova', 'severity': 'HIGH|MEDIUM|LOW', 'impact': 'Pasojat juridike'}}]}}"""
    return _parse_json_safely(_call_llm(system_prompt, text[:30000], True))

# --- SYSTEM UTILITIES ---

def extract_graph_data(text: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_PERSONA} Analizo entitetet (Personat, Gjykatat, Provat) dhe lidhjet mes tyre për vizualizim rrjetor. JSON Nodes/Edges."""
    return _parse_json_safely(_call_llm(system_prompt, text[:30000], True))

def analyze_financial_portfolio(data: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_PERSONA} Vepro si Ekspert Financiar Gjyqësor. Analizo të hyrat, shpenzimet dhe obligimet. JSON."""
    return _parse_json_safely(_call_llm(system_prompt, data, True))

def translate_for_client(legal_text: str) -> str:
    system_prompt = f"{KOSOVO_LEGAL_PERSONA} DETYRA: Përkthe 'Legalisht' në 'Shqip të Thjeshtë' për klientin që nuk është jurist. Ruaj kuptimin, thjeshtëso gjuhën."
    return _call_llm(system_prompt, legal_text) or "Gabim në përpunim."

def extract_deadlines(text: str) -> Dict[str, Any]:
    system_prompt = f"{KOSOVO_LEGAL_PERSONA} DETYRA: Identifiko Afatet Prekluzive dhe Instruktive (Nenet, Ankesat, Pagesat). JSON."
    return _parse_json_safely(_call_llm(system_prompt, text[:20000], True))

def perform_litigation_cross_examination(target: str, context: List[str]) -> Dict[str, Any]:
    context_str = "\n".join(context)
    system_prompt = f"{KOSOVO_LEGAL_PERSONA} DETYRA: Përgatit pyetje për marrje në pyetje (Cross-Exam) për subjektin: {target}. Bazu në mospërputhjet e dosjes."
    return _parse_json_safely(_call_llm(system_prompt, context_str[:40000], True))

def generate_summary(text: str) -> str:
    # Quick summary for lists/previews, not the deep analysis
    return _call_llm(f"{KOSOVO_LEGAL_PERSONA} Përmblidh thelbin e çështjes në 3 fjali koncize.", text[:20000]) or ""

def get_embedding(text: str) -> List[float]:
    client = get_openai_client()
    if not client: return [0.0] * 1536
    try:
        # Sanitize newlines to avoid embedding degradation
        res = client.embeddings.create(input=[text.replace("\n", " ")], model=EMBEDDING_MODEL)
        return res.data[0].embedding
    except Exception as e:
        logger.error(f"Embedding failed: {e}")
        return [0.0] * 1536

def forensic_interrogation(question: str, context_rows: List[str]) -> str:
    # RAG Response generator
    context_block = "\n---\n".join(context_rows)
    prompt = f"""{KOSOVO_LEGAL_PERSONA}
    Përgjigju pyetjes SAKTËSISHT duke u bazuar VETËM në fragmentet e mëposhtme të dosjes.
    Nëse informacioni nuk është në fragmente, thuaj "Nuk rezulton nga dokumentet e shqyrtuara".
    
    FRAGMENTS:
    {context_block}
    """
    return _call_llm(prompt, question, temp=0.0) or "Nuk ka informacion."

def categorize_document_text(text: str) -> str:
    res = _call_llm("Kategorizo dokumentin: (Padi, Përgjigje në Padi, Aktgjykim, Procesverbal, Kontratë, Provë Financiare). Kthe vetëm JSON {'category': '...'}.", text[:5000], True)
    return _parse_json_safely(res).get("category", "Të tjera")

def sterilize_legal_text(text: str) -> str:
    return sterilize_text_for_llm(text)

def extract_expense_details_from_text(raw_text: str) -> Dict[str, Any]:
    prompt = "Identifiko: {'amount': float, 'date': 'YYYY-MM-DD', 'merchant': '...', 'category': '...'}."
    res = _parse_json_safely(_call_llm(prompt, raw_text[:3000], True))
    return {
        "category": res.get("category", "Shpenzime të ndryshme"),
        "amount": float(res.get("amount", 0.0)),
        "date": res.get("date", datetime.now().strftime("%Y-%m-%d")),
        "description": res.get("merchant", "")
    }

def query_global_rag_for_claims(rag_results: str, user_query: str) -> Dict[str, Any]:
    system_prompt = f"{KOSOVO_LEGAL_PERSONA} Sugjero pretendime ose argumente shtesë bazuar në kërkimin global (Global Knowledge). JSON."
    return _parse_json_safely(_call_llm(system_prompt, f"RAG: {rag_results}\nQuery: {user_query}", True))

async def process_large_document_async(text: str, task_type: str = "SUMMARY") -> str:
    # Wrapper for potential future async pipeline enhancements
    return generate_summary(text)

async def stream_text_async(system_prompt: str, user_prompt: str, temp: float = 0.2) -> AsyncGenerator[str, None]:
    client = get_async_deepseek_client()
    if not client: 
        yield "[System Offline: API Key Missing]"
        return
        
    full_system = f"{KOSOVO_LEGAL_PERSONA}\n{system_prompt}"
    try:
        stream = await client.chat.completions.create(
            model=OPENROUTER_MODEL, 
            messages=[
                {"role": "system", "content": full_system}, 
                {"role": "user", "content": user_prompt}
            ], 
            temperature=temp, 
            stream=True
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content: 
                yield chunk.choices[0].delta.content
    except Exception as e:
        logger.error(f"Stream Error: {e}")
        yield f"[Ndërprerje: {str(e)}]"

# --- END OF FILE ---