# FILE: backend/app/api/endpoints/laws_pkg/__init__.py
# PHOENIX PROTOCOL - LAWS PACKAGE V2.0
#
# V2.0: Shtuar `laws_audit_router` (mungonte).
#       Shtuar `repealed_registry` (V208.2).
#       `__all__` i plotë për konsistencë me `laws.py`.

from app.api.endpoints.laws_pkg.laws_pdf_router import router as laws_pdf_router
from app.api.endpoints.laws_pkg.laws_audit_router import router as laws_audit_router
from app.api.endpoints.laws_pkg.laws_query_router import router as laws_query_router

from app.api.endpoints.laws_pkg import repealed_registry

__all__ = [
    "laws_pdf_router",
    "laws_audit_router",
    "laws_query_router",
    "repealed_registry",
]