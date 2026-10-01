# FILE: backend/app/services/chat_service.py
# PHOENIX PROTOCOL - CHAT SERVICE V32.2 (ORG-AWARE ACCESS + LOGGING CONSISTENCY)
# V32.2: LOGGING + ERROR HARDENING —
#        - `structlog` → `logging.getLogger(__name__)` (konsistencë me
#          pjesën tjetër të projektit; structlog nuk ishte konfiguruar
#          globalisht → log format i ndryshëm në prod).
#        - Hequr `import logging` i papërdorur (më parë importohej vetëm
#          për dead reference; tani logging është aktiv).
#        - Error message nuk leak-on më `str(e)` tek user (potencialisht
#          sensitive). Logohet server-side, dërgohet mesazh i përgjithshëm.
# V32.1: ACCESS CHECK FIX — _build_case_access_query.
# V32.0: Hequr kanali forensic.

from __future__ import annotations
import logging
from types import SimpleNamespace
from typing import AsyncGenerator, Optional, List
from bson import ObjectId
from datetime import datetime, timezone
from pymongo.database import Database
from app.models.case import ChatMessage
from app.services.case_service import _build_case_access_query

logger = logging.getLogger(__name__)


async def stream_chat_response(
    db: Database,
    case_id: str,
    user_query: str,
    user_id: str,
    document_ids: Optional[List[str]] = None,
    jurisdiction: Optional[str] = 'ks',
    domain: Optional[str] = 'automatic',
    save_history: bool = True,
) -> AsyncGenerator[str, None]:
    """
    Shërbimi Qendror i Bisedës për klientin.
    Historiku ruhet dhe lexohet nga `case.chat_history`.

    V32.1: Aksesi kontrollohet nga `_build_case_access_query` (org-aware,
    SELECTIVE-aware) — njësoj si pjesa tjetër e case endpoints.
    """
    try:
        from app.services.albanian_rag_service import AlbanianRAGService

        oid = ObjectId(case_id)
        user_oid = ObjectId(user_id)

        # V32.1: Ngarko user-in për org-aware access
        user_doc = db.users.find_one({"_id": user_oid})
        if not user_doc:
            yield "Gabim: Përdoruesi nuk u gjet."
            return

        # V32.1: Duck-typed user context — mjafton për _build_case_access_query
        user_ctx = SimpleNamespace(
            id=user_oid,
            organization_id=user_doc.get("organization_id"),
            org_access_level=user_doc.get("org_access_level", "FULL") or "FULL",
            assigned_case_ids=user_doc.get("assigned_case_ids", []) or [],
        )

        # V32.1: Query org-aware (owner + org + assigned) + _id constraint
        access_query = _build_case_access_query(user_ctx, case_id=oid)
        case = db.cases.find_one(access_query)

        if not case:
            yield "Gabim: Qasja u refuzua ose lënda nuk u gjet."
            return

        # 1. Ruajtja e pyetjes së përdoruesit
        if save_history:
            db.cases.update_one(
                {"_id": oid},
                {"$push": {"chat_history": ChatMessage(
                    role="user",
                    content=user_query,
                    timestamp=datetime.now(timezone.utc)
                ).model_dump()}}
            )
        raw_history = case.get("chat_history", [])
        recent_history = raw_history[-10:] if save_history else []

        full_response = ""
        yield " "  # Keep-alive fillestar

        agent_service = AlbanianRAGService(db=db)
        async for token in agent_service.chat(
            query=user_query,
            user_id=user_id,
            case_id=case_id,
            document_ids=document_ids,
            jurisdiction=jurisdiction or 'ks',
            history=recent_history,
            domain=domain
        ):
            full_response += token
            yield token

        # 2. Ruajtja e përgjigjes së AI
        if full_response.strip() and save_history:
            clean_ai_text = full_response.strip()
            db.cases.update_one(
                {"_id": oid},
                {"$push": {"chat_history": ChatMessage(
                    role="ai",
                    content=clean_ai_text,
                    timestamp=datetime.now(timezone.utc)
                ).model_dump()}}
            )

    except Exception as e:
        # V32.2: Log i plotë server-side, mesazh i përgjithshëm për user
        logger.exception("[ChatService V32.2] Stream error: %s", e)
        yield "\n\n[Gabim Teknik në Transmetim. Ju lutem rifreskoni faqen dhe provoni përsëri.]"