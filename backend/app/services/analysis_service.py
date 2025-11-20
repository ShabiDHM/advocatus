# FILE: backend/app/services/analysis_service.py
# PHOENIX PROTOCOL - MODEL UPDATE
# 1. MODEL CHANGE: Switched to 'llama-3.3-70b-versatile' (Older 3.1 model is decommissioned).
# 2. STABILITY: Retains all previous logic and robust error handling.

import os
import json
import structlog
from typing import List, Dict, Any, Optional
from pymongo.database import Database
from bson import ObjectId
from groq import Groq

logger = structlog.get_logger(__name__)

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
            
            GJETJET KYÇE:
            {findings_text}
            
            AFATET/DATAT:
            {deadlines_text}
            ===========================
            """
            context_buffer.append(doc_context)
            
        return "\n\n".join(context_buffer)
    except Exception as e:
        logger.error("analysis.context_build_failed", error=str(e))
        return ""

def cross_examine_case(db: Database, case_id: str) -> Dict[str, Any]:
    log = logger.bind(case_id=case_id)
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key: 
        return {"error": "AI service not configured"}
    
    client = Groq(api_key=api_key)
    
    case_context = _get_case_context(db, case_id)
    if not case_context:
        return {"error": "Nuk ka mjaftueshëm të dhëna për analizë. Ngarkoni dokumente fillimisht."}

    system_prompt = """
    Ti je një Avokat i Lartë ("Senior Litigator") i specializuar në analizën e rreziqeve.
    Detyra jote është të bësh "Cross-Examination" (Marrje në Pyetje) të dokumenteve të mëposhtme.
    
    Ti duhet të kërkosh për:
    1. KONTRADIKTA: A thotë Dokumenti A diçka ndryshe nga Dokumenti B? (psh. data të ndryshme, shuma të ndryshme).
    2. RREZIQE: A ka klauzola ose gjetje që e vënë klientin në rrezik ligjor?
    3. MUNGESA: Çfarë informacioni kritik mungon?
    
    Përgjigju VETËM në format JSON. Struktura e kërkuar:
    {
      "contradictions": ["list of strings..."],
      "risks": ["list of strings..."],
      "missing_info": ["list of strings..."],
      "summary_analysis": "A paragraph summarizing the case strength."
    }
    
    Përgjigju në GJUHËN SHQIPE.
    """
    
    user_prompt = f"""
    Analizo këtë dosje gjyqësore:
    
    {case_context[:25000]} 
    """

    try:
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            # PHOENIX FIX: Updated model version
            model="llama-3.3-70b-versatile", 
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        content = completion.choices[0].message.content
        
        if not content:
            return {"error": "AI returned no content."}
            
        return json.loads(content)

    except json.JSONDecodeError:
        log.error("analysis.json_parse_error")
        return {"error": "Gabim në formatimin e përgjigjes nga AI."}
    except Exception as e:
        log.error("analysis.failed", error=str(e))
        return {"error": "Analiza dështoi për shkak të një gabimi teknik."}