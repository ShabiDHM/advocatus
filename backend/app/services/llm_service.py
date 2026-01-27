# FILE: backend/app/services/llm_service.py
# PHOENIX PROTOCOL - CORE INTELLIGENCE V35.0 (GLOBAL RAG INTEGRATION)
# 1. ADDED: PROMPT_GLOBAL_RAG_CLAIM_SUGGESTOR prompt for Claim suggestion.
# 2. ADDED: query_global_rag_for_claims function to process RAG context into structured Claims.
# 3. STATUS: Full AI integration (Case-Specific Neo4j + Global ChromaDB RAG) is now supported.

import os
import json
import logging
import httpx
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from openai import OpenAI 

from .text_sterilization_service import sterilize_text_for_llm

logger = logging.getLogger(__name__)

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
    "query_global_rag_for_claims" # PHOENIX: New export
]

# --- CONFIGURATION ---
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") 
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat" 
EMBEDDING_MODEL = "text-embedding-3-small" 

OLLAMA_URL = os.environ.get("LOCAL_LLM_URL", "http://host.docker.internal:11434/api/generate")
OLLAMA_EMBED_URL = os.environ.get("LOCAL_LLM_EMBED_URL", "http://host.docker.internal:11434/api/embeddings")
LOCAL_MODEL_NAME = "llama3"
LOCAL_EMBED_MODEL = "nomic-embed-text"

_deepseek_client: Optional[OpenAI] = None
_openai_client: Optional[OpenAI] = None

# --- CONTEXTS ---
STRICT_CONTEXT = """
CONTEXT: Republika e Kosovës.
LAWS: Kushtetuta, LPK (Procedura Kontestimore), LFK (Familja), KPRK (Penale).
GLOBAL: UNCRC (Fëmijët), KEDNJ (Të Drejtat e Njeriut).
"""

# --- PROMPTS ---
PROMPT_SENIOR_LITIGATOR = f"""
Ti je "Avokat i Lartë" (Senior Partner).
{STRICT_CONTEXT}
DETYRA: Analizo çështjen, gjej bazën ligjore dhe strategjinë.

RREGULLAT E ANALIZËS:
1. ÇËSHTJET (ISSUES): Gjej problemet reale juridike.
2. BAZA LIGJORE (STRUKTURË STRIKTE):
   - Për çdo ligj, TI DUHET TË PËRDORËSH SAKTËSISHT këtë format me linja të reja (\\n):
   
   [Emri i Ligjit, Neni](doc://Emri i Ligjit, Neni):\\nPërmbajtja: [Përmbledhja e nenit]\\nRelevanca: [Si lidhet ky nen me faktet e rastit]
   
   - CITIMET E THJESHTA (pa Përmbajtje/Relevancë) JANË TË NDALUARA.
   - OBLIGATIVE: Cito STANDARDET GLOBALE (UNCRC, KEDNJ) me të njëjtin format.

3. STRATEGJIA: Sugjero hapa konkretë.

FORMATI I PËRGJIGJES (JSON STRICT):
{{
  "summary": "Përmbledhje e rastit...",
  "key_issues": ["Çështja 1...", "Çështja 2..."],
  "legal_basis": [
     "[Ligji për Familjen, Neni 331](doc://Ligji për Familjen, Neni 331):\\nPërmbajtja: Lejon ndryshimin e aktgjykimit nëse rrethanat kanë ndryshuar.\\nRelevanca: Rritja e pagës së palës tjetër përbën një rrethanë të re për rritjen e alimentacionit.",
     "[UNCRC, Neni 3](doc://UNCRC, Neni 3):\\nPërmbajtja: Thekson se interesi më i mirë i fëmijës është parësor.\\nRelevanca: Nevojat e fëmijës për një jetesë më të mirë tejkalojnë pretendimin e prindit për të mos paguar më shumë."
  ],
  "strategic_analysis": "Analizë e detajuar...",
  "weaknesses": ["Dobësia 1...", "Dobësia 2..."],
  "action_plan": ["Hapi 1...", "Hapi 2..."],
  "risk_level": "HIGH / MEDIUM / LOW"
}}
"""

