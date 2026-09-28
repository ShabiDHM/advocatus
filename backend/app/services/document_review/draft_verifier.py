# FILE: backend/app/services/document_review/draft_verifier.py
# PHOENIX PROTOCOL - DRAFT VERIFIER SHIM V3.0
# V3.0: SHIM — Logjika u zhvendos në verify/verifier.py (V2.1).
#       Ky file ruan API-n publike për backward-compatibility.

from .verify.verifier import DraftVerifier, get_draft_verifier

__all__ = ["DraftVerifier", "get_draft_verifier"]