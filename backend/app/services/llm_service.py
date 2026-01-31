# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - CORE INTELLIGENCE V65.0 (PERSONA-DRIVEN ZERO-TRUST RAG)
# 1. ARCHITECTURE: Re-architected `analyze_case_integrity` for Persona-Driven output.
#    - Generates distinct, actionable sections for Business Owners, Paralegals, and Lawyers.
# 2. ACCURACY: Implemented Zero-Trust RAG.
#    - The AI is now explicitly forbidden from using external knowledge, forcing it to rely
#      solely on the case facts and legal context provided by the vector store.
# 3. UTILITY: The new JSON output is more structured, predictable, and directly
#    maps to the professional roles of the users, increasing the value of the analysis.

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
ROLI: Ti je 'Senior Legal Partner' në një firmë ligjore prestigjioze në Kosovë.
DETYRA: Të prodhosh analiza ligjore të nivelit të Gjykatës Supreme: të sakta, të bazuara në fakte dhe strategjike.
GJUHA: VETËM SHQIP.

STRUKTURA E ARGUMENTIMIT (Për BAZËN LIGJORE):
Kur citon një ligj, ndiq KËTË STRUKTURË FIKSE ME 3 PJESË:
1. **PARIMI:** Shpjego qartë parimin që përcakton neni. (P.sh: "Ky nen përcakton se barra e provës bie mbi palën që pretendon një fakt.")
2. **LIDHJA ME RASTIN:** Apliko parimin drejtpërdrejt te faktet e rastit. (P.sh: "Në rastin konkret, pala paditëse pretendoi ekzistencën e një borxhi, por nuk ofroi asnjë dëshmi mbështetëse si faturë apo kontratë.")
3. **CITIM:** Përdor formatin zyrtar në fund. (P.sh: [Ligji Nr. 03/L-006 për Procedurën Kontestimore, Neni 7])

