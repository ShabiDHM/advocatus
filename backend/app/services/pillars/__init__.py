# FILE: backend/app/services/pillars/__init__.py
# PHOENIX PROTOCOL - PILLARS REGISTRY V4.0 (COMPREHENSIVE SERVICE FULLY WIPED OUT)
# 100% COMPLETE CODE • ZERO PHANTOM IMPORTS • CLEAN ARCHITECTURE

from .base_pillar_service import BasePillarService
from .role_guard_service import RoleGuardService
from .forensic_audit_service import ForensicAuditService
from .legal_drafting_service import LegalDraftingService
from .statutory_verification_service import StatutoryVerificationService
from .hallucination_filter import HallucinationFilter, hallucination_filter

__all__ = [
    "BasePillarService",
    "RoleGuardService",
    "ForensicAuditService",
    "LegalDraftingService",
    "StatutoryVerificationService",
    "HallucinationFilter",
    "hallucination_filter",
]