# FILE: backend/app/services/findings_service.py
# PHOENIX PROTOCOL - INTELLIGENT EXTRACTION V4.1
# 1. ENGINE: Direct integration with DeepSeek V3 (OpenRouter) for high-precision extraction.
# 2. PROMPT: specialized "Legal Auditor" persona for Kosovo context.
# 3. FALLBACK: Graceful degradation to legacy local LLM if API fails.

import os
import json
import structlog
from bson import ObjectId
from typing import List, Dict, Any, Optional
from pymongo.database import Database
from pymongo.results import DeleteResult
from datetime import datetime, timezone
from openai import OpenAI

# Legacy fallback
from app.services.llm_service import extract_findings_from_text as legacy_extract

logger = structlog.get_logger(__name__)

# --- CONFIGURATION ---
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY") 
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat"

def _extract_with_deepseek(text: str) -> Optional[List[Dict[str, Any]]]:
    """
    Uses DeepSeek V3 to perform a forensic audit of the document text.
    Returns structured JSON findings.
    """
    if not DEEPSEEK_API_KEY:
        return None

    try:
        client = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=OPENROUTER_BASE_URL
        )

        # Smart Context Window Management
        # DeepSeek has a huge context, but we keep it reasonable for cost/speed.
        truncated_text = text[:30000] 

        system_prompt = """
        Ti je "Juristi AI - Auditori Ligjor", një sistem ekspert për analizën e dokumenteve në Kosovë.
        
        DETYRA:
        Lexo tekstin e mëposhtëm dhe nxirr "Gjetjet Kyçe" (Key Findings).
        
        KATEGORITË E GJETJEVE TË KËRKUARA:
        1. AFATET & DATAT: Data të nënshkrimit, skadencës, ose afate ligjore.
        2. DETYRIMET FINANCIARE: Shuma parash, paga, gjoba, ose kompensime.
        3. RREZIQE / KLAUZOLA: Nene që imponojnë penalitete ose kufizime të rënda.
        4. PALËT: Kush është i përfshirë (Emra, Kompani, Numra Personal/Biznesi).

        FORMATI JSON I KËRKUAR:
        [
          {
            "finding_text": "Përshkrim i shkurtër dhe i qartë i gjetjes (në Shqip)",
            "source_text": "Citat i saktë nga teksti origjinal që mbështet gjetjen",
            "category": "AFAT" | "FINANCE" | "RREZIK" | "PALËT"
          }
        ]
        
        RREGULLA:
        - Mos shpik informacione.
        - Nëse nuk ka gjetje të rëndësishme, kthe listë bosh [].
        - Përgjigju VETËM me JSON.
        """

        response = client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"DOKUMENTI:\n{truncated_text}"}
            ],
            temperature=0.1, # Strict adherence to facts
            response_format={"type": "json_object"},
            extra_headers={
                "HTTP-Referer": "https://juristi.tech", 
                "X-Title": "Juristi AI Findings"
            }
        )

        content = response.choices[0].message.content
        if not content: return None

        # Parse JSON
        data = json.loads(content)
        # Handle cases where LLM wraps list in a key like "findings": [...]
        if isinstance(data, dict):
            for key in data:
                if isinstance(data[key], list):
                    return data[key]
            return [] # Fallback if dict structure is weird
        elif isinstance(data, list):
            return data
            
    except Exception as e:
        logger.error("deepseek_extraction_failed", error=str(e))
        return None
    
    return None

def extract_and_save_findings(db: Database, document_id: str, full_text: str):
    log = logger.bind(document_id=document_id)
    log.info("findings_service.extraction.started", text_length=len(full_text))
    
    document = db.documents.find_one({"_id": ObjectId(document_id)})
    if not document:
        log.warning("findings_service.document_not_found")
        return
    
    if not full_text or not full_text.strip():
        log.warning("findings_service.no_text_provided")
        return
    
    # 1. Try DeepSeek (Tier 1)
    extracted_findings = _extract_with_deepseek(full_text)
    
    # 2. Fallback to Local/Legacy (Tier 2)
    if extracted_findings is None:
        log.info("findings_service.switching_to_legacy_extractor")
        extracted_findings = legacy_extract(full_text)
    
    if not extracted_findings:
        log.info("findings_service.no_findings_found")
        return

    case_id = document.get("case_id")
    file_name = document.get("file_name", "Unknown Document")
    
    findings_to_insert = []
    for finding in extracted_findings:
        # Normalize keys regardless of source
        f_text = finding.get("finding_text") or finding.get("finding")
        s_text = finding.get("source_text") or finding.get("quote") or "N/A"
        
        if f_text:
            findings_to_insert.append({
                "case_id": case_id, 
                "document_id": ObjectId(document_id),
                "document_name": file_name,
                "finding_text": f_text,
                "source_text": s_text,
                "page_number": finding.get("page_number", 1),
                "confidence_score": 1.0, # AI is confident
                "created_at": datetime.now(timezone.utc)
            })
    
    if findings_to_insert:
        db.findings.insert_many(findings_to_insert)
        log.info("findings_service.extraction.completed", findings_saved=len(findings_to_insert))
        
        # PHOENIX ADDITION: Update Document status to signal findings ready
        # Optional: could trigger a notification here
    else:
        log.info("findings_service.extraction.completed.no_valid_findings")

def get_findings_for_case(db: Database, case_id: str) -> List[Dict[str, Any]]:
    try:
        case_object_id = ObjectId(case_id)
    except Exception:
        return []
    pipeline = [
        {'$match': {'case_id': case_object_id}},
        {'$sort': {'created_at': -1}}, # Newest first
        {'$project': {
            '_id': 1, 
            'case_id': 1, 
            'document_id': 1, 
            'finding_text': 1, 
            'source_text': 1,
            'page_number': 1, 
            'document_name': 1, 
            'confidence_score': 1,
            'created_at': 1 
        }}
    ]
    return list(db.findings.aggregate(pipeline))

def delete_findings_by_document_id(db: Database, document_id: ObjectId) -> List[ObjectId]:
    log = logger.bind(document_id=str(document_id))
    
    if not isinstance(document_id, ObjectId):
        log.error("findings_service.deletion.invalid_id_type")
        return []
        
    findings_to_delete = list(db.findings.find({"document_id": document_id}, {"_id": 1}))
    deleted_ids = [item["_id"] for item in findings_to_delete]

    if not deleted_ids:
        log.info("findings_service.deletion.no_findings_found")
        return []

    result: DeleteResult = db.findings.delete_many({"_id": {"$in": deleted_ids}})
    log.info("findings_service.deletion.completed", findings_deleted=result.deleted_count)
    
    return deleted_ids