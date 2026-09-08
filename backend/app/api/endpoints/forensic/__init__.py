# FILE: backend/app/api/endpoints/forensic/__init__.py
"""
Pika e Hyrjes për Router-at e Zyrës Forenzike (Juristi AI Forensic Suite)
"""
from .dossier_router import router as forensic_dossier_router
from .lab_router import router as forensic_lab_router
from .chat_router import router as forensic_chat_router
from .investigator_router import router as forensic_investigator_router

__all__ = [
    "forensic_dossier_router",
    "forensic_lab_router",
    "forensic_chat_router",
    "forensic_investigator_router"
]