# FILE: backend/app/services/analysis_service.py
# PHOENIX PROTOCOL - DEEP LEGAL ANALYSIS
# 1. LEGAL RAG: Fetches relevant laws from Knowledge Base based on case context.
# 2. CITATION: Instructs AI to cite specific articles from the fetched laws.
# 3. HYBRID: Maintains Cloud -> Local fallback.

import os
import json
import structlog
import httpx 
from typing import List, Dict, Any, Optional
from pymongo.database import Database
from bson import ObjectId
from groq import Groq

# PHOENIX IMPORTS: Access the Knowledge Base & Vectors
from .vector_store_service import query_legal_knowledge_base
from .embedding_service import generate_embedding

logger = structlog.get_logger(__name__)

# Configuration
LOCAL_LLM_URL = os.environ.get("LOCAL_LLM_URL", "http://local-llm:11434/api/chat")
LOCAL_MODEL_NAME = "llama3"

def _get_case_context(db: Database, case_id: str) -> str:
    try:
        documents = list(db.documents.find({"case_id": ObjectId(case_id)}))
        context_buffer = []
        
        for doc in documents:
            doc_id = str(doc["_id"])
            name = doc.get("file_name", "Unknown")
            summary = doc.get("summary", "No summary available.")
            
            findings = list(db.findings.find({"document_id": ObjectId(doc_id)}))
            findings_text = "\n".join([f"- {f.get('finding_text')}" for f in findings])
            
            deadlines = list(db.calendar_events.find({"document_id": doc_id}))
            deadlines_text = "\n".join([f"- {d.get('start_date')}: {d.get('title')}" for d in deadlines])

            doc_context = f"""
            === DOKUMENTI: {name} ===
            PËRMBLEDHJE: {summary}
            GJETJET KYÇE: {findings_text}
            AFATET: {deadlines_text}
            """
            context_buffer.append(doc_context)
            
        return "\n\n".join(context_buffer)
    except Exception as e:
        logger.error("analysis.context_build_failed", error=str(e))
        return ""

def _fetch_relevant_laws(case_text: str) -> str:
    """
    Generates a vector for the case summary and finds relevant laws in ChromaDB.
    """
    try:
        # Create a "Search Query" from the case summary (first 1000 chars)
        query_text = case_text[:1000].replace("\n", " ")
        embedding = generate_embedding(query_text)
        
        if not embedding: return ""

        # Find top 5 most relevant laws
        laws = query_legal_knowledge_base(embedding, n_results=5)
        
        if not laws: return ""

        law_buffer = ["=== BAZA LIGJORE RELEVANTE (NGA DATABAZA) ==="]
        for law in laws:
            source = law.get('document_name', 'Ligj')
            text = law.get('text', '')[:1500] # Truncate huge laws
            law_buffer.append(f"BURIMI: {source}\nTEKSTI: {text}\n---")
            
        return "\n".join(law_buffer)
    except Exception as e:
        logger.warning(f"Failed to fetch relevant laws: {e}")
        return ""

def _generate_static_fallback(error_msg: str) -> Dict[str, Any]:
    return {
        "summary_analysis": f"⚠️ Analiza e thellë AI nuk është e disponueshme (Kufizim: {error_msg}).",
        "contradictions": ["Nuk u identifikuan automatikisht."],
        "risks": ["Ju lutemi rishikoni gjetjet manuale."],
        "missing_info": ["Kontrolloni manualisht dosjen."]
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
            "format": "json"
        }
        with httpx.Client(timeout=90.0) as client: # Increased timeout for analysis
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
    
    # 1. Prepare Case Context
    case_context = _get_case_context(db, case_id)
    if not case_context:
        return {"error": "Nuk ka mjaftueshëm të dhëna për analizë."}

    # 2. Fetch Legal Grounding (New Step)
    relevant_laws = _fetch_relevant_laws(case_context)
    
    # 3. Define High-IQ Prompt
    system_prompt = """
    Ti je një Avokat i Lartë ("Senior Litigator") i specializuar në Ligjet e Kosovës dhe Shqipërisë.
    
    DETYRA: Analizo dosjen duke përdorur DOKUMENTET dhe LIGJET e ofruara.
    
    Kërko specifikisht:
    1. SHKELJE LIGJORE: A ka ndonjë klauzolë në dokumente që bie në kundërshtim me LIGJET e ofruara?
    2. KONTRADIKTA: A thotë Dokumenti A diçka ndryshe nga Dokumenti B?
    3. RREZIQE LATENTE: Çfarë mund të shkojë keq për klientin?
    
    Përgjigju VETËM në format JSON:
    {
      "contradictions": ["list of strings..."],
      "risks": ["list of strings (cite specific laws if applicable)..."],
      "missing_info": ["list of strings..."],
      "summary_analysis": "Analizë profesionale (max 150 fjalë)."
    }
    Përgjigju në GJUHËN SHQIPE.
    """
    
    user_prompt = f"""
    {relevant_laws}
    
    === DOSJA E RASTIT ===
    {case_context[:20000]} 
    """

    # --- TIER 1: GROQ (CLOUD) ---
    api_key = os.environ.get("GROQ_API_KEY")
    if api_key:
        try:
            client = Groq(api_key=api_key)
            completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model="llama-3.3-70b-versatile",
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            content = completion.choices[0].message.content
            if content:
                log.info("analysis.success_tier_1_groq")
                return json.loads(content)

        except Exception as e:
            log.warning("analysis.groq_failed", error=str(e))
            pass

    # --- TIER 2: LOCAL LLM (OLLAMA) ---
    # Local LLM gets the laws too!
    local_result = _call_local_llm(system_prompt, user_prompt)
    if local_result:
        log.info("analysis.success_tier_2_local")
        local_result["summary_analysis"] = "[AI Lokale] " + local_result.get("summary_analysis", "")
        return local_result

    # --- TIER 3: FALLBACK ---
    return _generate_static_fallback("Cloud & Local AI Unavailable")