# FILE: backend/app/api/endpoints/cases/case_analysis_router.py
# PHOENIX PROTOCOL - CASE ANALYSIS ROUTER V1.9
# V1.9: MULTI-DEVICE — shtuar GET /rewrite për të lexuar rishkrimin e ruajtur.
#       - I njëjti dokument i aksesueshëm nga çdo pajisje.
#       - Filtro sipas doc_type.
# V1.8: REWRITE DRAFT — POST (chunked parallel).
# V1.6: VERIFY DRAFT — GET + DELETE.

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
from ....services.document_review.draft_verifier import get_draft_verifier
from ....services.document_review.verify_prompts import VERIFY_DOC_TYPES
from ....services.document_review.rewrite_service import get_document_rewriter
from ....services.document_review.rewrite_prompts import get_rewrite_doc_types

logger = logging.getLogger(__name__)

router = APIRouter()

SYNTHESIS_ALLOWED_ROLES = {"ADMIN"}


# ═══════════════════════════════════════════════════════════════════════════
# REQUEST/RESPONSE MODELS
# ═══════════════════════════════════════════════════════════════════════════

class AnalyzeRequest(BaseModel):
    force_reprocess: bool = Field(False, description="Ri-ekstrakto edhe nëse ekziston cache")
    document_ids: Optional[List[str]] = Field(
        None,
        description="Nëse jepet, analiza skopohet vetëm në këto dokumente. "
                    "Nëse null, analizohet i gjithë fashikulli (kërkon ADMIN).",
    )


class VerifyDraftRequest(BaseModel):
    doc_type: str = Field(
        ...,
        description=(
            "Lloji i draftit: padi_civile | pergjigje_padi | kallzim_penal | "
            "kontrate | kerkese_propozim | ankese_kundershtim | tjeter"
        ),
    )


class RewriteDraftRequest(BaseModel):
    doc_type: str = Field(
        ...,
        description="Lloji i dokumentit për rishkrim.",
    )


class VerifyDraftResponse(BaseModel):
    has_verification: bool
    verification: Optional[dict] = None


class RewriteDraftResponse(BaseModel):
    has_rewrite: bool
    rewrite: Optional[dict] = None


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
    try:
        c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
    except InvalidId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid case_id format.",
        )

    case_exists = db.cases.find_one({"_id": c_oid}, {"_id": 1})
    if not case_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found.",
        )

    case_doc = case_service.get_case_for_user(db, c_oid, current_user)
    if not case_doc:
        logger.warning(
            f"🚫 [ACCESS DENIED] user={getattr(current_user, 'id', '?')} "
            f"case={case_id} role={getattr(current_user, 'role', '?')}"
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
    if document_ids and len(document_ids) > 0:
        return
    role = str(getattr(current_user, "role", "")).upper()
    if role not in SYNTHESIS_ALLOWED_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Analiza e plotë e lëndës (Synthesis) është e disponueshme "
                "vetëm për administratorë."
            ),
        )


# ═══════════════════════════════════════════════════════════════════════════
# ANALYZE — SSE
# ═══════════════════════════════════════════════════════════════════════════

@router.post(
    "/{case_id}/analyze",
    summary="Analiza e plotë e lëndës (SSE stream)",
    response_class=StreamingResponse,
)
async def analyze_case(
    case_id: str,
    body: Optional[AnalyzeRequest] = None,
    db: Database = Depends(get_db),
    current_user: UserInDB = Depends(get_current_active_user),
):
    _check_case_access(db, case_id, current_user)
    user_id_str = str(getattr(current_user, "id", ""))
    user_role = str(getattr(current_user, "role", "")).upper()

    force_reprocess = body.force_reprocess if body else False
    document_ids = body.document_ids if body else None

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
            logger.exception(f"❌ [SSE] Error during analysis for case {case_id}: {e}")
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


# ═══════════════════════════════════════════════════════════════════════════
# VERIFY DRAFT — POST (SSE)
# ═══════════════════════════════════════════════════════════════════════════

