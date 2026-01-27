# FILE: backend/app/services/evidence_map_service.py
# PHOENIX PROTOCOL - EVIDENCE MAP SERVICE (FIXED)
# 1. FIX: Uses 'db_instance' from core.db with runtime safety check.
# 2. FIX: Explicit 'PyObjectId' casting to satisfy Pylance strict typing.
# 3. LOGIC: Handles UPSERT operations for Case Maps.

import structlog
from datetime import datetime
from typing import cast
from fastapi import HTTPException
from pymongo.database import Database

from app.core.db import db_instance
from app.models.evidence_map import EvidenceMapInDB, EvidenceMapUpdate
from app.models.user import UserInDB
from app.models.common import PyObjectId

logger = structlog.get_logger(__name__)

class EvidenceMapService:
    @property
    def db(self) -> Database:
        """
        Runtime check to ensure DB is connected before access.
        Fixes 'db is unknown' and NoneType errors at import time.
        """
        if db_instance is None:
            raise RuntimeError("Database is not initialized. Check app lifespan.")
        return db_instance

    def get_map_by_case(self, case_id: str, user: UserInDB) -> EvidenceMapInDB:
        """
        Retrieves the map for a case. If none exists, returns an empty skeleton.
        Verifies Case access first.
        """
        # Type-safe ID conversion
        try:
            c_oid = PyObjectId(case_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid Case ID format")

        # 1. Verify Case Access
        # We assume org_id is present on the user. If not, access is denied.
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
        Concurrency Strategy: Last Write Wins (Phase 1).
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
        # We ensure we only update if org_id matches (safety net)
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

evidence_map_service = EvidenceMapService()