PROMPT_FORENSIC_INTERROGATOR = """
Ti je "Forensic Financial Agent" (Agjent Financiar Ligjor).
DETYRA: Përgjigju pyetjes së avokatit duke u bazuar VETËM në rreshtat e transaksioneve të ofruara.

RREGULLAT E GJUHËS:
1. Përgjigju VETËM NË GJUHËN SHQIPE.
2. Përdor terminologji ligjore/financiare të përshtatshme për Kosovën.

RREGULLAT E ANALIZËS:
1. Përdor Referenca: Çdo fakt duhet të ketë referencë (psh: "Rreshti 54, 10 Maj").
2. Ji Agresiv: Nëse gjen shpenzime luksi (bixhoz, hotele, online), theksoji ato si "Mospërputhje me të ardhurat".
3. Llogarit Totale: Nëse kërkohet, mblidh shumat.

FORMATI I PËRGJIGJES (Markdown):
- **Përgjigje Direkte**: Përgjigja direkte në Shqip.
- **Provat**: Lista e transaksioneve (Data | Përshkrimi | Shuma).
- **Implikimi Strategjik**: Si mund të përdoret kjo në gjykatë kundër palës tjetër.

CONTEXT (TRANSACTIONS FOUND):
{context}
"""

PROMPT_FORENSIC_ACCOUNTANT = f"""
Ti je "Ekspert Financiar Forensik".
DETYRA: Analizo të dhënat financiare JSON për anomali.
GJUHA: SHQIP.
FORMATI JSON: {{ "executive_summary": "...", "anomalies": [], "trends": [], "recommendations": [] }}
"""

PROMPT_ADVERSARIAL = f"""
Ti je "Avokati i Palës Kundërshtare".
DETYRA: Gjej dobësitë në argumentet e paraqitura dhe krijoi një kundër-strategji.
GJUHA: SHQIP.
FORMATI JSON: {{ "opponent_strategy": "...", "weakness_attacks": [], "counter_claims": [], "predicted_outcome": "..." }}
"""

PROMPT_CHRONOLOGY = f"""
Ti je "Arkivist Ligjor".
DETYRA: Krijo një kronologji preçize të ngjarjeve nga teksti.
GJUHA: SHQIP.
FORMATI JSON: {{ "timeline": [ {{ "date": "...", "event": "...", "source": "..." }} ] }}
"""

PROMPT_CONTRADICTION = f"""
Ti je "Detektiv Investigues".
DETYRA: Krahaso DEKLARATAT me PROVAT. Gjej gënjeshtra.
GJUHA: SHQIP.
FORMATI JSON: {{ "contradictions": [ {{ "claim": "...", "evidence": "...", "severity": "HIGH", "impact": "..." }} ] }}
"""

PROMPT_DEADLINE = f"""
Ti je "Zyrtar i Afateve".
DETYRA: Identifiko afatet e ankesës (15 ditë për Aktgjykim, 7 për Aktvendim).
GJUHA: SHQIP.
FORMATI JSON: {{ "is_judgment": bool, "document_type": "...", "deadline_date": "YYYY-MM-DD", "action_required": "..." }}
"""

PROMPT_CROSS_EXAMINE = f"""
Ti je "Ekspert i Kryqëzimit të Fakteve".
DETYRA: Analizo DOKUMENTIN TARGET në kontekst të DOKUMENTEVE TË TJERA.
GJUHA: SHQIP.
FORMATI JSON: {{ "consistency_check": "...", "contradictions": [], "corroborations": [], "strategic_value": "HIGH/MEDIUM/LOW" }}
"""

PROMPT_TRANSLATOR = """
Ti je "Ndërmjetësues". 
DETYRA: Përkthe tekstin ligjor në gjuhë të thjeshtë për klientin.
GJUHA: SHQIP.
"""

PROMPT_CATEGORIZER = f"""
Ti je "Arkivist Ligjor".
DETYRA: Klasifiko dokumentin në njërën prej këtyre kategorive:
[ "Padi", "Aktgjykim", "Vendim", "Përgjigje në Padi", "Ankesë", "Procesverbal", "Kontratë", "Faturë", "Dëshmi", "Të tjera" ]
GJUHA: SHQIP.
FORMATI JSON: {{ "category": "..." }}
"""

