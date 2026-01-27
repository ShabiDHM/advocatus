# FILE: backend/app/services/evidence_map_service.py
# PHOENIX PROTOCOL - EVIDENCE MAP SERVICE V3.0 (GLOBAL RAG FINAL INTEGRATION)
# 1. FIX: Added 'BaseModel' import to resolve Pylance error.
# 2. FIX: Implemented query_gkb_for_claims using vector_store_service.query_global_knowledge_base.
# 3. STATUS: Backend service is now fully integrated with ChromaDB/GKB.

import structlog
from datetime import datetime
from typing import cast, List, Dict, Any
from fastapi import HTTPException
from pymongo.database import Database
from pydantic import BaseModel # PHOENIX FIX: Added BaseModel Import

from app.core.db import db_instance
from app.models.evidence_map import EvidenceMapInDB, EvidenceMapUpdate
from app.models.user import UserInDB
from app.models.common import PyObjectId
# PHOENIX ADDITION: RAG Dependencies
from app.services.llm_service import get_embedding, query_global_rag_for_claims
from app.services import vector_store_service # Vector Store service for ChromaDB query

logger = structlog.get_logger(__name__)

# PHOENIX FIX: Define the expected output structure using BaseModel
class ClaimSuggestion(BaseModel):
    label: str
    content: str
    type: str = "claimNode"

class EvidenceMapService:
    @property
    def db(self) -> Database:
        """
        Runtime check to ensure DB is connected before access.
        """
        if db_instance is None:
            raise RuntimeError("Database is not initialized. Check app lifespan.")
        # Ensure we return the database instance itself
        return db_instance

    def get_map_by_case(self, case_id: str, user: UserInDB) -> EvidenceMapInDB:
        """
        Retrieves the map for a case. If none exists, returns an empty skeleton.
        """
        # Type-safe ID conversion
        try:
            c_oid = PyObjectId(case_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid Case ID format")

        # 1. Verify Case Access
        if not user.org_id:
             raise HTTPException(status_code=403, detail="User not part of an organization")

        case = self.db.cases.find_one({"_id": c_oid, "org_id": user.org_id})
        
        if not case:
            raise HTTPException(status_code=404, detail="Case not found or access denied")

        # 2. Fetch Map
        doc = self.db.evidence_maps.find_one({"case_id": c_oid})
        
        if not doc:
            # Return a virtual empty map (don't create DB entry until first save)
            return EvidenceMapInDB(
                case_id=c_oid,
                org_id=user.org_id,
                created_by=user.id,
                nodes=[],
                edges=[],
                viewport={"x": 0, "y": 0, "zoom": 1}
            )
            
        return EvidenceMapInDB(**doc)

    def save_map(self, case_id: str, data: EvidenceMapUpdate, user: UserInDB) -> EvidenceMapInDB:
        """
        Full overwrite of the map state (Nodes/Edges). 
        """
        try:
            c_oid = PyObjectId(case_id)
        except Exception:
             raise HTTPException(status_code=400, detail="Invalid Case ID format")

        if not user.org_id:
             raise HTTPException(status_code=403, detail="User must belong to an organization to save maps")
        
        # 1. Verify Case Access
        case = self.db.cases.find_one({"_id": c_oid, "org_id": user.org_id})
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")

        # 2. Prepare Payload
        update_data = {
            "nodes": [node.model_dump() for node in data.nodes],
            "edges": [edge.model_dump() for edge in data.edges],
            "updated_at": datetime.utcnow()
        }
        
        if data.viewport:
            update_data["viewport"] = data.viewport

        # 3. UPSERT
        result = self.db.evidence_maps.find_one_and_update(
            {"case_id": c_oid},
            {
                "$set": update_data,
                "$setOnInsert": {
                    "created_at": datetime.utcnow(),
                    "created_by": user.id,
                    "org_id": user.org_id, # Link to tenant
                    "case_id": c_oid
                }
            },
            upsert=True,
            return_document=True
        )
        
        if not result:
            raise HTTPException(status_code=500, detail="Failed to save map")

        return EvidenceMapInDB(**result)

    def query_gkb_for_claims(self, user_query: str) -> List[ClaimSuggestion]:
        """
        Executes a RAG query against the Global Knowledge Base (ChromaDB) to suggest Claim Cards.
        """
        try:
            # PHOENIX FIX: We are using the correct vector store query for the GKB
            
            # 1. Search Global Vector Store 
            # query_global_knowledge_base returns List[Dict[str, Any]] where each dict has a 'text' key (the context)
            rag_results = vector_store_service.query_global_knowledge_base(
                query_text=user_query, 
                n_results=5,
                jurisdiction='ks' # Assuming default jurisdiction
            )
            
            if not rag_results:
                # Return an empty list or a list with a suggestion about the lack of context
                return [] 
            
            # Aggregate context texts into a single string for the LLM
            rag_context_str = "\n---\n".join([r.get('text', '') for r in rag_results])

            # 2. Call LLM to structure Claims from Context
            llm_result_dict = query_global_rag_for_claims(rag_context_str, user_query)

            # 3. Parse and return structured suggestions
            claims_data = llm_result_dict.get('suggested_claims', [])
            
            suggestions = [ClaimSuggestion(**claim) for claim in claims_data]
            return suggestions
            
        except HTTPException:
             raise
        except Exception as e:
            logger.error(f"Global RAG query failed: {e}")
            # Raise a specific HTTP exception to inform the frontend
            raise HTTPException(
                status_code=500, 
                detail=f"Kërkesa RAG dështoi: Verifikoni lidhjen e bazës së njohurive. Detajet: {e}"
            )

evidence_map_service = EvidenceMapService()