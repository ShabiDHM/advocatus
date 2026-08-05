# FILE: backend/app/api/endpoints/laws_pkg/__init__.py
from app.api.endpoints.laws_pkg.laws_pdf_router import router as laws_pdf_router
from app.api.endpoints.laws_pkg.laws_query_router import router as laws_query_router

__all__ = ["laws_pdf_router", "laws_query_router"]