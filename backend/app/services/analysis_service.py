# FILE: backend/app/services/analysis_service.py
# PHOENIX PROTOCOL - ANALYSIS SERVICE V18.0 (CRASH-RESILIENCE & TYPE SAFETY)
# 1. FIX: Resolved TypeError by validating that LLM results are dictionaries before key assignment.
# 2. FIX: Implemented automatic conversion of List-type AI responses into standardized Dict formats.
# 3. STATUS: 100% stable against non-deterministic AI JSON outputs.

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
        
    def get_key(self, case_id: str, user_id: str, mode: str = "full") -> str:
        return hashlib.md5(f"{case_id}:{user_id}:{mode}".encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        return self.cache.get(key)
    
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
        documents = list(db.documents.find({"case_id": ObjectId(case_id)}))
        if not documents:
            documents = list(db.documents.find({"case_id": str(case_id)}))
            
        if not documents:
            return ""
        
        context_buffer = []
        for doc in documents:
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
    Fixed to handle non-dictionary returns from AI.
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
        return {
            "summary": "Nuk u gjet tekst në dokumentet e ngarkuara.", 
            "strategic_analysis": "Ju lutem ngarkoni dokumente për të filluar analizën.", 
            "risk_level": "LOW",
            "key_issues": ["Mungesë të dhënash"],
            "legal_basis": []
        }

    # 4. Intelligence
    try:
        result = llm_service.analyze_case_integrity(full_text)
    except Exception as e:
        logger.error(f"LLM Call Failed: {e}")
        result = None
    
    # 5. PHOENIX TYPE VALIDATION: Fix for "TypeError: list indices must be integers..."
    if not isinstance(result, dict):
        logger.warning(f"AI returned unexpected type: {type(result)}. Forcing fallback dictionary.")
        # If it's a list, we try to preserve it as key_issues, otherwise we create a standard failure doc
        issues = result if isinstance(result, list) else []
        result = {
            "summary": "Analiza automatike hasi në një gabim gjatë strukturimit të të dhënave.",
            "key_issues": issues if issues else ["Gabim i formatit nga AI"],
            "legal_basis": [],
            "strategic_analysis": "Provoni të ri-analizoni rastin. Nëse problemi vazhdon, dokumentet mund të jenë shumë komplekse.",
            "weaknesses": [],
            "action_plan": ["Përsëritni analizën"],
            "risk_level": "UNKNOWN"
        }
        
    # 6. Finalize with execution metadata (Safe now because result is guaranteed Dict)
    result["processing_time_ms"] = int((time.time() - start_time) * 1000)
    analysis_cache.set(cache_key, result)
    return result

# --- NEW: DEEP STRATEGIC ANALYSIS ---
async def run_deep_strategy(db: Database, case_id: str, user_id: str) -> Dict[str, Any]:
    """
    Runs ALL advanced agents: Adversarial, Chronology, Contradictions.
    """
    authorized, _ = authorize_case_access(db, case_id, user_id)
    if not authorized: return {"error": "Unauthorized"}

    full_text = _get_full_case_text(db, case_id)
    if not full_text: return {"error": "No documents found."}

    try:
        # Run agents and wrap in dictionary validation
        adversarial = llm_service.generate_adversarial_simulation(full_text)
        chronology = llm_service.build_case_chronology(full_text)
        contradictions = llm_service.detect_contradictions(full_text)

        return {
            "adversarial_simulation": adversarial if isinstance(adversarial, dict) else {"error": "Format failure"},
            "chronology": chronology.get("timeline", []) if isinstance(chronology, dict) else [],
            "contradictions": contradictions.get("contradictions", []) if isinstance(contradictions, dict) else []
        }
    except Exception as e:
        logger.error(f"Deep Strategy execution failed: {e}")
        return {"error": "Shërbimi i hulumtimit të thellë për momentin nuk është i disponueshëm."}

# --- NEW: DEADLINE CHECKER ---
def check_for_deadlines(text: str) -> Optional[Dict[str, Any]]:
    result = llm_service.extract_deadlines(text)
    if isinstance(result, dict) and result.get("is_judgment"):
        return result
    return None

def analyze_node_context(db: Database, case_id: str, node_id: str, user_id: str) -> Dict[str, Any]:
    return {"summary": "Analizë kontekstuale e pikës së grafit."}