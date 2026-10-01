# FILE: backend/app/services/pillars/__init__.py
# PHOENIX PROTOCOL - PILLARS REGISTRY V5.1
# V5.1: CROSS_REFERENCE EXPORT —
#       - Shtuar `CrossReferenceService` + `get_cross_reference_service` në
#         __init__. Service-i ekzistonte prej V1.1, por nuk ishte i eksportuar
#         → importuesit `from app.services.pillars import CrossReferenceService`
#         merrnin ImportError.
# V5.0: Removed ForensicAuditService (replaced by DocumentReviewService).

from .base_pillar_service import BasePillarService
from .role_guard_service import RoleGuardService
from .legal_drafting_service import LegalDraftingService
from .statutory_verification_service import StatutoryVerificationService
from .hallucination_filter import HallucinationFilter, hallucination_filter
from .cross_reference_service import (
    CrossReferenceService,
    get_cross_reference_service,
)

__all__ = [
    "BasePillarService",
    "RoleGuardService",
    "LegalDraftingService",
    "StatutoryVerificationService",
    "HallucinationFilter",
    "hallucination_filter",
    "CrossReferenceService",
    "get_cross_reference_service",
]