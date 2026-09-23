# FILE: backend/app/api/endpoints/cases/case_analysis_router.py
# PHOENIX PROTOCOL - CASE ANALYSIS ROUTER V1.4
# V1.4: Integrimi me case_service.get_case_for_user():
#       - Hequr logjika e duplikuar _check_case_ownership
#       - Perdor helper-in central qe njeh organizaten, assigned_user_ids
#       - Member i organizates me FULL access kalon per te gjitha case-t
# V1.3: Hequr SUPERADMIN. Vetem ADMIN per synthesis.
# V1.2: SYNTHESIS GATING (document_ids=None/[]).
# V1.1: accept document_ids in body.

import asyncio
import json
import logging
from typing import AsyncGenerator, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from pymongo.database import Database
from bson import ObjectId
from bson.errors import InvalidId

from ..dependencies import get_db, get_current_active_user
from ....models.user import UserInDB
from ....services import case_service
from ....services.case_analysis_orchestrator import (
    get_case_analysis_orchestrator,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Vetem ADMIN ka akses ne synthesis.
SYNTHESIS_ALLOWED_ROLES = {"ADMIN"}


class AnalyzeRequest(BaseModel):
    force_reprocess: bool = Field(False, description="Ri-ekstrakto edhe nëse ekziston cache")
    document_ids: Optional[List[str]] = Field(
        None,
        description="Nëse jepet, analiza skopohet vetëm në këto dokumente. "
                    "Nëse null, analizohet i gjithë fashikulli (kërkon ADMIN).",
    )


def _sse_format(event: dict) -> str:
    try:
        payload = json.dumps(event, default=str, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"⚠️ [SSE] JSON serialize failed: {e}")
        payload = json.dumps({"event": "error", "message": "Serialization failed"})
    return f"data: {payload}\n\n"


def _check_case_access(
    db: Database,
    case_id: str,
    current_user: UserInDB,
) -> dict:
    """
    V1.4: Kontroll central i aksesit duke perdorur case_service.
    Pranon:
      - owner (owner_id / user_id)
      - anëtarë të organizatës (FULL access)
      - usera me SELECTIVE qe jane ne assigned_user_ids
    """
    try:
        c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
    except InvalidId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid case_id format.",
        )

    # Kontrollo ekzistencen e case (per te dalluar 404 nga 403)
    case_exists = db.cases.find_one({"_id": c_oid}, {"_id": 1})
    if not case_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found.",
        )

    # V1.4: Kontroll central i aksesit
    case_doc = case_service.get_case_for_user(db, c_oid, current_user)
    if not case_doc:
        logger.warning(
            f"🚫 [ACCESS DENIED] user={getattr(current_user, 'id', '?')} "
            f"case={case_id} role={getattr(current_user, 'role', '?')} "
            f"org={getattr(current_user, 'organization_id', '?')}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this case.",
        )

    return case_doc


def _check_synthesis_permission(
    current_user: UserInDB,
    document_ids: Optional[List[str]],
) -> None:
    """
    Verifikon nese user-i ka leje per synthesis (docs=ALL).
    Single-doc = document_ids=[...] → OK per te gjithe me akses ne case.
    Synthesis = document_ids=None/[] → vetem ADMIN.
    """
    if document_ids and len(document_ids) > 0:
        return

    role = str(getattr(current_user, "role", "")).upper()

    if role not in SYNTHESIS_ALLOWED_ROLES:
        logger.warning(
            f"🚫 [V1.4 GATE] Refused synthesis for user role='{role}' "
            f"(user_id={getattr(current_user, 'id', '?')})"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Analiza e plotë e lëndës (Synthesis) është e disponueshme "
                "vetëm për administratorë. Për analizë dokumenti individual, "
                "ju lutem zgjidhni një dokument specifik."
            ),
        )


@router.post(
    "/{case_id}/analyze",
    summary="Analiza e plotë e lëndës (SSE stream)",
    description=(
        "Kthen SSE me progres live. Body: force_reprocess + document_ids. "
        "Nëse document_ids jepet, analiza skopohet në ato dokumente (single-doc). "
        "Nëse document_ids null/[] → synthesis (kerkon ADMIN)."
    ),
    response_class=StreamingResponse,
)
async def analyze_case(
    case_id: str,
    body: Optional[AnalyzeRequest] = None,
    db: Database = Depends(get_db),
    current_user: UserInDB = Depends(get_current_active_user),
):
    # V1.4: Kontroll aksesi me organizat
    case_doc = _check_case_access(db, case_id, current_user)
    user_id_str = str(getattr(current_user, "id", ""))
    user_role = str(getattr(current_user, "role", "")).upper()

    force_reprocess = body.force_reprocess if body else False
    document_ids = body.document_ids if body else None

    # Synthesis gating
    _check_synthesis_permission(current_user, document_ids)

    logger.info(
        f"🚀 [SSE] analyze_case start: case={case_id}, "
        f"user={user_id_str}, role={user_role}, force={force_reprocess}, "
        f"docs={document_ids or 'ALL (synthesis)'}"
    )

    async def event_stream() -> AsyncGenerator[str, None]:
        try:
            orchestrator = get_case_analysis_orchestrator(db)

            async for event in orchestrator.run(
                case_id=str(case_id),
                user_id=user_id_str,
                force_reprocess=force_reprocess,
                document_ids=document_ids,
            ):
                yield _sse_format(event)

            yield "data: [DONE]\n\n"
            logger.info(f"✅ [SSE] analyze_case complete: case={case_id}")

        except asyncio.CancelledError:
            logger.info(f"⏹️ [SSE] Client disconnected: case={case_id}")
            raise

        except Exception as e:
            logger.exception(
                f"❌ [SSE] Error during analysis for case {case_id}: {e}"
            )
            try:
                yield _sse_format({
                    "event": "error",
                    "message": f"Server error: {type(e).__name__}",
                })
                yield "data: [DONE]\n\n"
            except Exception:
                pass

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )