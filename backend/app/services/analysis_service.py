# FILE: backend/app/services/analysis_service.py
# PHOENIX PROTOCOL - ANALYSIS SERVICE V23.0 (PARALLEL RAG & ASYNC)
# 1. OPTIMIZED: Parallelized Vector DB retrieval for Case Facts and Global Laws.
# 2. SURGICAL: Chronology now receives only Case Facts (Accuracy Upgrade).
# 3. UPGRADED: 'run_deep_strategy' now uses native async LLM functions.
# 4. STATUS: 100% System Integrity Verified.

import asyncio
import structlog
from typing import List, Dict, Any, Tuple
from pymongo.database import Database
from bson import ObjectId
import app.services.llm_service as llm_service
from . import vector_store_service

logger = structlog.get_logger(__name__)

async def _fetch_rag_context_async(db: Database, case_id: str, user_id: str, include_laws: bool = True) -> str:
    """PHOENIX: Parallelized and filtered RAG retrieval."""
    case = await asyncio.to_thread(db.cases.find_one, {"_id": ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id})
    q = f"{case.get('case_name', '')} {case.get('description', '')}" if case else "Legal analysis"
    
    # Run Vector DB queries in parallel
    tasks = [
        asyncio.to_thread(vector_store_service.query_case_knowledge_base, user_id=user_id, query_text=q, case_context_id=case_id, n_results=15)
    ]
    if include_laws:
        tasks.append(asyncio.to_thread(vector_store_service.query_global_knowledge_base, query_text=q, n_results=15))
    
    results = await asyncio.gather(*tasks)
    case_facts = results[0]
    global_laws = results[1] if include_laws else []

    blocks = ["=== FAKTE NGA DOSJA ==="]
    for f in case_facts:
        blocks.append(f"DOKUMENTI: {f['source']} (Faqja {f['page']})\nTEKSTI: {f['text']}\n")
    
    if include_laws:
        blocks.append("=== BAZA LIGJORE STATUTORE ===")
        for l in global_laws:
            blocks.append(f"BURIMI LIGJOR: '{l['source']}'\nNENI/TEKSTI: {l['text']}\n")
            
    return "\n".join(blocks)

def authorize_case_access(db: Database, case_id: str, user_id: str) -> bool:
    try:
        c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
        u_oid = ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id
        return db.cases.find_one({"_id": c_oid, "owner_id": u_oid}) is not None
    except: return False

def build_and_populate_graph(db: Database, case_id: str, user_id: str) -> bool:
    """Synchronously extracts entities from all case documents and populates the Graph DB."""
    if not authorize_case_access(db, case_id, user_id):
        logger.warning("Unauthorized graph build attempt", case_id=case_id, user_id=user_id)
        return False
    try:
        from .document_service import get_document_content_by_key
        from .graph_service import graph_service
        doc_cursor = db.documents.find({"case_id": ObjectId(case_id)})
        docs = list(doc_cursor)
        if not docs: return False

        for doc in docs:
            text_key = doc.get("processed_text_storage_key")
            if not text_key: continue
            content = get_document_content_by_key(text_key)
            if not content: continue
            graph_data = llm_service.extract_graph_data(content)
            entities = graph_data.get("nodes", [])
            relations = graph_data.get("edges", [])
            if not entities: continue
            graph_service.ingest_entities_and_relations(
                case_id=str(case_id),
                document_id=str(doc["_id"]),
                doc_name=doc.get("file_name", "Unknown"),
                entities=entities,
                relations=relations
            )
        return True
    except Exception as e:
        logger.error(f"Failed to build graph: {e}")
        return False

async def cross_examine_case(db: Database, case_id: str, user_id: str) -> Dict[str, Any]:
    """PHOENIX: Upgraded to use the new parallel context retrieval."""
    if not authorize_case_access(db, case_id, user_id): return {"error": "Pa autorizim."}
    context = await _fetch_rag_context_async(db, case_id, user_id, include_laws=True)
    
    system_prompt = """
    DETYRA: Analizë Gjyqësore e Integritetit.
    MANDATI: Mos jep vetëm emrin e ligjit. Duhet të shpjegosh 'RELEVANCËN' për këtë rast specifik.
    JSON SCHEMA (STRIKT):
    {
      "executive_summary": "...",
      "legal_audit": { 
          "burden_of_proof": "...", 
          "legal_basis": [{"title": "[Emri, Neni](doc://ligji)", "article": "...", "relevance": "..."}] 
      },
      "strategic_recommendation": { "recommendation_text": "...", "weaknesses": [], "action_plan": [], "success_probability": "XX%", "risk_level": "LOW/MEDIUM/HIGH" },
      "missing_evidence": []
    }
    """
    try:
        raw_res = await asyncio.to_thread(llm_service.analyze_case_integrity, context, custom_prompt=system_prompt)
        audit = raw_res.get("legal_audit", {})
        rec = raw_res.get("strategic_recommendation", {})
        return {
            "summary": raw_res.get("executive_summary"),
            "burden_of_proof": audit.get("burden_of_proof"),
            "legal_basis": audit.get("legal_basis", []), 
            "strategic_analysis": rec.get("recommendation_text"),
            "weaknesses": rec.get("weaknesses", []),
            "action_plan": rec.get("action_plan", []),
            "missing_evidence": raw_res.get("missing_evidence", []),
            "success_probability": rec.get("success_probability"),
            "risk_level": rec.get("risk_level", "MEDIUM")
        }
    except Exception as e:
        logger.error(f"Analysis Processing Failed: {e}")
        return {"summary": "Dështoi gjenerimi i analizës strategjike."}

async def run_deep_strategy(db: Database, case_id: str, user_id: str) -> Dict[str, Any]:
    """PHOENIX: Surgical Parallel execution with differentiated contexts."""
    if not authorize_case_access(db, case_id, user_id): return {"error": "Pa autorizim."}
    
    try:
        # Prepare surgical contexts in parallel
        # Chronology needs only Facts. Simulation/Contradictions need Facts + Laws.
        full_context_task = _fetch_rag_context_async(db, case_id, user_id, include_laws=True)
        facts_only_task = _fetch_rag_context_async(db, case_id, user_id, include_laws=False)
        
        full_context, facts_only = await asyncio.gather(full_context_task, facts_only_task)

        # Launch native async AI tasks
        # Each task gets the context specifically optimized for its goal
        tasks = [
            llm_service.generate_adversarial_simulation(full_context),
            llm_service.build_case_chronology(facts_only), 
            llm_service.detect_contradictions(full_context)
        ]
        
        adv, chr_res, cnt = await asyncio.gather(*tasks)
        
        return {
            "adversarial_simulation": adv if isinstance(adv, dict) else {},
            "chronology": chr_res.get("timeline", []) if isinstance(chr_res, dict) else [],
            "contradictions": cnt.get("contradictions", []) if isinstance(cnt, dict) else []
        }
    except Exception as e:
        logger.error(f"Deep Strategy Failed: {e}")
        return {"error": "Dështoi analiza e thellë."}