# FILE: backend/app/services/document_review_service.py
# PHOENIX PROTOCOL - DOCUMENT REVIEW SERVICE (SHIM) V5.0
# V5.0: Rebuild i plotë — logjika është modularizuar në app/services/document_review/.
#       Ky file është thin shim — re-export për backward compatibility.
#       Arkitekturë: Regex + MongoDB + LLM (narrative).

from .document_review.service import (
    DocumentReviewService,
    get_document_review_service,
)
from .document_review.prompts import DOCUMENT_REVIEW_PROMPTS
from .document_review.citation_extractor import build_citation_profile
from .document_review.fact_extractor import build_fact_profile
from .document_review.mongo_verifier import verify_all
from .document_review.report_builder import build_full_report

__all__ = [
    "DocumentReviewService",
    "get_document_review_service",
    "DOCUMENT_REVIEW_PROMPTS",
    "build_citation_profile",
    "build_fact_profile",
    "verify_all",
    "build_full_report",
]