LOGJIKA E DOMINIT (Rregullat Themelore):
1. RASTE FAMILJARE (Ligji Nr. 2004/32): Fokusi absolut është "Interesi më i lartë i fëmijës". Dokumentet kyçe janë raporti i QPS-së, vërtetimet e pagave dhe provat për shpenzimet e fëmijës.
2. RASTE DETYRIMESH (Ligji Nr. 04/L-077): Parimi udhëheqës është "Pacta Sunt Servanda" (kontratat janë ligj për palët). Dokumentet kyçe janë kontrata, faturat dhe komunikimet mes palëve.
3. RASTE PROCEDURALE (Ligji Nr. 03/L-006 - LPK): Koncepti kyç është "Barra e Provës" (Neni 7, 319). Kush pretendon, duhet të provojë.
"""

def analyze_case_integrity(context: str) -> Dict[str, Any]:
    """
    Performs a Persona-Driven, Zero-Trust RAG analysis of a legal case.
    The AI is strictly commanded to use only the provided context and structure
    its output for different professional roles (Business, Paralegal, Lawyer).
    """
    system_prompt = f"""{KOSOVO_LEGAL_BRAIN}

    --- URDHËR I PADISKUTUESHËM: ZERO-TRUST RAG ---
    1.  ANALIZA JOTE DUHET TË BAZOHET **VETËM DHE EKSKLUZIVISHT** NË KONTEKSTIN E OFRUAR NË USER PROMPT, TË CILIN E GJEN NËN TITUJT `=== KONTEKSTI I RASTIT ===` DHE `=== BAZA LIGJORE ===`.
    2.  TË NDALOHET RREPTËSISHT PËRDORIMI I ÇDO NJOHURIE TË JASHTME.
    3.  NËSE KONTEKSTI NUK KA INFORMACION TË MJAFTUESHËM PËR TË PLOTËSUAR NJË FUSHË TË CAKTUAR TË JSON-it, SHKRUAJ VETËM: "Konteksti i ofruar është i pamjaftueshëm."
    
    --- DETYRA: KRIJO NJË ANALIZË STRATEGJIKE TË STRUKTURUAR PËR PERSONA TË NDRYSHËM ---
    
    Prodhoni një objekt JSON të pastër me strukturën dhe përmbajtjen e mëposhtme:

    {{
      "executive_summary": "...", // PËR PRONARIN E BIZNESIT: Shpjego rastin dhe konkluzionin në gjuhë të thjeshtë, pa zhargon ligjor. Fokuso te rezultati praktik. Bazoje këtë VETËM në `KONTEKSTI I RASTIT`.
      "paralegal_checklist": {{
        "missing_evidence": ["...", "..."], // PËR PARALEGALIN: Krijo një listë të dokumenteve konkrete që mungojnë. Bazoje në `KONTEKSTI I RASTIT` dhe `LOGJIKA E DOMINIT`. Përdor emra realë të dokumenteve (p.sh., 'Certifikata e pronësisë nga Kadastri', 'Raporti i QPS-së').
        "action_plan": ["...", "..."] // PËR PARALEGALIN: Listo 3-5 hapat e ardhshëm, konkretë dhe të veprueshëm në procesin ligjor.
      }},
      "legal_audit": {{
        "burden_of_proof": "...", // PËR AVOKATIN: Kryej një audit të thellë forensic. Apliko Nenet 7 & 319 të LPK-së te faktet nga `KONTEKSTI I RASTIT`. Identifiko saktësisht kush ka dështuar të provojë pretendimet e tij dhe ku ekziston një 'Vakuum provues'.
        "legal_basis": [ // PËR AVOKATIN: Për çdo ligj të rëndësishëm nga `BAZA LIGJORE`, krijo një objekt. Apliko STRUKTURËN E ARGUMENTIMIT ME 3 PJESË pa dështuar.
          {{
            "law": "Emri i plotë i ligjit",
            "article": "Neni përkatës",
            "relevance": "PARIMI: [Shpjego nenin]... LIDHJA ME RASTIN: [Apliko nenin te faktet nga `KONTEKSTI I RASTIT`]... CITIM: [Formati zyrtar i citimit]"
          }}
        ]
      }},
      "strategic_recommendation": {{ // PËR AVOKATIN DHE KLIENTIN
        "recommendation_text": "...", // Cila është lëvizja strategjike më e mençur: Gjyq, Pajtim, apo Mediatim? Argumento prerazi pse.
        "success_probability": "XX%", // Vlerësimi i mundësisë për sukses në përqindje.
        "risk_level": "I ULËT | I MESËM | I LARTË" // Zgjidh një nga tre nivelet e rrezikut.
      }}
    }}
    """
    
    # Use a generous context window as the RAG context can be large.
    safe_context = context[:100000] if context else "Konteksti nuk u ofrua."
    
    # The frontend expects the old keys. We will run the new analysis and then map the results
    # to the old structure for backward compatibility without breaking the UI.
    new_analysis = _parse_json_safely(_call_llm(system_prompt, safe_context, json_mode=True, temp=0.2))

    if not new_analysis or "executive_summary" not in new_analysis:
        return {
            "summary": "Analiza dështoi. Ju lutem provoni përsëri ose kontrolloni cilësinë e dokumenteve.",
            "key_issues": [], "legal_basis": [], "strategic_analysis": "Nuk ka.", "burden_of_proof": "Nuk ka.",
            "missing_evidence": [], "action_plan": [], "risk_level": "I LARTË", "success_probability": "0%"
        }

    # --- MAPPING TO OLD FRONTEND STRUCTURE (Adapter Pattern) ---
    # This ensures the frontend continues to work without needing immediate changes.
    legal_audit = new_analysis.get("legal_audit", {})
    paralegal_checklist = new_analysis.get("paralegal_checklist", {})
    strategic_rec = new_analysis.get("strategic_recommendation", {})

    # The new `legal_basis` is already in the correct format.
    # We can add key issues if needed, but the new structure is more robust.
    # For now, we derive it from the summary or leave it empty.
    
    return {
        "summary": new_analysis.get("executive_summary", "Përmbledhja nuk u gjenerua."),
        "key_issues": [], # This can be phased out or populated from analysis if needed.
        "burden_of_proof": legal_audit.get("burden_of_proof", "Analiza e barrës së provës nuk u gjenerua."),
        "legal_basis": legal_audit.get("legal_basis", []),
        "strategic_analysis": strategic_rec.get("recommendation_text", "Rekomandimi strategjik nuk u gjenerua."),
        "missing_evidence": paralegal_checklist.get("missing_evidence", []),
        "action_plan": paralegal_checklist.get("action_plan", []),
        "success_probability": strategic_rec.get("success_probability", "N/A"),
        "risk_level": strategic_rec.get("risk_level", "I MESËM")
    }


# --- WAR ROOM & SIMULATION FUNCTIONS ---

def generate_adversarial_simulation(context: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_BRAIN}
    ROLI: Ti je Avokati i Palës Kundërshtare. Detyra jote është të jesh agresiv, i pamëshirshëm dhe të gjesh çdo dobësi në rastin tonë.
    DETYRA: Bazoje analizën tënde VETËM në kontekstin e ofruar. Identifiko tri pikat tona më të dobëta dhe ndërto kundër-argumente të fuqishme për secilën.
    
    OUTPUT JSON: 
    {{ 
        "opponent_strategy": "Përmbledhja e strategjisë së tyre kryesore në një paragraf.", 
        "weakness_attacks": [
            "Sulmi #1: Përshkrimi i sulmit të tyre ndaj dobësisë sonë të parë.",
            "Sulmi #2: Përshkrimi i sulmit të tyre ndaj dobësisë sonë të dytë."
        ], 
        "counter_claims": [
            "Pretendimi #1: Një kundër-pretendim që ata mund ta ngrenë.",
            "Pretendimi #2: Një kundër-pretendim tjetër."
        ]
    }}"""
    return _parse_json_safely(_call_llm(system_prompt, context[:30000], True, temp=0.4))