@router.post(
    "/{case_id}/documents/{doc_id}/verify",
    summary="Verifiko Draftin (SSE stream)",
    response_class=StreamingResponse,
)
async def verify_draft(
    case_id: str,
    doc_id: str,
    body: VerifyDraftRequest,
    db: Database = Depends(get_db),
    current_user: UserInDB = Depends(get_current_active_user),
):
    _check_case_access(db, case_id, current_user)
    user_id_str = str(getattr(current_user, "id", ""))
    user_role = str(getattr(current_user, "role", "")).upper()

    if body.doc_type not in VERIFY_DOC_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Lloj dokumenti i panjohur: '{body.doc_type}'. "
                f"Të lejuara: {sorted(VERIFY_DOC_TYPES.keys())}"
            ),
        )

    logger.info(
        f"🚀 [SSE VERIFY] start: case={case_id}, doc={doc_id}, "
        f"doc_type={body.doc_type}, user={user_id_str}, role={user_role}"
    )

    async def event_stream() -> AsyncGenerator[str, None]:
        loop = asyncio.get_event_loop()
        queue: "asyncio.Queue[dict]" = asyncio.Queue()

        def progress_callback(event: str, payload: dict) -> None:
            try:
                asyncio.run_coroutine_threadsafe(
                    queue.put({"event": event, **(payload or {})}),
                    loop,
                )
            except Exception as e:
                logger.warning(f"⚠️ [SSE VERIFY] progress push failed: {e}")

        async def _run_verifier() -> None:
            try:
                verifier = get_draft_verifier(db)
                result = await asyncio.to_thread(
                    verifier.verify,
                    case_id,
                    doc_id,
                    body.doc_type,
                    user_id_str,
                    progress_callback,
                    None,
                )
                await queue.put({"event": "completed", "result": result})
            except Exception as e:
                logger.exception(f"❌ [SSE VERIFY] verifier failed: {e}")
                await queue.put({
                    "event": "error",
                    "message": f"Verification failed: {type(e).__name__}",
                })

        task = asyncio.create_task(_run_verifier())

        try:
            while True:
                item = await queue.get()
                yield _sse_format(item)
                ev = item.get("event")
                if ev in ("completed", "error"):
                    break

            yield "data: [DONE]\n\n"
            logger.info(f"✅ [SSE VERIFY] complete: case={case_id}, doc={doc_id}")

        except asyncio.CancelledError:
            logger.info(f"⏹️ [SSE VERIFY] Client disconnected: case={case_id}")
            task.cancel()
            raise
        except Exception as e:
            logger.exception(f"❌ [SSE VERIFY] stream error: {e}")
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


# ═══════════════════════════════════════════════════════════════════════════
# VERIFY DRAFT — GET
# ═══════════════════════════════════════════════════════════════════════════

@router.get(
    "/{case_id}/documents/{doc_id}/verify",
    summary="Lexo raportin e verifikimit të draftit",
    response_model=VerifyDraftResponse,
)
async def get_verify_draft(
    case_id: str,
    doc_id: str,
    doc_type: Optional[str] = None,
    db: Database = Depends(get_db),
    current_user: UserInDB = Depends(get_current_active_user),
):
    _check_case_access(db, case_id, current_user)

    try:
        c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
    except InvalidId:
        c_oid = case_id

    case = db.cases.find_one(
        {"_id": c_oid},
        {"case_document_verifications": 1},
    )
    if not case:
        return VerifyDraftResponse(has_verification=False)

    verifs = case.get("case_document_verifications") or {}
    entry = verifs.get(doc_id)

    if not entry:
        return VerifyDraftResponse(has_verification=False)

    if doc_type and entry.get("doc_type") != doc_type:
        return VerifyDraftResponse(has_verification=False)

    verification = {
        "doc_type": entry.get("doc_type"),
        "doc_type_label": entry.get("doc_type_label"),
        "file_name": entry.get("file_name"),
        "built_at": entry.get("built_at"),
        "readiness": entry.get("readiness"),
        "score": entry.get("score"),
        "score_breakdown": entry.get("score_breakdown"),
        "full_report": entry.get("full_report"),
        "stats": entry.get("stats") or {},
        "status": entry.get("status"),
    }

    return VerifyDraftResponse(has_verification=True, verification=verification)


# ═══════════════════════════════════════════════════════════════════════════
# VERIFY DRAFT — DELETE
# ═══════════════════════════════════════════════════════════════════════════

@router.delete(
    "/{case_id}/documents/{doc_id}/verify",
    summary="Fshi raportin e verifikimit të draftit",
)
async def clear_verify_draft(
    case_id: str,
    doc_id: str,
    db: Database = Depends(get_db),
    current_user: UserInDB = Depends(get_current_active_user),
):
    _check_case_access(db, case_id, current_user)

    try:
        c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
    except InvalidId:
        c_oid = case_id

    try:
        result = db.cases.update_one(
            {"_id": c_oid},
            {"$unset": {f"case_document_verifications.{doc_id}": ""}},
        )
        logger.info(
            f"🗑️ [VERIFY DELETE] case={case_id}, doc={doc_id}, "
            f"modified={result.modified_count}"
        )
        return {"deleted": True, "modified_count": result.modified_count}
    except Exception as e:
        logger.error(f"❌ [VERIFY DELETE] Failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear verification: {e}",
        )


