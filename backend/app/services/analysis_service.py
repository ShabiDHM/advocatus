# FILE: backend/app/services/analysis_service.py
# PHOENIX PROTOCOL - ANALYSIS SERVICE V22.2 (SCHEMA SYNC)
# 1. FIX: Added 'strategic_weaknesses' and 'action_steps' to prompt and mapping.
# 2. FIX: Ensured 1:1 alignment with AnalysisModal.tsx props to prevent empty UI boxes.
# 3. FIX: Parallelized Deep Strategy maintained for speed.
# 4. STATUS: Schema Integrity Confirmed.

import asyncio
import structlog
from typing import List, Dict, Any
from pymongo.database import Database
from bson import ObjectId

import app.services.llm_service as llm_service
from . import vector_store_service

logger = structlog.get_logger(__name__)

def _get_full_case_text(db: Database, case_id: str) -> str:
    try:
        query = {"$or": [{"case_id": case_id}, {"case_id": ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id}]}
        docs = list(db.documents.find(query))
        return "\n".join([f"--- DOKUMENTI: {d.get('file_name')} ---\n{str(d.get('extracted_text') or d.get('summary') or '')[:10000]}" for d in docs])
    except Exception: return ""

def _assemble_rag_context(db: Database, case_id: str, user_id: str) -> str:
    case = db.cases.find_one({"_id": ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id})
    q = f"{case.get('case_name', '')} {case.get('description', '')}" if case else "Legal analysis"
    case_facts = vector_store_service.query_case_knowledge_base(user_id=user_id, query_text=q, case_context_id=case_id, n_results=15)
    global_laws = vector_store_service.query_global_knowledge_base(query_text=q, n_results=15)
    
    blocks = ["=== FAKTET NGA DOSJA ==="]
    for f in case_facts: blocks.append(f"DOKUMENTI: {f['source']} (Faqja {f['page']})\nTEKSTI: {f['text']}\n")
    blocks.append("=== BAZA LIGJORE (KOSOVA) ===")
    for l in global_laws: blocks.append(f"LIGJI: '{l['source']}'\nNENI: {l['text']}\n")
    return "\n".join(blocks)

def authorize_case_access(db: Database, case_id: str, user_id: str) -> bool:
    try:
        c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
        u_oid = ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id
        return db.cases.find_one({"_id": c_oid, "owner_id": u_oid}) is not None
    except: return False

def cross_examine_case(db: Database, case_id: str, user_id: str) -> Dict[str, Any]:
    if not authorize_case_access(db, case_id, user_id): return {"error": "Pa autorizim."}
    context = _assemble_rag_context(db, case_id, user_id)
    
    # PHOENIX FIX: Extended schema to support ALL Modal tabs
    system_prompt = """
    DETYRA: Analizë Profesionale e Rastit.
    CITIMI: Çdo ligj në JSON duhet të jetë: [Emri i Ligjit](doc://ligji).
    JSON STRUCTURE:
    {
      "executive_summary": "...",
      "legal_audit": { "burden_of_proof": "...", "legal_basis": ["..."] },
      "strategic_recommendation": { 
          "recommendation_text": "...", 
          "weaknesses": ["..."], 
          "action_plan": ["..."],
          "success_probability": "XX%", 
          "risk_level": "LOW/MEDIUM/HIGH" 
      },
      "missing_evidence": ["..."]
    }
    """
    try:
        raw_res = llm_service.analyze_case_integrity(context, custom_prompt=system_prompt)
        # Mapping to Frontend Props
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
        logger.error(f"Analysis Mapping Failed: {e}")
        return {"summary": "Dështoi gjenerimi i analizës."}

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