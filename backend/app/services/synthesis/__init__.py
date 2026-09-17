# FILE: backend/app/services/synthesis/__init__.py
# PHOENIX PROTOCOL - SYNTHESIS PACKAGE V4.0
# Public API për paketën synthesis.

from .service import SynthesisService, get_synthesis_service

__all__ = ["SynthesisService", "get_synthesis_service"]