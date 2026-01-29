# FILE: backend/app/services/analysis_service.py
# PHOENIX PROTOCOL - ANALYSIS SERVICE V21.0 (PIPELINE DECOUPLING)
# 1. DECOUPLED: Removed graph creation from `cross_examine_case` to restore its original function.
# 2. ADDED: Created a dedicated, high-integrity `build_and_get_graph` function for the Evidence Map.
# 3. STATUS: Clean separation of concerns. Text analysis and Graph analysis are now independent.

import structlog
from typing import List, Dict, Any
from pymongo.database import Database
from bson import ObjectId

import app.services.llm_service as llm_service
from .graph_service import graph_service

logger = structlog.get_logger(__name__)

# --- UTILITIES ---
def _get_full_case_text(db: Database, case_id: str) -> str:
    try:
        docs = list(db.documents.find({"case_id": ObjectId(case_id)}))
        if not docs: docs = list(db.documents.find({"case_id": case_id}))
        
        buffer = [f"\n--- DOKUMENTI: {d.get('file_name')} ---\n{str(d.get('extracted_text') or d.get('summary') or '')[:8000]}" for d in docs if d.get("extracted_text") or d.get("summary")]
        return "\n".join(buffer)
    except Exception: 
        return ""

def authorize_case_access(db: Database, case_id: str, user_id: str) -> bool:
    try:
        case = db.cases.find_one({"_id": ObjectId(case_id), "user_id": ObjectId(user_id)})
        return case is not None
    except Exception:
        return False

# --- DEDICATED GRAPH BUILDER (CALLED BY EVIDENCE MAP) ---
def build_and_populate_graph(db: Database, case_id: str, user_id: str) -> bool:
    """
    The core AI engine for the Evidence Map. Extracts text, calls the AI to create a graph,
    and ingests it into Neo4j. Returns True on success.
    """
    if not authorize_case_access(db, case_id, user_id):
        logger.warning("Unauthorized attempt to build graph", case_id=case_id)
        return False

    full_text = _get_full_case_text(db, case_id)
    if not full_text:
        logger.info("No text content to build graph from", case_id=case_id)
        return False

    try:
        logger.info("Requesting graph data from LLM", case_id=case_id)
        graph_data = llm_service.extract_graph_data(full_text)
        
        nodes = graph_data.get("nodes", [])
        relations = graph_data.get("edges", [])

        if not nodes:
            logger.warning("LLM returned no nodes for graph", case_id=case_id)
            return False

        # Ingest the extracted data into Neo4j
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
    """
    This function is ONLY for the textual 'Analizo Rastin' report.
    It no longer touches the graph database.
    """
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
    # This function's logic remains the same
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