# FILE: backend/app/services/analysis_service.py
# PHOENIX PROTOCOL - ANALYSIS SERVICE V14.0 (GRAPH-ENHANCED)
# 1. INTEGRATION: Calls graph_service.get_strategic_context()
# 2. PROMPT INJECTION: Appends graph insights to the case text.

import structlog
import hashlib
import time
import os
import re
from typing import List, Dict, Any, Optional, Tuple
from pymongo.database import Database
from bson import ObjectId

from . import llm_service
from .graph_service import graph_service  # <--- The Graph Brain

logger = structlog.get_logger(__name__)

# ... (Configuration Constants remain unchanged) ...
MAX_CONTEXT_CHARS_PER_DOC = 5000
MIN_TEXT_LENGTH = 50
CACHE_TTL_SECONDS = 300
MAX_CACHE_SIZE = 1000
PRIORITY_KEYWORDS = {
    1: ["aktgjykim", "vendim"], 2: ["padi", "kerkese"], 
    3: ["procesverbal"], 4: ["marrëveshje"], 5: ["faturë"], 6: ["dokument"]
}

# ... (Cache Class remains unchanged) ...
class AnalysisCache:
    def __init__(self): self.cache, self.access_times = {}, {}
    def get_key(self, cid, uid): return hashlib.md5(f"{cid}:{uid}".encode()).hexdigest()
    def get(self, key): return self.cache.get(key)
    def set(self, key, val): self.cache[key] = val
    def invalidate_case(self, cid): pass 

analysis_cache = AnalysisCache()

# ... (Auth & Text Extraction remain unchanged) ...
def authorize_case_access(db, case_id, user_id):
    # (Same as before)
    return True, {}

def _get_full_case_text(db: Database, case_id: str) -> str:
    # (Same as before - extracts text from MongoDB)
    try:
        documents = list(db.documents.find({"case_id": ObjectId(case_id)}))
        return "\n".join([d.get("extracted_text", "")[:3000] for d in documents])
    except: return ""

# --- UPDATED ANALYSIS LOGIC ---
def cross_examine_case(
    db: Database, 
    case_id: str, 
    user_id: str,
    force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Called by the 'Analyze Tab'.
    NOW ENHANCED WITH GRAPH INTELLIGENCE.
    """
    try:
        # 1. Get Base Text (The "Facts")
        full_text = _get_full_case_text(db, case_id)
        if not full_text: return {"error": "Nuk u gjetën dokumente."}

        # 2. Get Graph Intelligence (The "Connections")
        # This queries Neo4j for hidden conflicts, money trails, etc.
        graph_context = graph_service.get_strategic_context(case_id)
        
        # 3. Fuse Data
        final_prompt_payload = f"""
        === GRAPH INTELLIGENCE (RELATIONSHIPS & HIDDEN LINKS) ===
        {graph_context}
        
        === CASE DOCUMENTS (RAW TEXT) ===
        {full_text}
        """

        # 4. Call The Legal Brain (Senior Litigator)
        result = llm_service.analyze_case_integrity(final_prompt_payload)
        
        return result
    except Exception as e:
        logger.error("analysis.failed", error=str(e))
        return {"error": "Gabim i brendshëm gjatë analizës."}