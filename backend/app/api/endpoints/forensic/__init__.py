# FILE: backend/app/api/endpoints/forensic/__init__.py
# PHOENIX PROTOCOL - 1:1 FORENSIC DEDICATED ROUTERS SUITE V2.1 (REMOVED INVESTIGATOR)

from .dossier_router import router as forensic_dossier_router
from .audio_router import router as forensic_audio_router
from .visual_router import router as forensic_visual_router
from .document_router import router as forensic_document_router
from .chat_router import router as forensic_chat_router

__all__ = [
    "forensic_dossier_router",
    "forensic_audio_router",
    "forensic_visual_router",
    "forensic_document_router",
    "forensic_chat_router"
]