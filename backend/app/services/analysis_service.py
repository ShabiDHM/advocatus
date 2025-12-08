# FILE: backend/app/services/analysis_service.py
# PHOENIX PROTOCOL - ANALYSIS SERVICE V5 (LITIGATION READY)
# 1. GRAPH INTEGRATION: Extracts 'graph_data' (Accusations, Contradictions) and feeds Neo4j.
# 2. PROMPT UPGRADE: Instructs LLM to act as a Forensic Legal Auditor.
# 3. OUTPUT: Generates both the UI Report AND the Graph Structure in one pass.

import os
import json
import structlog
import httpx 
from typing import List, Dict, Any, Optional
from pymongo.database import Database
from bson import ObjectId
from openai import OpenAI

from .vector_store_service import query_legal_knowledge_base
from .embedding_service import generate_embedding
from .graph_service import graph_service  # PHOENIX: Connected the Graph Engine

logger = structlog.get_logger(__name__)

# --- CONFIGURATION ---
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY") 
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat" 

# Local Fallback
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
            === DOKUMENTI (ID: {doc_id}): {name} ===
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
    try:
        query_text = case_text[:1500].replace("\n", " ")
        embedding = generate_embedding(query_text)
        if not embedding: return ""
        laws = query_legal_knowledge_base(embedding, n_results=5)
        if not laws: return ""
        law_buffer = ["=== BAZA LIGJORE RELEVANTE (NGA LIGJET E KOSOVËS) ==="]
        for law in laws:
            source = law.get('document_name', 'Ligj')
            text = law.get('text', '')[:1500] 
            law_buffer.append(f"BURIMI: {source}\nTEKSTI: {text}\n---")
        return "\n".join(law_buffer)
    except Exception: return ""

def _generate_static_fallback(error_msg: str) -> Dict[str, Any]:
    return {
        "summary_analysis": f"⚠️ Analiza e thellë nuk mund të gjenerohej ({error_msg}).",
        "contradictions": ["Kontrolloni manualisht dokumentet."],
        "risks": ["Sistemi AI nuk është i qasshëm momentalisht."],
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
    
    # 2. Forensic Prompt
    system_prompt = """
    Ti je "Juristi AI", Auditor Ligjor Forenzik (Senior Legal Auditor) për Kosovën.
    
    DETYRA:
    Analizo dosjen për të gjetur (1) Rreziqe Ligjore dhe (2) Strukturën e Konfliktit për bazën e të dhënave Graph.
    
    FORMATI I DALJES (JSON STRIKT):
    {
      "summary_analysis": "Analizë narrative profesionale (paragraf).",
      "contradictions": ["Listë tekstuale e mospërputhjeve..."],
      "risks": ["Listë e rreziqeve ligjore..."],
      "missing_info": ["Dokumente që mungojnë..."],
      "graph_data": [
         {
           "type": "ACCUSATION",
           "source": "Emri i Akuzuesit",
           "target": "Emri i të Akuzuarit",
           "text": "Përshkrimi i shkurtër i akuzës (psh. Mashtrim)"
         },
         {
           "type": "CONTRADICTION",
           "claim_text": "Pretendimi (psh. Pagesa u bë)",
           "evidence_text": "Evidenca kundërshtuese (psh. Llogaria bankare bosh)"
         }
      ]
    }
    
    Përgjigju vetëm JSON. Përdor Shqipen.
    """
    
    user_prompt = f"{relevant_laws}\n\n=== DOSJA E RASTIT ===\n{case_context[:28000]}"

    result = None

    # --- EXECUTION ---
    if DEEPSEEK_API_KEY:
        try:
            client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=OPENROUTER_BASE_URL)
            completion = client.chat.completions.create(
                model=OPENROUTER_MODEL,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            content = completion.choices[0].message.content
            if content:
                result = json.loads(content)
                log.info("analysis.success_deepseek")
        except Exception as e:
            log.warning("analysis.deepseek_failed", error=str(e))

    if not result:
        result = _call_local_llm(system_prompt, user_prompt)

    # --- GRAPH INGESTION ---
    if result and "graph_data" in result:
        try:
            # We associate these findings with the Case itself, or a 'General Analysis' node.
            # Ideally, we pass a specific doc_id if available, but for case-wide analysis, 
            # we can use the Case ID as the anchor or iterate documents if we knew source.
            # Here, we treat the 'Case' as the source context.
            graph_items = result["graph_data"]
            # To link properly, we need a valid document ID. 
            # Strategy: Find the most relevant document ID from the text or pick the first one 
            # For now, we skip Doc linking if ambiguous, or link to a "CASE_ANALYSIS" node.
            
            # Simplified: Pass the first document ID found in DB just to anchor the nodes, 
            # or update ingest_legal_analysis to handle pure Case ID ingestion.
            # Check graph_service.py -> it expects doc_id. 
            # Workaround: Use case_id as doc_id (Neo4j won't mind, it's just a string ID).
            graph_service.ingest_legal_analysis(case_id, f"ANALYSIS_{case_id}", graph_items)
            log.info("analysis.graph_ingested", items=len(graph_items))
        except Exception as e:
            log.error("analysis.graph_ingest_failed", error=str(e))

    return result or _generate_static_fallback("Analiza dështoi.")