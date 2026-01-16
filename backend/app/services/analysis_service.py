# FILE: backend/app/services/analysis_service.py
# PHOENIX PROTOCOL - ANALYSIS SERVICE V16.1 (TYPE SAFETY FIX)
# 1. FIX: Resolved Pylance error in 'authorize_case_access' by handling None return type explicitly.
# 2. CORE: Preserved all Deep Strategy and Agent Orchestration logic from V16.0.

import structlog
import hashlib
import time
import asyncio
from typing import List, Dict, Any, Optional, Tuple, cast
from pymongo.database import Database
from bson import ObjectId

# SAFE IMPORT
import app.services.llm_service as llm_service
from .graph_service import graph_service

logger = structlog.get_logger(__name__)

# --- CONFIGURATION ---
MAX_CONTEXT_CHARS_PER_DOC = 6000
MIN_TEXT_LENGTH = 20
CACHE_TTL_SECONDS = 300

# --- CACHING LAYER ---
class AnalysisCache:
    def __init__(self):
        self.cache = {}
        self.access_times = {}
        
    def get_key(self, case_id: str, user_id: str, mode: str = "full") -> str:
        return hashlib.md5(f"{case_id}:{user_id}:{mode}".encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        if key in self.cache:
            return self.cache[key]
        return None
    
    def set(self, key: str, value: Dict[str, Any]) -> None:
        self.cache[key] = value

analysis_cache = AnalysisCache()

# --- SECURITY & AUTH ---
def authorize_case_access(db: Database, case_id: str, user_id: str) -> Tuple[bool, Dict[str, Any]]:
    try:
        case_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
        user_oid = ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id
        
        # 1. Standard Check: Does User Own Case?
        case = db.cases.find_one({
            "_id": case_oid,
            "$or": [{"user_id": user_oid}, {"user_id": str(user_oid)}]
        })
        
        if case:
            return True, cast(Dict[str, Any], case)
        
        # 2. Admin Override Check
        user = db.users.find_one({"_id": user_oid})
        if user and user.get("role") == "ADMIN":
            # Explicitly check if case exists globally
            admin_case = db.cases.find_one({"_id": case_oid})
            if admin_case:
                return True, cast(Dict[str, Any], admin_case)
                
        return False, {"error": "Nuk keni akses në këtë rast."}
    except Exception as e:
        logger.error(f"Auth failed: {e}")
        return False, {"error": "Gabim autorizimi."}

# --- TEXT EXTRACTION ---
def _get_full_case_text(db: Database, case_id: str) -> str:
    """
    Aggregates text from all documents in a case.
    """
    try:
        # Try both ObjectId and String formats to be safe
        documents = list(db.documents.find({"case_id": ObjectId(case_id)}))
        if not documents:
            documents = list(db.documents.find({"case_id": str(case_id)}))
            
        if not documents:
            return ""
        
        context_buffer = []
        for doc in documents:
            # Hierarchy: Extracted > OCR > Summary > Nothing
            txt = doc.get("extracted_text") or doc.get("ocr_text") or doc.get("summary") or ""
            if len(str(txt)) > MIN_TEXT_LENGTH:
                clean_content = str(txt)[:MAX_CONTEXT_CHARS_PER_DOC]
                context_buffer.append(f"\n=== DOKUMENTI: {doc.get('file_name', 'Unknown')} ===\n{clean_content}")

        return "\n".join(context_buffer)
    except Exception as e:
        logger.error(f"Context extraction failed: {e}")
        return ""

# --- MAIN ANALYSIS FUNCTION (STANDARD) ---
def cross_examine_case(
    db: Database, 
    case_id: str, 
    user_id: str,
    force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Called by the 'Analyze Tab'. Runs standard legal integrity check.
    """
    start_time = time.time()
    
    # 1. Auth
    authorized, auth_result = authorize_case_access(db, case_id, user_id)
    if not authorized: return auth_result
    
    # 2. Cache
    cache_key = analysis_cache.get_key(case_id, user_id, "standard")
    if not force_refresh:
        if cached := analysis_cache.get(cache_key): 
            return cached

    # 3. Data
    full_text = _get_full_case_text(db, case_id)
    if not full_text:
        return {"summary": "Nuk u gjet tekst.", "strategic_analysis": "Mungojnë të dhënat.", "risk_level": "LOW", "error": True}

    # 4. Intelligence
    # Note: We pass 'full_text' directly. The prompt handles Graph + Text inside 'llm_service' logic if we expanded it,
    # but here we keep it simple for the Standard Analysis.
    result = llm_service.analyze_case_integrity(full_text)
    
    if result:
        result["processing_time_ms"] = int((time.time() - start_time) * 1000)
        analysis_cache.set(cache_key, result)
        return result
        
    return {"error": "Analiza dështoi.", "risk_level": "UNKNOWN"}

# --- NEW: DEEP STRATEGIC ANALYSIS (THE SENIOR PARTNER SUITE) ---
async def run_deep_strategy(db: Database, case_id: str, user_id: str) -> Dict[str, Any]:
    """
    Runs ALL advanced agents: Adversarial, Chronology, Contradictions.
    Intended for the 'Strategic Plan' tab.
    """
    authorized, _ = authorize_case_access(db, case_id, user_id)
    if not authorized: return {"error": "Unauthorized"}

    full_text = _get_full_case_text(db, case_id)
    if not full_text: return {"error": "No documents found."}

    # Run agents sequentially (or in parallel if using asyncio.gather)
    adversarial = llm_service.generate_adversarial_simulation(full_text)
    chronology = llm_service.build_case_chronology(full_text)
    contradictions = llm_service.detect_contradictions(full_text)

    return {
        "adversarial_simulation": adversarial,
        "chronology": chronology.get("timeline", []),
        "contradictions": contradictions.get("contradictions", [])
    }

# --- NEW: DEADLINE CHECKER (ON UPLOAD) ---
def check_for_deadlines(text: str) -> Optional[Dict[str, Any]]:
    """
    Called when a document is uploaded. Returns alert data if a deadline is found.
    """
    result = llm_service.extract_deadlines(text)
    if result.get("is_judgment"):
        return result
    return None

def analyze_node_context(db: Database, case_id: str, node_id: str, user_id: str) -> Dict[str, Any]:
    return {"summary": "Node analysis placeholder."}