# FILE: backend/app/services/analysis_service.py
# PHOENIX PROTOCOL - ANALYSIS SERVICE V18.1 (DATA RECOVERY & RESTORATION)
# 1. FIX: Implemented "Data Recovery" to handle AI responses that return Lists instead of Dicts.
# 2. FIX: Ensured mandatory frontend fields (summary, key_issues, legal_basis) are never null.
# 3. STATUS: Full intelligence restored. Integrated with LLM Service V38.0.

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
        
        case = db.cases.find_one({
            "_id": case_oid,
            "$or": [{"user_id": user_oid}, {"user_id": str(user_oid)}]
        })
        
        if case:
            return True, cast(Dict[str, Any], case)
        
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

# --- MAIN ANALYSIS FUNCTION ---
def cross_examine_case(
    db: Database, 
    case_id: str, 
    user_id: str,
    force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Standard legal integrity check.
    Upgraded with Data Recovery logic to prevent empty UI on malformed AI JSON.
    """
    start_time = time.time()
    
    # 1. Auth & Cache
    authorized, auth_result = authorize_case_access(db, case_id, user_id)
    if not authorized: return auth_result
    
    cache_key = analysis_cache.get_key(case_id, user_id, "standard")
    if not force_refresh:
        if cached := analysis_cache.get(cache_key): return cached

    # 2. Data
    full_text = _get_full_case_text(db, case_id)
    if not full_text:
        return {"summary": "Shtoni dokumente për analizë.", "risk_level": "LOW", "error": "Mungesë të dhënash"}

    # 3. Intelligence
    try:
        result = llm_service.analyze_case_integrity(full_text)
    except Exception as e:
        logger.error(f"LLM Crash: {e}")
        result = None
    
    # 4. PHOENIX DATA RECOVERY (The Critical Fix)
    if isinstance(result, list):
        # AI returned a list of points instead of a dict. Map them to key_issues.
        logger.info("Data Recovery: Converting AI List to Dict")
        result = {
            "summary": "Analiza u gjenerua si listë pikash.",
            "key_issues": result,
            "legal_basis": [],
            "strategic_analysis": "Rishikoni pikat e identifikuara më poshtë.",
            "risk_level": "MEDIUM"
        }
    
    if not isinstance(result, dict):
        # AI failed completely or returned a string
        result = {
            "summary": "Analiza nuk mundi të strukturohej.",
            "key_issues": ["Gabim formati"],
            "legal_basis": [],
            "strategic_analysis": "Përgjigja e AI ishte e paqartë. Provoni përsëri.",
            "risk_level": "UNKNOWN"
        }

    # 5. Mandatory Field Enforcement
    # Ensure UI always has something to show
    if not result.get("key_issues"): result["key_issues"] = ["Nuk u identifikuan çështje specifike."]
    if not result.get("legal_basis"): result["legal_basis"] = ["Baza ligjore do të përcaktohet pas rishikimit."]
    if not result.get("summary"): result["summary"] = "Përmbledhja nuk është gati."
    if not result.get("strategic_analysis"): result["strategic_analysis"] = "Strategjia kërkon më shumë të dhëna."

    # 6. Finalize
    result["processing_time_ms"] = int((time.time() - start_time) * 1000)
    analysis_cache.set(cache_key, result)
    return result

# --- DEEP STRATEGIC ANALYSIS ---
async def run_deep_strategy(db: Database, case_id: str, user_id: str) -> Dict[str, Any]:
    authorized, _ = authorize_case_access(db, case_id, user_id)
    if not authorized: return {"error": "Unauthorized"}

    full_text = _get_full_case_text(db, case_id)
    if not full_text: return {"error": "No documents found."}

    try:
        # PHOENIX: Run all agents with the restored logic
        adv = llm_service.generate_adversarial_simulation(full_text)
        chr = llm_service.build_case_chronology(full_text)
        cnt = llm_service.detect_contradictions(full_text)
        
        return {
            "adversarial_simulation": adv if isinstance(adv, dict) else {"opponent_strategy": "Dështoi strukturimi", "weakness_attacks": []},
            "chronology": chr.get("timeline", []) if isinstance(chr, dict) else [],
            "contradictions": cnt.get("contradictions", []) if isinstance(cnt, dict) else []
        }
    except Exception as e:
        logger.error(f"Deep Strategy Failed: {e}")
        return {"error": "Shërbimi nuk u përgjigj."}

# --- DEADLINE CHECKER ---
def check_for_deadlines(text: str) -> Optional[Dict[str, Any]]:
    result = llm_service.extract_deadlines(text)
    if isinstance(result, dict) and result.get("is_judgment"):
        return result
    return None

def analyze_node_context(db: Database, case_id: str, node_id: str, user_id: str) -> Dict[str, Any]:
    return {"summary": "Analizë e pikës specifike të grafit."}