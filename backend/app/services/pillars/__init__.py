# FILE: backend/app/services/pillars/__init__.py
# PHOENIX PROTOCOL - PILLARS REGISTRY V3.0 (CLEAN REGISTRY • ZERO PHANTOM IMPORTS)

from .base_pillar_service import BasePillarService
from .role_guard_service import RoleGuardService
from .comprehensive_analysis_service import ComprehensiveAnalysisService
from .forensic_audit_service import ForensicAuditService
from .legal_drafting_service import LegalDraftingService
from .statutory_verification_service import StatutoryVerificationService
from .hallucination_filter import HallucinationFilter, hallucination_filter

__all__ = [
    "BasePillarService",
    "RoleGuardService",
    "ComprehensiveAnalysisService",
    "ForensicAuditService",
    "LegalDraftingService",
    "StatutoryVerificationService",
    "HallucinationFilter",
    "hallucination_filter",
]