# FILE: backend/app/services/analysis_service.py
# PHOENIX PROTOCOL - ANALYSIS SERVICE V7.1 (STABILITY PATCH)
# 1. FIX: Uses 'Lazy Import' for vector_store_service to resolve Pylance circular dependency errors.
# 2. JURISDICTION: Remains STRICTLY HARDCODED to Kosovo.
# 3. LOGIC: Validates logic and flags Albania/Foreign jurisdictions as risks.

import os
import json
import structlog
import httpx 
from typing import List, Dict, Any, Optional
from pymongo.database import Database
from bson import ObjectId
from openai import OpenAI

# PHOENIX: Lazy imports are used inside functions for vector_store to prevent circular locks.
from .embedding_service import generate_embedding
from .graph_service import graph_service 

logger = structlog.get_logger(__name__)

# --- CONFIGURATION ---
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY") 
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat" 

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
            created_at = doc.get("created_at", "N/A")
            
            doc_context = f"""
            === DOKUMENTI (ID: {doc_id}): {name} ===
            DATA E DOKUMENTIT (SISTEM): {created_at}
            PËRMBLEDHJE: {summary}
            GJETJET AUTOMATIKE: {findings_text}
            ------------------------------------------------
            """
            context_buffer.append(doc_context)
        return "\n".join(context_buffer)
    except Exception as e:
        logger.error("analysis.context_build_failed", error=str(e))
        return ""

def _fetch_relevant_laws(case_text: str) -> str:
    try:
        # PHOENIX FIX: Lazy Import to resolve "unknown import symbol" / Circular Dependency
        from .vector_store_service import query_legal_knowledge_base
        
        query_text = case_text[:1500].replace("\n", " ")
        embedding = generate_embedding(query_text)
        if not embedding: return ""
        
        # We invoke the function which now strictly enforces 'ks' internally
        laws = query_legal_knowledge_base(embedding, n_results=5)
        
        if not laws: return ""
        law_buffer = ["=== BAZA LIGJORE (LIGJET E KOSOVËS) ==="]
        for law in laws:
            source = law.get('document_name', 'Ligj i Kosovës')
            text = law.get('text', '')[:1000] 
            law_buffer.append(f"BURIMI: {source}\nTEKSTI: {text}\n---")
        return "\n".join(law_buffer)
    except Exception as e:
        logger.warning(f"analysis.fetch_laws_failed: {e}")
        return ""

def _generate_static_fallback(error_msg: str) -> Dict[str, Any]:
    return {
        "summary_analysis": f"⚠️ Analiza dështoi: {error_msg}",
        "contradictions": [],
        "risks": ["Sistemi nuk u përgjigj."],
        "missing_info": [],
        "graph_data": []
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
            "options": {"temperature": 0.1}
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
    
    # 1. Data Prep
    case_context = _get_case_context(db, case_id)
    if not case_context:
        return {"error": "Nuk ka mjaftueshëm të dhëna në dosje për analizë."}
    
    relevant_laws = _fetch_relevant_laws(case_context)
    
    # 2. STRICT KOSOVO PROMPT
    system_prompt = """
    Ti je "Juristi AI", Ekspert për Legjislacionin e Republikës së Kosovës.
    
    DETYRA:
    Analizo dosjen vetëm sipas LIGJEVE TË KOSOVËS.
    
    RREGULLA TË GURTA (STRICT RULES):
    1. VALIDIMI LOGJIK: 
       - Nëse sheh data inekzistente (psh. "228 Dhjetor", "32 Janar"), KJO ËSHTË KONTRADIKTË KRITIKE.
       - Nëse datat e nënshkrimit janë pas datës së dorëzimit, shënoje si Kontradiktë.
    
    2. JURIDIKSIONI (KOSOVË ONLY):
       - Nëse dokumenti përmend qytete jashtë Kosovës (psh. Tiranë, Shqipëri, Durrës), kjo përbën RREZIK LIGJOR.
       - Mos apliko ligjet e Shqipërisë. 
       - Shëno te Rreziqet: "Dokumenti i referohet juridiksionit të huaj (psh. Tiranë) dhe mund të mos jetë i zbatueshëm në Kosovë."

    3. FORMATI JSON:
    {
      "summary_analysis": "Përmbledhje e shkurtër. Përmend nëse ka probleme me datat apo juridiksionin.",
      "contradictions": [
         "Gabim Logjik: Data '228 Dhjetor' është e pamundur.",
         "Mospërputhje tjera..."
      ],
      "risks": [
         "Rrezik Juridiksioni: Prona gjendet në Tiranë (Jashtë Kosovës).",
         "Rreziqe tjera sipas ligjeve të Kosovës..."
      ],
      "missing_info": ["Dokumente që mungojnë..."],
      "graph_data": [
         { "type": "ACCUSATION" | "CONTRADICTION", "source": "String", "target": "String", "text": "String" }
      ]
    }
    
    Përgjigju vetëm në JSON dhe në SHQIP.
    """
    
    user_prompt = f"""
    {relevant_laws}
    
    === DOSJA ===
    {case_context[:30000]}
    """

    result = None

    if DEEPSEEK_API_KEY:
        try:
            client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=OPENROUTER_BASE_URL)
            completion = client.chat.completions.create(
                model=OPENROUTER_MODEL,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            content = completion.choices[0].message.content
            if content:
                result = json.loads(content)
        except Exception as e:
            log.warning("analysis.deepseek_failed", error=str(e))

    if not result:
        result = _call_local_llm(system_prompt, user_prompt)

    if result and "graph_data" in result:
        try:
            graph_items = result["graph_data"]
            graph_service.ingest_legal_analysis(case_id, f"ANALYSIS_{case_id}", graph_items)
        except Exception as e:
            log.error("analysis.graph_ingest_failed", error=str(e))

    return result or _generate_static_fallback("Analiza dështoi.")