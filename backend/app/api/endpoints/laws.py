# FILE: backend/app/api/endpoints/laws.py
# PHOENIX PROTOCOL - LAWS ROUTER (UNIFIES MODULAR LAWS PACKAGE)

from fastapi import APIRouter
from app.api.endpoints.laws_pkg.laws_pdf_router import router as laws_pdf_router
from app.api.endpoints.laws_pkg.laws_audit_router import router as laws_audit_router
from app.api.endpoints.laws_pkg.laws_query_router import router as laws_query_router

router = APIRouter(tags=["Laws"])

# Rregulli: audit_router dhe pdf_router regjistrohen para query_router (për të shmangur kapjen nga /{chunk_id})
router.include_router(laws_pdf_router)
router.include_router(laws_audit_router)
router.include_router(laws_query_router)