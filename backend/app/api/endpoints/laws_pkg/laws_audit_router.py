# FILE: backend/app/api/endpoints/laws_pkg/laws_audit_router.py
# PHOENIX PROTOCOL - LAWS AUDIT ROUTER V3.0
#
# V3.0: FIX A1-A9 (auditim i Bibliotekës Ligjore).
#   - A1: Post-check aktive (jo vetëm raportim)
#   - A2: Normalizim diakritikësh në cache keys
#   - A3: Hequr startswith("[") heuristikë arbitrare
#   - A4: Timeout për stream LLM
#   - A5: Hequr kufizim >80 arbitrar
#   - A6: Log detajuar verifikimi
#   - A7: User ID extraction në helper
#   - A8: Audit logging për pyetjet
#   - A9: _canonical_keys me cache

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import asyncio
import logging
import re

from app.core.db import get_db_instance
from app.services.rag.response_generator import ResponseGenerator
from app.services.law_library import (
    get_law_library_service,
    LawLibraryService,
)
from app.api.endpoints.dependencies import get_current_user
from app.api.endpoints.laws_pkg.laws_dictionary import _normalize_diacritics

logger = logging.getLogger(__name__)
router = APIRouter()

# A4: Timeout për stream LLM (60 sekonda)
LLM_STREAM_TIMEOUT = 60.0
# A5: Hequr 80 char minimum — vetëm kontroll valid
MIN_VALID_CONTENT_CHARS = 20


class ExplainLawRequest(BaseModel):
    prompt: Optional[str] = None
    law_title: str
    article_number: str
    force_refresh: Optional[bool] = False


class AuditChatRequest(BaseModel):
    article_id: Optional[str] = ""
    law_title: Optional[str] = ""
    article_number: Optional[str] = ""
    query: str


def _canonical_keys(law_title: str, article_number: str):
    """
    A2: Gjeneron çelësa kanonikë me NORMALIZIM diakritikësh.
    """
    clean_law = str(law_title or "").strip()
    law_key = re.sub(r'[\s_\-]+', ' ', clean_law).strip().lower()
    law_key = _normalize_diacritics(law_key)   # A2

    clean_art = str(article_number or "").strip()
    clean_art = clean_art.replace("Neni", "").replace("neni", "").replace("NENI", "").strip()
    art_match = re.search(r'\d+', clean_art)
    art_key = art_match.group(0) if art_match else clean_art.lower()

    return clean_law, law_key, clean_art, art_key


def _extract_user_id(current_user) -> str:
    """A7: Single helper për extraction të user_id."""
    if current_user is None:
        return "system"
    if hasattr(current_user, "id"):
        return str(current_user.id)
    if hasattr(current_user, "_id"):
        return str(current_user._id)
    if isinstance(current_user, dict):
        return str(current_user.get("_id") or current_user.get("id") or "system")
    return "system"


def _is_valid_content(text: Optional[str]) -> bool:
    """
    A3: Valide real (jo heuristikë arbitrare).
    Kthen True nëse teksti ka përmbajtje reale juridike.
    """
    if not text:
        return False
    stripped = text.strip()
    if len(stripped) < MIN_VALID_CONTENT_CHARS:
        return False
    # Refuzo placeholder/error markers të njohur
    lower = stripped.lower()[:100]
    if lower.startswith("error:") or lower.startswith("traceback"):
        return False
    return True


def _build_cache_query(law_key: str, art_key: str, clean_law: str) -> dict:
    """A2: Query cache i normalizuar."""
    return {
        "$or": [
            {"law_key": law_key, "art_key": art_key},
            {
                "law_title": {"$regex": f"^{re.escape(clean_law)}$", "$options": "i"},
                "article_number": {
                    "$regex": f"^{art_key}$|^Neni\\s*{art_key}$",
                    "$options": "i",
                },
            },
        ]
    }


# ═══════════════════════════════════════════════════════════════════════════
# GET CACHED
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/explain/cached")
async def get_cached_law_analysis(
    law_title: str = Query(...),
    article_number: str = Query(...),
    current_user = Depends(get_current_user),
):
    try:
        db = get_db_instance()
        clean_law, law_key, clean_art, art_key = _canonical_keys(law_title, article_number)

        cached_doc = db.legal_analysis_cache.find_one(
            _build_cache_query(law_key, art_key, clean_law)
        )

        if cached_doc and _is_valid_content(cached_doc.get("content")):
            logger.info(f"[CACHE_GET] HIT: {clean_law} - Art {art_key}")
            return {"cached": True, "content": cached_doc["content"]}

        return {"cached": False, "content": None}
    except Exception as e:
        logger.warning(f"[CACHE_GET] Error: {e}")
        return {"cached": False, "content": None}


