# FILE: backend/app/services/law_library/__init__.py
# PHOENIX PROTOCOL - LAW LIBRARY V5.0 (VERIFY-ENHANCED)
# Arkitekturë: Python verifikon → LLM shpjegon.

from .article_fetcher import fetch_article_from_db, article_exists
from .post_processor import verify_explanation_output
from .prompts import build_sokrati_prompt, build_auditor_prompt
from .service import LawLibraryService, get_law_library_service

__all__ = [
    "fetch_article_from_db",
    "article_exists",
    "verify_explanation_output",
    "build_sokrati_prompt",
    "build_auditor_prompt",
    "LawLibraryService",
    "get_law_library_service",
]