# ═══════════════════════════════════════════════════════════════════════════
# V1.9: REWRITE — GET (multi-device)
# ═══════════════════════════════════════════════════════════════════════════

@router.get(
    "/{case_id}/documents/{doc_id}/rewrite",
    summary="Lexo rishkrimin e ruajtur (multi-device)",
    description=(
        "Lexon rishkrimin e ruajtur nga cases.document_rewrites.{doc_id}. "
        "I njëjti dokument i aksesueshëm nga çdo pajisje. "
        "Nëse nuk ekziston, kthen has_rewrite=false."
    ),
    response_model=RewriteDraftResponse,
)
async def get_rewrite_draft(
    case_id: str,
    doc_id: str,
    doc_type: Optional[str] = None,
    db: Database = Depends(get_db),
    current_user: UserInDB = Depends(get_current_active_user),
):
    _check_case_access(db, case_id, current_user)
    user_id_str = str(getattr(current_user, "id", ""))

    rewriter = get_document_rewriter(db)
    result = rewriter.get_saved_rewrite(
        case_id=case_id,
        document_id=doc_id,
        doc_type=doc_type,
    )

    if result.get("has_rewrite"):
        logger.info(
            f"📖 [REWRITE GET] Served: case={case_id}, doc={doc_id}, "
            f"user={user_id_str}"
        )

    return RewriteDraftResponse(
        has_rewrite=result.get("has_rewrite", False),
        rewrite=result.get("rewrite"),
    )


# ═══════════════════════════════════════════════════════════════════════════
# V1.8: REWRITE — POST (SSE) me CHUNKED PARALLEL
# ═══════════════════════════════════════════════════════════════════════════

@router.post(
    "/{case_id}/documents/{doc_id}/rewrite",
    summary="Rishkruaj Draftin me rekomandimet (SSE stream)",
    response_class=StreamingResponse,
)
async def rewrite_draft(
    case_id: str,
    doc_id: str,
    body: RewriteDraftRequest,
    db: Database = Depends(get_db),
    current_user: UserInDB = Depends(get_current_active_user),
):
    _check_case_access(db, case_id, current_user)
    user_id_str = str(getattr(current_user, "id", ""))
    user_role = str(getattr(current_user, "role", "")).upper()

    allowed = get_rewrite_doc_types()
    if body.doc_type not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Lloj dokumenti i panjohur: '{body.doc_type}'. "
                f"Të lejuara: {sorted(allowed.keys())}"
            ),
        )

    logger.info(
        f"✍️ [SSE REWRITE] start: case={case_id}, doc={doc_id}, "
        f"doc_type={body.doc_type}, user={user_id_str}, role={user_role}"
    )

    async def event_stream() -> AsyncGenerator[str, None]:
        loop = asyncio.get_event_loop()
        queue: "asyncio.Queue[dict]" = asyncio.Queue()

        def progress_callback(event: str, payload: dict) -> None:
            try:
                asyncio.run_coroutine_threadsafe(
                    queue.put({"event": event, **(payload or {})}),
                    loop,
                )
            except Exception as e:
                logger.warning(f"⚠️ [SSE REWRITE] progress push failed: {e}")

        async def _run_rewriter() -> None:
            try:
                rewriter = get_document_rewriter(db)
                result = await asyncio.to_thread(
                    rewriter.rewrite,
                    case_id,
                    doc_id,
                    body.doc_type,
                    None,
                    user_id_str,
                    progress_callback,
                )

                if result.get("status") == "error":
                    await queue.put({
                        "event": "error",
                        "message": result.get("error_message", "Rishkrimi dështoi."),
                    })
                    return

                await queue.put({"event": "completed", "result": result})

            except Exception as e:
                logger.exception(f"❌ [SSE REWRITE] rewriter failed: {e}")
                await queue.put({
                    "event": "error",
                    "message": f"Rishkrimi dështoi: {type(e).__name__}",
                })

        task = asyncio.create_task(_run_rewriter())

        try:
            while True:
                item = await queue.get()
                yield _sse_format(item)
                ev = item.get("event")
                if ev in ("completed", "error"):
                    break

            yield "data: [DONE]\n\n"
            logger.info(f"✅ [SSE REWRITE] complete: case={case_id}, doc={doc_id}")

        except asyncio.CancelledError:
            logger.info(f"⏹️ [SSE REWRITE] Client disconnected: case={case_id}")
            task.cancel()
            raise
        except Exception as e:
            logger.exception(f"❌ [SSE REWRITE] stream error: {e}")
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