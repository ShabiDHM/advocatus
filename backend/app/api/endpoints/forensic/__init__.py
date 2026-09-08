# FILE: backend/app/api/endpoints/forensic/__init__.py
# PHOENIX PROTOCOL - 1:1 FORENSIC DEDICATED ROUTERS SUITE V2.0

from .dossier_router import router as forensic_dossier_router
from .audio_router import router as forensic_audio_router
from .visual_router import router as forensic_visual_router
from .finance_router import router as forensic_finance_router
from .document_router import router as forensic_document_router
from .war_room_router import router as forensic_war_room_router
from .chat_router import router as forensic_chat_router
from .investigator_router import router as forensic_investigator_router

__all__ = [
    "forensic_dossier_router",
    "forensic_audio_router",
    "forensic_visual_router",
    "forensic_finance_router",
    "forensic_document_router",
    "forensic_war_room_router",
    "forensic_chat_router",
    "forensic_investigator_router"
]