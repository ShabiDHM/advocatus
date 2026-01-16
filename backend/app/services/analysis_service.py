# FILE: backend/app/services/analysis_service.py
# PHOENIX PROTOCOL - ANALYSIS SERVICE V15.1 (SAFE IMPORTS)
# 1. FIX: Switched to 'import app.services.llm_service as llm_service' to fix Pylance resolution.
# 2. LOGIC: Unchanged.

import structlog
import hashlib
import time
import os
import re
from typing import List, Dict, Any, Optional, Tuple
from pymongo.database import Database
from bson import ObjectId

# SAFE IMPORT
import app.services.llm_service as llm_service
from .graph_service import graph_service

logger = structlog.get_logger(__name__)

# --- CONFIGURATION ---
MAX_CONTEXT_CHARS_PER_DOC = 6000
MIN_TEXT_LENGTH = 20
CACHE_TTL_SECONDS = 60 
MAX_CACHE_SIZE = 1000

# Document priority
PRIORITY_KEYWORDS = {
    1: ["aktgjykim", "vendim", "aktvendim", "judgment"],
    2: ["padi", "kerkese", "lawsuit", "complaint"],
    3: ["procesverbal", "minutes"],
    4: ["marrëveshje", "contract", "agreement"],
    5: ["faturë", "invoice"],
    6: ["dokument", "document"]
}

# --- CACHING LAYER ---
class AnalysisCache:
    def __init__(self):
        self.cache = {}
        self.access_times = {}
        
    def get_key(self, case_id: str, user_id: str, mode: str = "full") -> str:
        return hashlib.md5(f"{case_id}:{user_id}:{mode}".encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        if key in self.cache:
            if time.time() - self.access_times.get(key, 0) < CACHE_TTL_SECONDS:
                return self.cache[key]
            del self.cache[key]
        return None
    
    def set(self, key: str, value: Dict[str, Any]) -> None:
        if len(self.cache) >= MAX_CACHE_SIZE:
            oldest_key = min(self.access_times.items(), key=lambda x: x[1])[0]
            del self.cache[oldest_key]
            del self.access_times[oldest_key]
        self.cache[key] = value
        self.access_times[key] = time.time()

analysis_cache = AnalysisCache()

# --- SECURITY & AUTH ---
def authorize_case_access(db: Database, case_id: str, user_id: str) -> Tuple[bool, Dict[str, Any]]:
    try:
        case_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
        user_oid = ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id
        
        # Try finding case where user is owner
        case = db.cases.find_one({
            "_id": ObjectId(case_id),
            "$or": [{"user_id": user_oid}, {"user_id": str(user_oid)}]
        })
        
        if not case:
            # Admin override check
            user = db.users.find_one({"_id": user_oid})
            if user and user.get("role") == "ADMIN":
                case = db.cases.find_one({"_id": ObjectId(case_id)})
                if case: return True, case
            return False, {"error": "Nuk keni akses në këtë rast."}
        
        return True, case
    except Exception as e:
        logger.error(f"Auth failed: {e}")
        return False, {"error": "Gabim autorizimi."}

# --- TEXT EXTRACTION (ROBUST) ---
def _get_document_priority(doc_name: str) -> int:
    if not doc_name: return 999
    name = doc_name.lower()
    for priority, keywords in PRIORITY_KEYWORDS.items():
        if any(keyword in name for keyword in keywords): return priority
    return 999

def _get_full_case_text(db: Database, case_id: str) -> str:
    try:
        query = {"case_id": ObjectId(case_id)}
        documents = list(db.documents.find(query))
        
        if not documents:
            documents = list(db.documents.find({"case_id": str(case_id)}))
            
        if not documents:
            logger.warning(f"Analysis: No documents found for case {case_id}")
            return ""
        
        documents.sort(key=lambda x: _get_document_priority(x.get("file_name", "")))
        
        context_buffer = []
        total_chars = 0
        
        for doc in documents:
            name = doc.get("file_name", "Untitled")
            content = doc.get("extracted_text")
            if not content or len(str(content)) < MIN_TEXT_LENGTH:
                content = doc.get("ocr_text")
            if not content or len(str(content)) < MIN_TEXT_LENGTH:
                content = doc.get("summary")
            if not content or len(str(content)) < MIN_TEXT_LENGTH:
                content = f"[Metadata Only] This file '{name}' exists but has no readable text content yet."

            clean_content = str(content)[:MAX_CONTEXT_CHARS_PER_DOC]
            entry = f"\n=== DOKUMENTI: {name} ===\n{clean_content}\n"
            context_buffer.append(entry)
            total_chars += len(clean_content)

        full_context = "\n".join(context_buffer)
        logger.info(f"Analysis Context Built: {len(documents)} docs, {total_chars} chars")
        return full_context

    except Exception as e:
        logger.error(f"Context build failed: {e}")
        return ""

# --- MAIN ANALYSIS FUNCTION ---
def cross_examine_case(
    db: Database, 
    case_id: str, 
    user_id: str,
    force_refresh: bool = False
) -> Dict[str, Any]:
    start_time = time.time()
    try:
        authorized, auth_result = authorize_case_access(db, case_id, user_id)
        if not authorized: return auth_result
        
        cache_key = analysis_cache.get_key(case_id, user_id)
        if not force_refresh:
            if cached := analysis_cache.get(cache_key): 
                logger.info("Analysis served from cache.")
                return cached

        full_text = _get_full_case_text(db, case_id)
        
        if not full_text or len(full_text) < 50:
            return {
                "summary": "Nuk u gjet tekst i mjaftueshëm për analizë.",
                "strategic_analysis": "Ju lutem sigurohuni që dokumentet janë ngarkuar dhe procesuar (OCR). Aktualisht sistemi nuk sheh tekst.",
                "risk_level": "LOW",
                "error": True
            }

        graph_context = graph_service.get_strategic_context(case_id)
        
        final_prompt_payload = f"""
        === GRAPH INTELLIGENCE (RELATIONSHIPS) ===
        {graph_context}
        
        === CASE DOCUMENTS (EVIDENCE) ===
        {full_text}
        """

        # SAFE CALL using module.function
        result = llm_service.analyze_case_integrity(final_prompt_payload)
        
        if isinstance(result, dict) and result.get("summary"):
            result["processing_time_ms"] = int((time.time() - start_time) * 1000)
            analysis_cache.set(cache_key, result)
        else:
             result = {
                 "summary": "Analiza dështoi të strukturohej nga AI.",
                 "strategic_analysis": "Sistemi mori të dhënat por nuk arriti të gjenerojë formatin JSON të kërkuar.",
                 "risk_level": "UNKNOWN",
                 "error": True
             }
        
        return result

    except Exception as e:
        logger.error(f"Analysis Critical Failure: {e}")
        return {"error": "Gabim i brendshëm i sistemit gjatë analizës."}

def analyze_node_context(db: Database, case_id: str, node_id: str, user_id: str) -> Dict[str, Any]:
    return {"summary": "Node analysis placeholder."}