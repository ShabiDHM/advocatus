# FILE: backend/app/services/document_review/__init__.py
# PHOENIX PROTOCOL - DOCUMENT REVIEW PACKAGE V5.0 (REBUILD COMPLETE)
# Arkitekturë: Regex (Laborator) + MongoDB (Arkiva) + LLM (Narrative).

from . import constants
from . import patterns
from . import helpers
from . import citation_extractor
from . import fact_extractor
from . import mongo_verifier
from . import prompts
from . import streaming
from . import report_builder
from . import persistence
from . import service

from .citation_extractor import build_citation_profile
from .fact_extractor import build_fact_profile
from .mongo_verifier import verify_all
from .prompts import DOCUMENT_REVIEW_PROMPTS, build_verified_context
from .streaming import synthesize_section_streaming
from .report_builder import build_full_report
from .service import DocumentReviewService, get_document_review_service

__all__ = [
    "constants",
    "patterns",
    "helpers",
    "citation_extractor",
    "fact_extractor",
    "mongo_verifier",
    "prompts",
    "streaming",
    "report_builder",
    "persistence",
    "service",
    "build_citation_profile",
    "build_fact_profile",
    "verify_all",
    "DOCUMENT_REVIEW_PROMPTS",
    "build_verified_context",
    "synthesize_section_streaming",
    "build_full_report",
    "DocumentReviewService",
    "get_document_review_service",
]