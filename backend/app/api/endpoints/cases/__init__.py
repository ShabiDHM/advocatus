# FILE: app/api/endpoints/cases/__init__.py
from app.api.endpoints.cases.case_management_router import router as case_management_router
from app.api.endpoints.cases.document_router import router as document_router
from app.api.endpoints.cases.graph_router import router as graph_router
from app.api.endpoints.cases.analysis_router import router as analysis_router

from fastapi import APIRouter

router = APIRouter()

router.include_router(case_management_router)
router.include_router(document_router)
router.include_router(graph_router)
router.include_router(analysis_router)