# FILE: backend/app/services/analysis_service.py
# PHOENIX PROTOCOL - ANALYSIS SERVICE V19.0 (STABILITY & CRASH PREVENTION)
# 1. FIX: Implemented "Safe Object Factory" in run_deep_strategy to prevent Frontend .map() crashes.
# 2. FIX: Guaranteed that all nested lists (weakness_attacks, counter_claims, etc.) are always present.
# 3. STATUS: 100% synchronized with AnalysisModal.tsx V9.0 requirements.

import structlog
import hashlib
import time
import asyncio
from typing import List, Dict, Any, Optional, Tuple, cast
from pymongo.database import Database
from bson import ObjectId

import app.services.llm_service as llm_service
from .graph_service import graph_service

logger = structlog.get_logger(__name__)

# --- CACHING LAYER ---
class AnalysisCache:
    def __init__(self): 
        self.cache: Dict[str, Any] = {}
        
    def get_key(self, case_id: str, user_id: str, mode: str) -> str: 
        return hashlib.md5(f"{case_id}:{user_id}:{mode}".encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Dict[str, Any]]: 
        return self.cache.get(key)
    
    def set(self, key: str, value: Dict[str, Any]): 
        self.cache[key] = value

analysis_cache = AnalysisCache()

# --- SECURITY & AUTH ---
def authorize_case_access(db: Database, case_id: str, user_id: str) -> Tuple[bool, Dict[str, Any]]:
    try:
        c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
        u_oid = ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id
        
        case = db.cases.find_one({"_id": c_oid, "$or": [{"user_id": u_oid}, {"user_id": str(u_oid)}]})
        if case: return True, cast(Dict[str, Any], case)
        
        user = db.users.find_one({"_id": u_oid})
        if user and user.get("role") == "ADMIN":
            admin_case = db.cases.find_one({"_id": c_oid})
            if admin_case: return True, cast(Dict[str, Any], admin_case)
            
        return False, {"error": "Nuk keni akses në këtë rast."}
    except Exception: 
        return False, {"error": "Gabim gjatë autorizimit."}

# --- TEXT EXTRACTION ---
def _get_full_case_text(db: Database, case_id: str) -> str:
    try:
        docs = list(db.documents.find({"case_id": ObjectId(case_id)}))
        if not docs: docs = list(db.documents.find({"case_id": str(case_id)}))
        
        buffer = []
        for d in docs:
            txt = d.get("extracted_text") or d.get("ocr_text") or d.get("summary") or ""
            if len(str(txt)) > 20: 
                buffer.append(f"\n=== DOKUMENTI: {d.get('file_name')} ===\n{str(txt)[:6000]}")
        return "\n".join(buffer)
    except Exception: 
        return ""

# --- MAIN ANALYSIS FUNCTION (Legal Analysis Tab) ---
def cross_examine_case(
    db: Database, 
    case_id: str, 
    user_id: str,
    force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Standard legal integrity check.
    Ensures all keys required by AnalysisModal.tsx are initialized.
    """
    start_time = time.time()
    auth_ok, auth_res = authorize_case_access(db, case_id, user_id)
    if not auth_ok: return auth_res
    
    cache_key = analysis_cache.get_key(case_id, user_id, "standard")
    if not force_refresh:
        if cached := analysis_cache.get(cache_key): return cached

    full_text = _get_full_case_text(db, case_id)
    if not full_text: 
        return {"summary": "Shtoni dokumente për të filluar analizën.", "risk_level": "LOW"}

    result: Dict[str, Any] = {}
    try:
        ai_res = llm_service.analyze_case_integrity(full_text)
        result = ai_res if isinstance(ai_res, dict) else {}
    except Exception: 
        logger.error("LLM Standard Analysis failed")
        result = {}

    # PHOENIX: GUARANTEED FRONTEND KEYS ENFORCEMENT
    # This block prevents UI crashes in the 'Legal Analysis' tab
    if not result.get("summary"): result["summary"] = "Analiza po përgatitet..."
    if not result.get("key_issues") or not isinstance(result["key_issues"], list): result["key_issues"] = []
    if not result.get("legal_basis") or not isinstance(result["legal_basis"], list): result["legal_basis"] = []
    if not result.get("strategic_analysis"): result["strategic_analysis"] = "Strategjia kërkon shqyrtim manual."
    if not result.get("weaknesses") or not isinstance(result["weaknesses"], list): result["weaknesses"] = []
    if not result.get("action_plan") or not isinstance(result["action_plan"], list): result["action_plan"] = []
    if not result.get("risk_level"): result["risk_level"] = "MEDIUM"

    result["processing_time_ms"] = int((time.time() - start_time) * 1000)
    analysis_cache.set(cache_key, result)
    return result

# --- DEEP STRATEGIC ANALYSIS (War Room Tab) ---
async def run_deep_strategy(db: Database, case_id: str, user_id: str) -> Dict[str, Any]:
    """
    Runs Agents: Adversarial, Chronology, Contradictions.
    Garanton që struktura e kthyer të mos shkaktojë crash në React.
    """
    auth_ok, _ = authorize_case_access(db, case_id, user_id)
    if not auth_ok: return {"error": "Pa autorizim."}
    
    full_text = _get_full_case_text(db, case_id)
    if not full_text: return {"error": "Mungojnë dokumentet."}
    
    try:
        # Execute LLM Agents
        adv = llm_service.generate_adversarial_simulation(full_text)
        chr_res = llm_service.build_case_chronology(full_text)
        cnt = llm_service.detect_contradictions(full_text)
        
        # PHOENIX STABILITY FIX: Initialize standard adversarial structure
        # Even if AI fails, this prevents "undefined .map()" error in frontend
        safe_adv = adv if isinstance(adv, dict) else {}
        
        final_adversarial = {
            "opponent_strategy": safe_adv.get("opponent_strategy", "Nuk u identifikua strategji kundërshtare."),
            "weakness_attacks": safe_adv.get("weakness_attacks") if isinstance(safe_adv.get("weakness_attacks"), list) else [],
            "counter_claims": safe_adv.get("counter_claims") if isinstance(safe_adv.get("counter_claims"), list) else []
        }

        return {
            "adversarial_simulation": final_adversarial,
            "chronology": chr_res.get("timeline", []) if isinstance(chr_res, dict) else [],
            "contradictions": cnt.get("contradictions", []) if isinstance(cnt, dict) else []
        }
    except Exception as e:
        logger.error(f"Deep Strategy failed: {e}")
        # Return fallback with valid empty arrays to keep UI stable
        return {
            "adversarial_simulation": {"opponent_strategy": "Gabim AI", "weakness_attacks": [], "counter_claims": []},
            "chronology": [],
            "contradictions": []
        }

def check_for_deadlines(text: str) -> Optional[Dict[str, Any]]:
    result = llm_service.extract_deadlines(text)
    return result if isinstance(result, dict) and result.get("is_judgment") else None

def analyze_node_context(db: Database, case_id: str, node_id: str, user_id: str) -> Dict[str, Any]:
    return {"summary": "Analizë kontekstuale."}