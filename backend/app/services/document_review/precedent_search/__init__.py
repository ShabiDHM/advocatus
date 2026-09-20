# FILE: backend/app/services/document_review/precedent_search/__init__.py
# PHOENIX PROTOCOL - PRECEDENT SEARCH PACKAGE V2.1
# Public API re-exports per backward compatibility.
#
# Perdorimi:
#   from app.services.document_review.precedent_search import (
#       search_relevant_precedents,
#       build_precedent_query,
#       PRECEDENT_SIMILARITY_THRESHOLD,
#       PRECEDENT_TOP_K,
#   )

from .config import (
    PRECEDENT_SIMILARITY_THRESHOLD,
    PRECEDENT_TOP_K,
    PRECEDENT_USE_HYBRID,
    PRECEDENT_RERANKER,
    PRECEDENT_RERANK_MIN_SCORE,
)
from .query_builder import build_precedent_query
from .service import search_relevant_precedents

__all__ = [
    "search_relevant_precedents",
    "build_precedent_query",
    "PRECEDENT_SIMILARITY_THRESHOLD",
    "PRECEDENT_TOP_K",
    "PRECEDENT_USE_HYBRID",
    "PRECEDENT_RERANKER",
    "PRECEDENT_RERANK_MIN_SCORE",
]