# PHOENIX ENHANCED: V3 - CONTEXTUAL PLAUSIBILITY
PROMPT_EXPENSE_EXTRACTOR_V2 = f"""
Ti je "AI Forensic Auditor" për faturat e Kosovës.
OCR ka një gabim sistematik: Lexon "0" si "8" ose "6". (P.sh. 0.85 -> 8.85).

DETYRA: RIKONSTRUKTO të dhënat duke përdorur LOGJIKËN E TREGUT.

1. LOGJIKA E ÇMIMIT (Context Check):
   - Shiko artikujt: A janë "Tinimini", "Kafe", "Uje", "Buke", "Snack"? 
   - Këto kushtojnë NËN 2.00 EURO.
   - Nëse totali del 8.85€ për një snack, kjo është GABIM. Korrigjoje në 0.85€.
   - Nëse totali del 6.50€ për një kafe, kjo është GABIM. Korrigjoje në 0.50€ ose 1.50€.

2. GJETJA E TOTALIT:
   - Kërko rreshtin "TOTALI NE EURO" ose "SHUMA".
   - Numri pas tij është totali.
   - Apliko "Logjikën e Çmimit" mbi këtë numër.

3. DATA:
   - Formati DD.MM.YYYY.

4. KATEGORIA:
   - Ushqim, Zyrë, Karburant, Të tjera.

OUTPUT FORMAT (JSON ONLY):
{{
  "merchant": "Emri i Tregtarit",
  "category": "Kategoria",
  "amount": 0.00,
  "date": "YYYY-MM-DD",
  "description": "Përshkrimi"
}}
"""

# PHOENIX NEW: Global RAG Claim Suggestor Prompt
PROMPT_GLOBAL_RAG_CLAIM_SUGGESTOR = f"""
Ti je "Ekspert Ligjor Global" i Juristi.tech.
DETYRA: Bazohe VETËM në kontekstin e ofruar nga Baza e Njohurive Globale (statutet, jurisprudenca).
GJUHA: SHQIP.

Kërkesa: Gjenero një listë të strukturave ligjore dhe elementeve thelbësore (Claim Cards) që përputhen me kërkesën e përdoruesit.

RREGULLAT E OUTPUT-IT:
1. Përgjigju me një listë me pika. Çdo pikë duhet të jetë një pretendim i fortë ligjor.
2. Për çdo pikë, jep: **Titullin e Pretendimit** dhe një **Përmbajtje/Arsyetim** (deri në 2 fjali).
3. Mos bëj asnjë supozim për faktet e rastit. Përgjigju vetëm me parime ligjore të përgjithshme.

FORMATI I PËRGJIGJES (JSON STRICT):
{{
  "suggested_claims": [
    {{
      "label": "Emri i Pretendimit (P.sh., Shkelje Kontrate)",
      "content": "Elementi Thelbësor i parë i kërkuar nga ligji është... [Cito Nenin]"
    }},
    {{
      "label": "Emri i Pretendimit 2 (P.sh., Mosplotësimi i Kujdesit Prindëror)",
      "content": "Interesi më i mirë i fëmijës kërkon... [Cito Nenin]"
    }}
  ]
}}
"""

def get_deepseek_client() -> Optional[OpenAI]:
    global _deepseek_client
    if not _deepseek_client and DEEPSEEK_API_KEY:
        try: _deepseek_client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=OPENROUTER_BASE_URL)
        except Exception as e: logger.error(f"DeepSeek Init Failed: {e}")
    return _deepseek_client

def get_openai_client() -> Optional[OpenAI]:
    """Specific client for Embeddings if using standard OpenAI models"""
    global _openai_client
    if not _openai_client and OPENAI_API_KEY:
        try: _openai_client = OpenAI(api_key=OPENAI_API_KEY)
        except Exception as e: logger.error(f"OpenAI Init Failed: {e}")
    return _openai_client

def _parse_json_safely(content: str) -> Dict[str, Any]:
    try: return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
        if match:
            try: return json.loads(match.group(1))
            except: pass
        start, end = content.find('{'), content.rfind('}')
        if start != -1 and end != -1:
            try: return json.loads(content[start:end+1])
            except: pass
        return {}

def _call_llm(system_prompt: str, user_prompt: str, json_mode: bool = False, temp: float = 0.2) -> Optional[str]:
    client = get_deepseek_client()
    if client:
        try:
            kwargs = {
                "model": OPENROUTER_MODEL, 
                "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}], 
                "temperature": temp
            }
            if json_mode: kwargs["response_format"] = {"type": "json_object"}
            res = client.chat.completions.create(**kwargs)
            return res.choices[0].message.content
        except: pass
    
    try:
        with httpx.Client(timeout=60.0) as c:
            res = c.post(OLLAMA_URL, json={
                "model": LOCAL_MODEL_NAME, "prompt": f"{system_prompt}\nUSER: {user_prompt}", 
                "stream": False, "format": "json" if json_mode else None, "options": {"temperature": temp}
            })
            return res.json().get("response", "")
    except: return None

# --- NEW: VECTORIZATION SUPPORT ---

def get_embedding(text: str) -> List[float]:
    """
    Generates a vector embedding for the provided text.
    Prioritizes OpenAI (text-embedding-3-small) for quality, falls back to Ollama.
    """
    clean_text = text.replace("\n", " ")
    
    client = get_openai_client()
    if client:
        try:
            return client.embeddings.create(input=[clean_text], model=EMBEDDING_MODEL).data[0].embedding
        except Exception as e:
            logger.warning(f"OpenAI Embedding failed, falling back: {e}")

    try:
        with httpx.Client(timeout=10.0) as c:
            res = c.post(OLLAMA_EMBED_URL, json={
                "model": LOCAL_EMBED_MODEL,
                "prompt": clean_text
            })
            data = res.json()
            if "embedding" in data: return data["embedding"]
    except Exception:
        pass
        
    logger.error("All embedding methods failed. Returning zero-vector.")
    return [0.0] * 1536 

# --- PUBLIC FUNCTIONS ---

def sterilize_legal_text(text: str) -> str:
    """Wrapper for the core sterilization function."""
    return sterilize_text_for_llm(text)

def forensic_interrogation(question: str, context_rows: List[str]) -> str:
    context_str = "\n".join(context_rows)
    prompt_filled = PROMPT_FORENSIC_INTERROGATOR.replace("{context}", context_str)
    result = _call_llm(prompt_filled, question, False, temp=0.3)
    return result or "Sistemi nuk mundi të analizojë të dhënat."

def analyze_financial_portfolio(data: str) -> Dict[str, Any]:
    result = _call_llm(PROMPT_FORENSIC_ACCOUNTANT, data, True)
    return _parse_json_safely(result or "{}")

def analyze_case_integrity(text: str) -> Dict[str, Any]:
    clean = sterilize_text_for_llm(text[:35000])
    result = _call_llm(PROMPT_SENIOR_LITIGATOR, clean, True)
    return _parse_json_safely(result or "{}")

def generate_adversarial_simulation(text: str) -> Dict[str, Any]:
    clean = sterilize_text_for_llm(text[:25000])
    result = _call_llm(PROMPT_ADVERSARIAL, clean, True, temp=0.4)
    return _parse_json_safely(result or "{}")

def build_case_chronology(text: str) -> Dict[str, Any]:
    clean = sterilize_text_for_llm(text[:30000])
    result = _call_llm(PROMPT_CHRONOLOGY, clean, True, temp=0.1)
    return _parse_json_safely(result or "{}")

def detect_contradictions(text: str) -> Dict[str, Any]:
    clean = sterilize_text_for_llm(text[:30000])
    result = _call_llm(PROMPT_CONTRADICTION, clean, True, temp=0.1)
    return _parse_json_safely(result or "{}")

def extract_deadlines(text: str) -> Dict[str, Any]:
    clean = sterilize_text_for_llm(text[:5000]) 
    result = _call_llm(PROMPT_DEADLINE, clean, True, temp=0.0)
    return _parse_json_safely(result or "{}")

def perform_litigation_cross_examination(target_text: str, context_summaries: List[str]) -> Dict[str, Any]:
    clean_target = sterilize_text_for_llm(target_text[:15000])
    context_block = "\n".join(context_summaries)
    prompt = f"TARGET DOCUMENT CONTENT:\n{clean_target}\n\nCONTEXT (OTHER DOCUMENTS):\n{context_block}"
    result = _call_llm(PROMPT_CROSS_EXAMINE, prompt, True, temp=0.2)
    return _parse_json_safely(result or "{}")

