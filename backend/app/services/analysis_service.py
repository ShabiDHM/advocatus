# FILE: backend/app/services/analysis_service.py
# PHOENIX PROTOCOL - ANALYSIS SERVICE V22.7 (GRAPH INTEGRATION)
# 1. FIX: Restored 'build_and_populate_graph' to bridge Documents and Neo4j.
# 2. FIX: Mandated 'Statutory reasoning' - AI must explain HOW the law applies to the facts.
# 3. STATUS: Synchronous logic verified.

import asyncio
import structlog
from typing import List, Dict, Any
from pymongo.database import Database
from bson import ObjectId
import app.services.llm_service as llm_service
from . import vector_store_service

logger = structlog.get_logger(__name__)

def _assemble_rag_context(db: Database, case_id: str, user_id: str) -> str:
    case = db.cases.find_one({"_id": ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id})
    q = f"{case.get('case_name', '')} {case.get('description', '')}" if case else "Legal analysis"
    # Depth upgraded to n=15 for deep statutory lookup
    case_facts = vector_store_service.query_case_knowledge_base(user_id=user_id, query_text=q, case_context_id=case_id, n_results=15)
    global_laws = vector_store_service.query_global_knowledge_base(query_text=q, n_results=15)
    
    blocks = ["=== FAKTE NGA DOSJA ==="]
    for f in case_facts: blocks.append(f"DOKUMENTI: {f['source']} (Faqja {f['page']})\nTEKSTI: {f['text']}\n")
    blocks.append("=== BAZA LIGJORE STATUTORE ===")
    for l in global_laws: blocks.append(f"BURIMI LIGJOR: '{l['source']}'\nNENI/TEKSTI: {l['text']}\n")
    return "\n".join(blocks)

def authorize_case_access(db: Database, case_id: str, user_id: str) -> bool:
    try:
        c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
        u_oid = ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id
        return db.cases.find_one({"_id": c_oid, "owner_id": u_oid}) is not None
    except: return False

def build_and_populate_graph(db: Database, case_id: str, user_id: str) -> bool:
    """
    Synchronously extracts entities from all case documents and populates the Graph DB.
    """
    if not authorize_case_access(db, case_id, user_id):
        logger.warning("Unauthorized graph build attempt", case_id=case_id, user_id=user_id)
        return False

    try:
        from .document_service import get_document_content_by_key
        from .graph_service import graph_service
        
        # 1. Fetch all processed documents for the case
        doc_cursor = db.documents.find({"case_id": ObjectId(case_id)})
        docs = list(doc_cursor)
        
        if not docs:
            logger.info("No documents found to build graph", case_id=case_id)
            return False

        for doc in docs:
            text_key = doc.get("processed_text_storage_key")
            if not text_key:
                continue
            
            # 2. Retrieve Text Content
            content = get_document_content_by_key(text_key)
            if not content:
                continue

            # 3. Extract Graph Data (Nodes/Edges) via LLM
            # llm_service.extract_graph_data returns {'nodes': [], 'edges': []}
            graph_data = llm_service.extract_graph_data(content)
            
            entities = graph_data.get("nodes", [])
            relations = graph_data.get("edges", [])

            if not entities:
                continue

            # 4. Ingest into Neo4j
            graph_service.ingest_entities_and_relations(
                case_id=str(case_id),
                document_id=str(doc["_id"]),
                doc_name=doc.get("file_name", "Unknown"),
                entities=entities,
                relations=relations
            )
            
        logger.info("Graph population complete", case_id=case_id)
        return True
        
    except Exception as e:
        logger.error(f"Failed to build graph: {e}", exc_info=True)
        return False

def cross_examine_case(db: Database, case_id: str, user_id: str) -> Dict[str, Any]:
    """
    SENIOR PARTNER CROSS-EXAMINATION:
    Produces a high-IQ analysis where every law is mapped to case relevance.
    """
    if not authorize_case_access(db, case_id, user_id): return {"error": "Pa autorizim."}
    context = _assemble_rag_context(db, case_id, user_id)
    
    # PHOENIX MANDATE: No citations without reasoning.
    system_prompt = """
    DETYRA: Analizë Gjyqësore e Integritetit.
    MANDATI: Mos jep vetëm emrin e ligjit. Duhet të shpjegosh 'RELEVANCËN' për këtë rast specifik.
    
    JSON SCHEMA (STRIKT):
    {
      "executive_summary": "...",
      "legal_audit": { 
          "burden_of_proof": "...", 
          "legal_basis": [
              {
                "title": "[Emri i Ligjit, Nr, Neni](doc://ligji)",
                "article": "Përmbledhja e asaj që thotë neni...",
                "relevance": "Pse ky nen është thelbësor për këtë rast specifik të palës..."
              }
          ] 
      },
      "strategic_recommendation": { 
          "recommendation_text": "...", 
          "weaknesses": ["[Ligji/Fakti](doc://ligji) - Detaje", "..."], 
          "action_plan": ["..."],
          "success_probability": "XX%", 
          "risk_level": "LOW/MEDIUM/HIGH" 
      },
      "missing_evidence": ["..."]
    }
    """
    try:
        # Pass context and strict prompt to LLM
        raw_res = llm_service.analyze_case_integrity(context, custom_prompt=system_prompt)
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
    if not authorize_case_access(db, case_id, user_id): return {"error": "Pa autorizim."}
    context = _assemble_rag_context(db, case_id, user_id)
    try:
        tasks = [
            asyncio.to_thread(llm_service.generate_adversarial_simulation, context),
            asyncio.to_thread(llm_service.build_case_chronology, context),
            asyncio.to_thread(llm_service.detect_contradictions, context)
        ]
        adv, chr_res, cnt = await asyncio.gather(*tasks)
        return {
            "adversarial_simulation": adv if isinstance(adv, dict) else {},
            "chronology": chr_res.get("timeline", []) if isinstance(chr_res, dict) else [],
            "contradictions": cnt.get("contradictions", []) if isinstance(cnt, dict) else []
        }
    except Exception: return {"error": "Dështoi analiza e thellë."}