def build_case_chronology(text: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_BRAIN}
    DETYRA: Ekstrakto një kronologji të verifikuar të ngjarjeve nga teksti. Për çdo ngjarje, identifiko datën dhe burimin (emrin e dokumentit). Injoro datat pa ngjarje të qarta.
    
    OUTPUT JSON: 
    {{
        "timeline": [
            {{
                "date": "YYYY-MM-DD", 
                "event": "Përshkrimi i saktë i ngjarjes.", 
                "source": "Emri i dokumentit nga i cili është nxjerrë informacioni."
            }}
        ]
    }}"""
    return _parse_json_safely(_call_llm(system_prompt, text[:40000], True))

def detect_contradictions(text: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_BRAIN}
    DETYRA: Vepro si një hetues. Skano tekstin për të gjetur mospërputhje ose kontradikta direkte mes deklaratave dhe provave.
    
    OUTPUT JSON: 
    {{
        "contradictions": [
            {{
                "claim": "Deklarata ose pretendimi i bërë nga njëra palë.", 
                "evidence": "Fakti ose prova nga një dokument tjetër që e kundërshton atë.", 
                "severity": "I LARTË | I MESËM | I ULËT", 
                "impact": "Shpjegim i shkurtër se si kjo kontradiktë ndikon në besueshmërinë e palës."
            }}
        ]
    }}"""
    return _parse_json_safely(_call_llm(system_prompt, text[:30000], True))

# --- UTILITY & HELPER FUNCTIONS ---

