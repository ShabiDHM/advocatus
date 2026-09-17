# FILE: backend/app/api/endpoints/cases/case_analysis_router.py
# PHOENIX PROTOCOL - CASE ANALYSIS ROUTER V1.1
# FIX: accept document_ids in body.

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
from ....services.case_analysis_orchestrator import (
    get_case_analysis_orchestrator,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class AnalyzeRequest(BaseModel):
    force_reprocess: bool = Field(False, description="Ri-ekstrakto edhe nëse ekziston cache")
    document_ids: Optional[List[str]] = Field(
        None,
        description="Nëse jepet, analiza skopohet vetëm në këto dokumente. "
                    "Nëse null, analizohet i gjithë fashikulli.",
    )


def _sse_format(event: dict) -> str:
    try:
        payload = json.dumps(event, default=str, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"⚠️ [SSE] JSON serialize failed: {e}")
        payload = json.dumps({"event": "error", "message": "Serialization failed"})
    return f"data: {payload}\n\n"


def _check_case_ownership(
    db: Database,
    case_id: str,
    current_user: UserInDB,
) -> dict:
    try:
        c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
    except InvalidId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid case_id format.",
        )

    case_doc = db.cases.find_one({"_id": c_oid})
    if not case_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found.",
        )

    user_id_str = str(getattr(current_user, "id", ""))
    role = str(getattr(current_user, "role", "")).upper()

    if role in ("ADMIN", "SUPERADMIN"):
        return case_doc

    case_owner = str(
        case_doc.get("owner_id")
        or case_doc.get("user_id")
        or case_doc.get("created_by")
        or ""
    )

    if not case_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Case ownership cannot be verified.",
        )

    if case_owner != user_id_str:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this case.",
        )

    return case_doc


@router.post(
    "/{case_id}/analyze",
    summary="Analiza e plotë e lëndës (SSE stream)",
    description=(
        "Kthen SSE me progres live. Body: force_reprocess + document_ids. "
        "Nëse document_ids jepet, analiza skopohet në ato dokumente."
    ),
    response_class=StreamingResponse,
)
async def analyze_case(
    case_id: str,
    body: Optional[AnalyzeRequest] = None,
    db: Database = Depends(get_db),
    current_user: UserInDB = Depends(get_current_active_user),
):
    case_doc = _check_case_ownership(db, case_id, current_user)
    user_id_str = str(getattr(current_user, "id", ""))

    force_reprocess = body.force_reprocess if body else False
    document_ids = body.document_ids if body else None

    logger.info(
        f"🚀 [SSE] analyze_case start: case={case_id}, "
        f"user={user_id_str}, force={force_reprocess}, "
        f"docs={document_ids or 'ALL'}"
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