def translate_for_client(legal_text: str) -> str:
    result = _call_llm(PROMPT_TRANSLATOR, legal_text, False, temp=0.5)
    return result or "Gabim në përkthim."

def generate_summary(text: str) -> str:
    clean = sterilize_text_for_llm(text[:15000])
    result = _call_llm("Përmblidh dokumentin.", clean, False)
    return result or ""

def extract_graph_data(text: str) -> Dict[str, Any]:
    return {"entities": [], "relations": []}

def categorize_document_text(text: str) -> str:
    clean = sterilize_text_for_llm(text[:4000])
    result = _call_llm(PROMPT_CATEGORIZER, clean, True, temp=0.0)
    parsed = _parse_json_safely(result or "{}")
    return parsed.get("category", "Të tjera")

# PHOENIX NEW: OCR Repair Logic Implemented
def extract_expense_details_from_text(raw_text: str) -> Dict[str, Any]:
    """
    Extracts structured expense data (Category, Amount, Date) from raw receipt text.
    V2: Uses Forensic Prompt to repair OCR artifacts.
    """
    if not raw_text or len(raw_text) < 5:
        return {"category": "", "amount": 0, "date": "", "description": ""}
        
    # We DO NOT sterilize too aggressively for receipts, as symbols like '.' and ',' are vital.
    # We only limit length.
    clean_text = raw_text[:2500]
    
    # Pass current date for context
    current_date = datetime.now().strftime("%Y-%m-%d")
    context_prompt = f"DATA SOT: {current_date}\n\nTEKSTI I FATURËS (RAW OCR):\n{clean_text}"
    
    # Call LLM with NEW Forensic Prompt
    result = _parse_json_safely(_call_llm(PROMPT_EXPENSE_EXTRACTOR_V2, context_prompt, True, temp=0.1) or "{}")
    
    # Extract and validate amount
    amount = result.get("amount", 0.0)
    description = result.get("description", "")
    merchant = result.get("merchant", "")
    category = result.get("category", "").lower()
    
    # Construct description from Merchant if available
    if merchant and (not description or description == "Blerje"):
        description = f"Blerje: {merchant}"
    
    # --- PHOENIX SANITY CHECK ---
    # Double check small amounts if LLM missed it
    if isinstance(amount, (int, float)):
        amount = float(amount)
        # If amount is roughly 8.xx or 6.xx and item is clearly small
        is_small_item = any(x in category or x in description.lower() for x in ['ushqim', 'kafe', 'uj', 'snack', 'tinimini', 'bum', 'tea', 'caj'])
        
        if amount > 5.0 and amount < 10.0 and is_small_item:
            # Check if it looks like a digit swap (e.g. 8.85 -> 0.85)
            # We assume it's an OCR error if the item is cheap
            logger.warning(f"Sanity Check: Correcting suspicious amount {amount} for small item to {amount - 8.0}")
            if str(amount).startswith('8.'):
                amount = amount - 8.0
            elif str(amount).startswith('6.'):
                amount = amount - 6.0

    return {
        "category": result.get("category", "Të tjera"),
        "amount": round(float(amount), 2),
        "date": result.get("date", current_date),
        "description": description
    }

def query_global_rag_for_claims(rag_results: str, user_query: str) -> Dict[str, Any]:
    """
    Analyzes RAG context (from ChromaDB/GKB) and generates structured Claim suggestions.
    
    :param rag_results: The context returned by the RAG search service (e.g., related statutes).
    :param user_query: The user's original query (e.g., "start a divorce case").
    :return: Structured JSON of suggested Claim Cards.
    """
    
    system_prompt = PROMPT_GLOBAL_RAG_CLAIM_SUGGESTOR
    user_prompt = f"KËRKESA E PËRDORUESIT: {user_query}\n\nKONTEKSTI NGA BAZA GLOBALE:\n{rag_results}"
    
    # Increase temperature slightly for creativity in naming/structuring claims
    result = _call_llm(system_prompt, user_prompt, True, temp=0.5) 
    
    return _parse_json_safely(result or "{}")