def extract_graph_data(text: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_BRAIN} Nxjerr Entitetet (Persona, Kompani, Vende) dhe Lidhjet mes tyre. JSON: {{'nodes':[], 'edges':[]}}."""
    return _parse_json_safely(_call_llm(system_prompt, text[:30000], True))

def analyze_financial_portfolio(data: str) -> Dict[str, Any]:
    system_prompt = f"""{KOSOVO_LEGAL_BRAIN} Analizo të dhënat financiare. JSON."""
    return _parse_json_safely(_call_llm(system_prompt, data, True))

def translate_for_client(legal_text: str) -> str:
    system_prompt = f"{KOSOVO_LEGAL_BRAIN} Përkthe këtë tekst ligjor në gjuhë të thjeshtë që e kupton një klient pa njohuri juridike."
    return _call_llm(system_prompt, legal_text) or "Përkthimi dështoi."

def extract_deadlines(text: str) -> Dict[str, Any]:
    system_prompt = f"{KOSOVO_LEGAL_BRAIN} Gjej të gjitha Afatet Ligjore (p.sh., për ankesë, përgjigje). JSON: {{'deadlines':[]}}."
    return _parse_json_safely(_call_llm(system_prompt, text[:20000], True))

def perform_litigation_cross_examination(target: str, context: List[str]) -> Dict[str, Any]:
    context_str = "\n".join(context)
    system_prompt = f"{KOSOVO_LEGAL_BRAIN} Përgatit pyetje kryqëzuese për dëshmitarin/palën: {target}. JSON: {{'questions':[]}}."
    return _parse_json_safely(_call_llm(system_prompt, context_str[:40000], True))

def generate_summary(text: str) -> str:
    return _call_llm(f"{KOSOVO_LEGAL_BRAIN} Krijo një përmbledhje ekzekutive në 3 pika kryesore.", text[:20000]) or ""

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
    Përgjigju pyetjes VETËM duke përdorur informacionin nga dokumentet e mëposhtme:
    {context_block}
    """
    return _call_llm(prompt, question, temp=0.0) or "Nuk ka informacion në dokumentet e ofruara."

def categorize_document_text(text: str) -> str:
    res = _call_llm("Kategorizo këtë tekst: (Padi, Aktgjykim, Provë materiale, Kontratë, Të tjera). Kthe vetëm një fjalë në JSON {'category': '...'}.", text[:5000], True)
    return _parse_json_safely(res).get("category", "Të tjera")

def sterilize_legal_text(text: str) -> str:
    return sterilize_text_for_llm(text)

def extract_expense_details_from_text(raw_text: str) -> Dict[str, Any]:
    prompt = "Nga ky tekst, nxirr shpenzimin në formatin JSON: {'amount': float, 'date': 'YYYY-MM-DD', 'merchant': 'emri', 'category': 'kategoria'}."
    res = _parse_json_safely(_call_llm(prompt, raw_text[:3000], True))
    return {
        "category": res.get("category", "Shpenzime"),
        "amount": float(res.get("amount", 0.0)),
        "date": res.get("date", datetime.now().strftime("%Y-%m-%d")),
        "description": res.get("merchant", "")
    }

def query_global_rag_for_claims(rag_results: str, user_query: str) -> Dict[str, Any]:
    system_prompt = f"{KOSOVO_LEGAL_BRAIN} Bazuar në këto fragmente nga praktika gjyqësore, sugjero argumente shtesë. JSON: {{'suggestions':[]}}."
    return _parse_json_safely(_call_llm(system_prompt, f"RAG Results: {rag_results}\nQuery: {user_query}", True))

async def process_large_document_async(text: str, task_type: str = "SUMMARY") -> str:
    return generate_summary(text)

async def stream_text_async(system_prompt: str, user_prompt: str, temp: float = 0.2) -> AsyncGenerator[str, None]:
    client = get_async_deepseek_client()
    if not client: yield "[SISTEMI OFFLINE]"; return
    full_system = f"{KOSOVO_LEGAL_BRAIN}\n{system_prompt}"
    try:
        stream = await client.chat.completions.create(model=OPENROUTER_MODEL, messages=[{"role": "system", "content": full_system}, {"role": "user", "content": user_prompt}], temperature=temp, stream=True)
        async for chunk in stream:
            if chunk.choices[0].delta.content: yield chunk.choices[0].delta.content
    except Exception as e:
        logger.error(f"Stream Error: {e}")
        yield f"[GABIM NË SISTEM: {str(e)}]"

# --- END OF FILE ---