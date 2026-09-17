# FILE: backend/app/services/pillars/__init__.py
# PHOENIX PROTOCOL - PILLARS REGISTRY V5.0
# V5.0: Removed ForensicAuditService (replaced by DocumentReviewService).

from .base_pillar_service import BasePillarService
from .role_guard_service import RoleGuardService
from .legal_drafting_service import LegalDraftingService
from .statutory_verification_service import StatutoryVerificationService
from .hallucination_filter import HallucinationFilter, hallucination_filter

__all__ = [
    "BasePillarService",
    "RoleGuardService",
    "LegalDraftingService",
    "StatutoryVerificationService",
    "HallucinationFilter",
    "hallucination_filter",
]