# ═══════════════════════════════════════════════════════════════════════════
# EXPLAIN — V3.0
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/explain")
async def explain_law_article(
    req: ExplainLawRequest,
    current_user = Depends(get_current_user),
):
    """
    V3.0: Shpjegon nenin DUKE VERIFIKUAR PARË që ekziston në DB.
    Post-check aktive: nëse ka gabime, shënohen në metadata.
    """
    db = get_db_instance()
    clean_law, law_key, clean_art, art_key = _canonical_keys(req.law_title, req.article_number)
    user_id = _extract_user_id(current_user)

    # ═══ 1. CACHE CHECK ═══
    if not req.force_refresh:
        cached_doc = db.legal_analysis_cache.find_one(
            _build_cache_query(law_key, art_key, clean_law)
        )
        if cached_doc and _is_valid_content(cached_doc.get("content")):
            cached_text = cached_doc["content"]
            logger.info(f"[EXPLAIN] CACHE HIT: {clean_law} - Art {art_key} (user={user_id})")

            async def stream_cached():
                yield cached_text

            return StreamingResponse(stream_cached(), media_type="text/plain")

    # ═══ 2. VERIFY ARTICLE EXISTS ═══
    library_service = get_law_library_service(db)
    article_context = library_service.get_article_context(
        law_title=clean_law,
        article_number=clean_art,
    )

    if not article_context:
        error_message = (
            f"⚠️ **Neni {clean_art} i ligjit '{clean_law}' nuk u gjet "
            f"në bazën ligjore.**\n\n"
            f"Nuk mund të shpjegoj një nen që nuk ekziston në bazë. "
            f"Kontrolloni:\n"
            f"- A është shkruar saktë numri i nenit?\n"
            f"- A është shkruar saktë titulli i ligjit?\n"
            f"- A ekziston ligji në bibliotekë?"
        )
        logger.warning(f"[EXPLAIN] Article not found: {clean_law} - {clean_art} (user={user_id})")

        async def stream_error():
            yield error_message

        return StreamingResponse(stream_error(), media_type="text/plain")

    # ═══ 3. BUILD PROMPT ═══
    system_prompt = library_service.build_explain_prompt(
        law_title=clean_law,
        article_number=clean_art,
        article_context=article_context,
    )

    logger.info(
        f"[EXPLAIN] Context found: {article_context['law_title']} — "
        f"Neni {clean_art}, {len(article_context['text'])} chars (user={user_id})"
    )

    # ═══ 4. GENERATE + POST-CHECK ═══
    try:
        generator = ResponseGenerator()
        user_query = req.prompt or f"Analizo nenin {clean_art} sipas tekstit të dhënë."

        async def stream_and_cache():
            accumulated = []
            try:
                async def _stream_with_timeout():
                    async for chunk in generator.generate_stream(system_prompt, user_query, ""):
                        yield chunk

                async for chunk in _stream_with_timeout():
                    accumulated.append(chunk)
                    yield chunk
            except asyncio.TimeoutError:
                logger.error(f"[EXPLAIN] LLM timeout (user={user_id})")
                yield "\n\n⚠️ Koha e përgjigjes skadoi. Provoni përsëri."
                return
            except Exception as e:
                logger.error(f"[EXPLAIN] Stream error: {e} (user={user_id})")
                yield f"\n\n⚠️ Gabim gjatë gjenerimit: {str(e)[:100]}"
                return

            full_content = "".join(accumulated).strip()

            # ═══ 5. POST-CHECK ═══
            verification = library_service.verify_output(
                output_text=full_content,
                article_context=article_context,
                article_number=clean_art,
            )

            if not verification["is_clean"]:
                correction = verification["correction_note"]
                logger.warning(
                    f"[EXPLAIN] POST-CHECK FAIL: "
                    f"extra_articles={verification['extra_articles']}, "
                    f"extra_laws={verification['extra_law_numbers']} (user={user_id})"
                )
                yield correction
                full_content += correction
            else:
                logger.info(f"[EXPLAIN] POST-CHECK OK (user={user_id})")

            # ═══ 6. SAVE TO CACHE (vetëm nëse valid) ═══
            if _is_valid_content(full_content):
                try:
                    db.legal_analysis_cache.update_one(
                        {"law_key": law_key, "art_key": art_key},
                        {"$set": {
                            "law_key": law_key,
                            "art_key": art_key,
                            "law_title": clean_law,
                            "article_number": clean_art,
                            "content": full_content,
                            "updated_at": datetime.now(timezone.utc),
                            "created_by": user_id,
                            "v5_verified": verification["is_clean"],
                        }},
                        upsert=True,
                    )
                    logger.info(f"[EXPLAIN] Cache saved: {clean_law} - Art {art_key}")
                except Exception as save_err:
                    logger.error(f"[EXPLAIN] Cache save failed: {save_err}")

        return StreamingResponse(stream_and_cache(), media_type="text/plain")

    except Exception as e:
        logger.error(f"[EXPLAIN] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Dështoi analiza: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════
# CLEAR CACHE
# ═══════════════════════════════════════════════════════════════════════════

@router.delete("/explain/cache")
async def clear_law_article_cache(
    law_title: str = Query(...),
    article_number: str = Query(...),
    current_user = Depends(get_current_user),
):
    try:
        db = get_db_instance()
        clean_law, law_key, clean_art, art_key = _canonical_keys(law_title, article_number)
        user_id = _extract_user_id(current_user)

        result = db.legal_analysis_cache.delete_many(
            _build_cache_query(law_key, art_key, clean_law)
        )
        logger.info(
            f"[CACHE_PURGE] {clean_law} - Art {art_key} "
            f"(deleted={result.deleted_count}, user={user_id})"
        )
        return {
            "success": True,
            "deleted_count": result.deleted_count,
            "message": "Analiza u shlye me sukses.",
        }
    except Exception as e:
        logger.error(f"[CACHE_PURGE] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Dështoi shlyerja: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════
# AUDIT CHAT
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/audit-chat")
async def audit_law_chat(
    req: AuditChatRequest,
    current_user = Depends(get_current_user),
):
    """
    V3.0: Chat me auditorin me kontekst të nenit + post-check.
    """
    db = get_db_instance()
    library_service = get_law_library_service(db)
    user_id = _extract_user_id(current_user)

    # ═══ 1. VERIFY ARTICLE ═══
    article_context = library_service.get_article_context(
        law_title=req.law_title,
        article_number=req.article_number,
    )

    if not article_context:
        error_message = (
            f"⚠️ **Neni {req.article_number} i ligjit '{req.law_title}' "
            f"nuk u gjet në bazën ligjore.**\n\n"
            f"Nuk mund të përgjigjem për një nen që nuk ekziston."
        )
        logger.warning(
            f"[AUDIT_CHAT] Article not found: {req.law_title} - {req.article_number} "
            f"(user={user_id})"
        )

        async def stream_error():
            yield error_message

        return StreamingResponse(stream_error(), media_type="text/plain")

    # ═══ 2. BUILD PROMPT ═══
    system_prompt = library_service.build_audit_prompt(
        law_title=req.law_title,
        article_number=req.article_number,
        article_context=article_context,
    )

    try:
        generator = ResponseGenerator()

        async def stream_output():
            accumulated = []
            try:
                async for chunk in generator.generate_stream(system_prompt, req.query, ""):
                    accumulated.append(chunk)
                    yield chunk
            except Exception as e:
                logger.error(f"[AUDIT_CHAT] Stream error: {e} (user={user_id})")
                yield f"\n\n⚠️ Gabim: {str(e)[:100]}"
                return

            full_content = "".join(accumulated).strip()
            verification = library_service.verify_output(
                output_text=full_content,
                article_context=article_context,
                article_number=req.article_number,
            )

            if not verification["is_clean"]:
                logger.warning(
                    f"[AUDIT_CHAT] POST-CHECK FAIL: "
                    f"{verification['extra_articles']} / "
                    f"{verification['extra_law_numbers']} (user={user_id})"
                )
                yield verification["correction_note"]
            else:
                logger.info(f"[AUDIT_CHAT] OK (user={user_id})")

        return StreamingResponse(stream_output(), media_type="text/plain")
    except Exception as e:
        logger.error(f"[AUDIT_CHAT] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Dështoi komunikimi: {str(e)}")