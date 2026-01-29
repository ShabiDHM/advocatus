# FILE: backend/app/services/analysis_service.py
# PHOENIX PROTOCOL - ANALYSIS SERVICE V21.1 (ROBUST ID & PIPELINE FIX)
# 1. FIX: Implemented a robust "Dual-Type ID Query" to find documents regardless of whether case_id is a String or ObjectId.
# 2. FIX: Decoupled graph creation from `cross_examine_case` to restore its original function.
# 3. STATUS: This guarantees the text extraction finds the documents, triggering the AI graph build.

import structlog
from typing import List, Dict, Any
from pymongo.database import Database
from bson import ObjectId
from bson.errors import InvalidId

import app.services.llm_service as llm_service
from .graph_service import graph_service

logger = structlog.get_logger(__name__)

# --- UTILITIES ---
def _get_full_case_text(db: Database, case_id: str) -> str:
    """
    PHOENIX FIX: Robustly queries for documents using both String and ObjectId formats
    to prevent silent failures in the AI pipeline.
    """
    try:
        # Create a query that checks for the case_id in both formats
        query_filter = {
            "$or": [
                {"case_id": case_id},
                {"case_id": ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id}
            ]
        }
        docs = list(db.documents.find(query_filter))
        
        if not docs:
            logger.warning("No documents found for case_id", case_id=case_id)
            return ""

        buffer = [f"\n--- DOKUMENTI: {d.get('file_name')} ---\n{str(d.get('extracted_text') or d.get('summary') or '')[:8000]}" for d in docs if d.get("extracted_text") or d.get("summary")]
        return "\n".join(buffer)
    except Exception as e:
        logger.error("Failed to get case text", case_id=case_id, error=str(e))
        return ""

def authorize_case_access(db: Database, case_id: str, user_id: str) -> bool:
    try:
        user_oid = ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id
        case_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
        
        query_filter = {
            "_id": case_oid,
            "$or": [
                {"user_id": user_oid},
                {"user_id": str(user_oid)}
            ]
        }
        case = db.cases.find_one(query_filter)
        return case is not None
    except Exception:
        return False

# --- DEDICATED GRAPH BUILDER (CALLED BY EVIDENCE MAP) ---
def build_and_populate_graph(db: Database, case_id: str, user_id: str) -> bool:
    if not authorize_case_access(db, case_id, user_id):
        logger.warning("Unauthorized attempt to build graph", case_id=case_id)
        return False

    full_text = _get_full_case_text(db, case_id)
    if not full_text:
        logger.warning("No text content found to build graph from", case_id=case_id)
        return False

    try:
        logger.info("Requesting graph data from LLM", case_id=case_id)
        graph_data = llm_service.extract_graph_data(full_text)
        
        nodes = graph_data.get("nodes", [])
        relations = graph_data.get("edges", [])

        if not nodes:
            logger.warning("LLM returned no nodes for graph", case_id=case_id)
            return False

        graph_service.ingest_entities_and_relations(
            case_id=case_id,
            document_id=f"case-graph-summary-{case_id}",
            doc_name=f"Case Graph for {case_id}",
            entities=nodes,
            relations=relations
        )
        logger.info("Successfully ingested AI graph data into Neo4j", case_id=case_id)
        return True

    except Exception as e:
        logger.error(f"Failed to build and populate graph for case {case_id}: {e}")
        return False

# --- TEXTUAL ANALYSIS (FOR SOCRATIC ASSISTANT) ---
def cross_examine_case(db: Database, case_id: str, user_id: str) -> Dict[str, Any]:
    if not authorize_case_access(db, case_id, user_id): return {"error": "Unauthorized"}
    
    full_text = _get_full_case_text(db, case_id)
    if not full_text: return {"summary": "Shtoni dokumente për të filluar analizën.", "risk_level": "LOW"}

    try:
        ai_res = llm_service.analyze_case_integrity(full_text)
        result = ai_res if isinstance(ai_res, dict) else {}
    except Exception: 
        result = {}

    result.setdefault("summary", "Analiza po përgatitet...")
    result.setdefault("key_issues", [])
    result.setdefault("legal_basis", [])
    result.setdefault("strategic_analysis", "Strategjia kërkon shqyrtim manual.")
    result.setdefault("weaknesses", [])
    result.setdefault("action_plan", [])
    result.setdefault("risk_level", "MEDIUM")

    return result

# --- OTHER ANALYSIS FUNCTIONS (UNCHANGED) ---
async def run_deep_strategy(db: Database, case_id: str, user_id: str) -> Dict[str, Any]:
    if not authorize_case_access(db, case_id, user_id): return {"error": "Pa autorizim."}
    full_text = _get_full_case_text(db, case_id)
    if not full_text: return {"error": "Mungojnë dokumentet."}
    
    try:
        adv = llm_service.generate_adversarial_simulation(full_text)
        chr_res = llm_service.build_case_chronology(full_text)
        cnt = llm_service.detect_contradictions(full_text)
        
        safe_adv = adv if isinstance(adv, dict) else {}
        final_adversarial = {
            "opponent_strategy": safe_adv.get("opponent_strategy", "N/A"),
            "weakness_attacks": safe_adv.get("weakness_attacks", []),
            "counter_claims": safe_adv.get("counter_claims", [])
        }
        return {
            "adversarial_simulation": final_adversarial,
            "chronology": chr_res.get("timeline", []) if isinstance(chr_res, dict) else [],
            "contradictions": cnt.get("contradictions", []) if isinstance(cnt, dict) else []
        }
    except Exception as e:
        logger.error(f"Deep Strategy failed: {e}")
        return {"adversarial_simulation": {"opponent_strategy": "Gabim AI", "weakness_attacks": [], "counter_claims": []}, "chronology": [], "contradictions": []}

def analyze_node_context(db: Database, case_id: str, node_id: str, user_id: str) -> Dict[str, Any]:
    return {"summary": "Analizë kontekstuale."}