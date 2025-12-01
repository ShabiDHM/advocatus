# FILE: backend/app/services/analysis_service.py
# PHOENIX PROTOCOL - ANALYSIS SERVICE V4.1
# 1. ENGINE: Upgraded to DeepSeek V3 (via OpenRouter) for deep reasoning.
# 2. RAG: Integrates Document Findings + Knowledge Base (Laws).
# 3. PROMPT: Specific instruction to act as a 'Kosovo Senior Litigator'.

import os
import json
import structlog
import httpx 
from typing import List, Dict, Any, Optional
from pymongo.database import Database
from bson import ObjectId
from openai import OpenAI

# PHOENIX IMPORTS: Access the Knowledge Base & Vectors
from .vector_store_service import query_legal_knowledge_base
from .embedding_service import generate_embedding

logger = structlog.get_logger(__name__)

# --- CONFIGURATION (OPENROUTER/DEEPSEEK) ---
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY") 
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat" 

# Local Fallback
LOCAL_LLM_URL = os.environ.get("LOCAL_LLM_URL", "http://local-llm:11434/api/chat")
LOCAL_MODEL_NAME = "llama3"

def _get_case_context(db: Database, case_id: str) -> str:
    """
    Compiles all document summaries, findings, and deadlines into a single context string.
    """
    try:
        documents = list(db.documents.find({"case_id": ObjectId(case_id)}))
        context_buffer = []
        
        for doc in documents:
            doc_id = str(doc["_id"])
            name = doc.get("file_name", "Unknown")
            summary = doc.get("summary", "No summary available.")
            
            # Fetch findings related to this doc
            findings = list(db.findings.find({"document_id": ObjectId(doc_id)}))
            findings_text = "\n".join([f"- {f.get('finding_text')}" for f in findings])
            
            # Fetch deadlines
            deadlines = list(db.calendar_events.find({"document_id": doc_id}))
            deadlines_text = "\n".join([f"- {d.get('start_date')}: {d.get('title')}" for d in deadlines])

            doc_context = f"""
            === DOKUMENTI: {name} ===
            PËRMBLEDHJE: {summary}
            GJETJET KYÇE: {findings_text}
            AFATET: {deadlines_text}
            ------------------------------------------------
            """
            context_buffer.append(doc_context)
            
        return "\n".join(context_buffer)
    except Exception as e:
        logger.error("analysis.context_build_failed", error=str(e))
        return ""

def _fetch_relevant_laws(case_text: str) -> str:
    """
    Generates a vector for the case summary and finds relevant laws in ChromaDB.
    """
    try:
        # Create a "Search Query" from the case summary (first 1000 chars)
        query_text = case_text[:1500].replace("\n", " ")
        embedding = generate_embedding(query_text)
        
        if not embedding: return ""

        # Find top 5 most relevant laws from Knowledge Base
        laws = query_legal_knowledge_base(embedding, n_results=5)
        
        if not laws: return ""

        law_buffer = ["=== BAZA LIGJORE RELEVANTE (NGA LIGJET E KOSOVËS) ==="]
        for law in laws:
            source = law.get('document_name', 'Ligj')
            text = law.get('text', '')[:1500] 
            law_buffer.append(f"BURIMI: {source}\nTEKSTI: {text}\n---")
            
        return "\n".join(law_buffer)
    except Exception as e:
        logger.warning(f"Failed to fetch relevant laws: {e}")
        return ""

def _generate_static_fallback(error_msg: str) -> Dict[str, Any]:
    return {
        "summary_analysis": f"⚠️ Analiza e thellë nuk mund të gjenerohej ({error_msg}).",
        "contradictions": ["Kontrolloni manualisht dokumentet."],
        "risks": ["Sistemi AI nuk është i qasshëm momentalisht."],
        "missing_info": []
    }

def _call_local_llm(system_prompt: str, user_prompt: str) -> Optional[Dict[str, Any]]:
    logger.info("🔄 Switching to LOCAL LLM (Ollama)...")
    try:
        payload = {
            "model": LOCAL_MODEL_NAME,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.1} # Strict for JSON
        }
        with httpx.Client(timeout=120.0) as client:
            response = client.post(LOCAL_LLM_URL, json=payload)
            response.raise_for_status()
            data = response.json()
            content = data.get("message", {}).get("content", "")
            return json.loads(content)
    except Exception as e:
        logger.error("analysis.local_llm_failed", error=str(e))
        return None

def cross_examine_case(db: Database, case_id: str) -> Dict[str, Any]:
    log = logger.bind(case_id=case_id)
    
    # 1. Prepare Case Context (Docs + Findings + Dates)
    case_context = _get_case_context(db, case_id)
    if not case_context:
        return {"error": "Nuk ka mjaftueshëm të dhëna në dosje për analizë."}

    # 2. Fetch Legal Grounding (RAG Search)
    relevant_laws = _fetch_relevant_laws(case_context)
    
    # 3. Define Deep Reasoning Prompt (Kosovo Context)
    system_prompt = """
    Ti je "Juristi AI", një Avokat i Lartë (Senior Litigator) i specializuar në legjislacionin e Republikës së Kosovës.
    
    DETYRA:
    Analizo dosjen e mëposhtme në mënyrë kritike. Identifiko rreziqet, kontradiktat dhe shkeljet ligjore.
    
    UDHËZIME PËR ANALIZËN:
    1. KONTRADIKTA: Krahaso dokumentet me njëri-tjetrin. A ka mospërputhje datash, shumash ose faktesh?
    2. RREZIQE LIGJORE: Krahaso faktet me 'BAZA LIGJORE RELEVANTE'. A ka shkelje ligjore?
    3. MUNGESAT: Çfarë dokumentesh kyçe mungojnë për të fituar rastin?

    Përgjigju VETËM në format JSON strikt:
    {
      "summary_analysis": "Një paragraf përmbledhës profesional dhe i thellë.",
      "contradictions": ["Lista e mospërputhjeve të gjetura..."],
      "risks": ["Lista e rreziqeve ligjore (cito ligjin nëse mundesh)..."],
      "missing_info": ["Lista e informacioneve ose dokumenteve që mungojnë..."]
    }
    Përgjigju në GJUHËN SHQIPE standarde.
    """
    
    user_prompt = f"""
    {relevant_laws}
    
    === DOSJA E RASTIT PËR ANALIZË ===
    {case_context[:25000]} 
    """

    # --- TIER 1: OPENROUTER / DEEPSEEK V3 ---
    if DEEPSEEK_API_KEY:
        try:
            client = OpenAI(
                api_key=DEEPSEEK_API_KEY,
                base_url=OPENROUTER_BASE_URL
            )
            
            completion = client.chat.completions.create(
                model=OPENROUTER_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2, # Low temp for analytical precision
                response_format={"type": "json_object"},
                extra_headers={
                    "HTTP-Referer": "https://juristi.tech", 
                    "X-Title": "Juristi AI Analysis"
                }
            )
            
            content = completion.choices[0].message.content
            if content:
                log.info("analysis.success_tier_1_deepseek")
                return json.loads(content)

        except Exception as e:
            log.warning("analysis.deepseek_failed", error=str(e))
            # Fall through to Local LLM

    # --- TIER 2: LOCAL LLM (OLLAMA) ---
    local_result = _call_local_llm(system_prompt, user_prompt)
    if local_result:
        log.info("analysis.success_tier_2_local")
        local_result["summary_analysis"] = "[Mode: Backup AI] " + local_result.get("summary_analysis", "")
        return local_result

    # --- TIER 3: FALLBACK ---
    return _generate_static_fallback("Shërbimi AI momentalisht i padisponueshëm")