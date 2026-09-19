# FILE: backend/app/api/endpoints/laws_pkg/laws_audit_router.py
# PHOENIX PROTOCOL - LAWS AUDIT ROUTER V2.0 (V5 ARCHITECTURE)
# V2.0: Zbatohet filozofia V5:
#   - Python verifikon ekzistencën e nenit para se të shpjegojë
#   - LLM merr tekstin e saktë nga DB
#   - Post-processor kontrollon output-in për halluzinim

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone
import logging
import re

from app.core.db import get_db_instance
from app.services.rag.response_generator import ResponseGenerator
from app.services.law_library import (
    get_law_library_service,
    LawLibraryService,
)
from app.api.endpoints.dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


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
    """Gjeneron çelësa kanonikë."""
    clean_law = str(law_title).strip()
    law_key = re.sub(r'[\s_\-]+', ' ', clean_law).strip().lower()

    clean_art = str(article_number).strip().replace("Neni", "").replace("neni", "").strip()
    art_match = re.search(r'\d+', clean_art)
    art_key = art_match.group(0) if art_match else clean_art.lower()

    return clean_law, law_key, clean_art, art_key


# ═══════════════════════════════════════════════════════════════════════════
# GET CACHED
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/explain/cached")
async def get_cached_law_analysis(
    law_title: str = Query(...),
    article_number: str = Query(...),
    current_user = Depends(get_current_user)
):
    try:
        db = get_db_instance()
        clean_law, law_key, clean_art, art_key = _canonical_keys(law_title, article_number)

        cached_doc = db.legal_analysis_cache.find_one({
            "$or": [
                {"law_key": law_key, "art_key": art_key},
                {"law_title": {"$regex": f"^{re.escape(clean_law)}$", "$options": "i"},
                 "article_number": {"$regex": f"^{art_key}$|^Neni\\s*{art_key}$", "$options": "i"}}
            ]
        })

        if cached_doc and cached_doc.get("content"):
            content = cached_doc.get("content")
            if not content.startswith("[") and len(content) > 60:
                logger.info(f"⚡ [CACHE HIT ON GET] {clean_law} - Art {art_key}")
                return {"cached": True, "content": content}

        return {"cached": False, "content": None}
    except Exception as e:
        logger.warning(f"Error reading cache: {e}")
        return {"cached": False, "content": None}


# ═══════════════════════════════════════════════════════════════════════════
# EXPLAIN — V5 ARCHITECTURE
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/explain")
async def explain_law_article(
    req: ExplainLawRequest,
    current_user = Depends(get_current_user)
):
    """
    V5: Shpjegon nenin DUKE VERIFIKUAR PARË që ekziston në DB.
    """
    db = get_db_instance()
    clean_law, law_key, clean_art, art_key = _canonical_keys(req.law_title, req.article_number)

    # ═══ 1. CACHE CHECK ═══
    if not req.force_refresh:
        cached_doc = db.legal_analysis_cache.find_one({
            "$or": [
                {"law_key": law_key, "art_key": art_key},
                {"law_title": {"$regex": f"^{re.escape(clean_law)}$", "$options": "i"},
                 "article_number": {"$regex": f"^{art_key}$|^Neni\\s*{art_key}$", "$options": "i"}}
            ]
        })
        if cached_doc and cached_doc.get("content"):
            cached_text = cached_doc.get("content")
            if not cached_text.startswith("[") and len(cached_text) > 60:
                logger.info(f"⚡ [CACHE HIT ON POST] {clean_law} - Art {art_key}")

                async def stream_cached():
                    yield cached_text

                return StreamingResponse(stream_cached(), media_type="text/plain")

    # ═══ 2. VERIFY ARTICLE EXISTS IN DB (V5) ═══
    library_service = get_law_library_service(db)
    article_context = library_service.get_article_context(
        law_title=clean_law,
        article_number=clean_art,
    )

    if not article_context:
        # ❌ Neni nuk u gjet — mos shpik
        error_message = (
            f"⚠️ **Neni {clean_art} i ligjit '{clean_law}' nuk u gjet "
            f"në bazën ligjore.**\n\n"
            f"Nuk mund të shpjegoj një nen që nuk ekziston në bazë. "
            f"Kontrolloni:\n"
            f"- A është shkruar saktë numri i nenit?\n"
            f"- A është shkruar saktë titulli i ligjit?\n"
            f"- A ekziston ligji në bibliotekë?"
        )
        logger.warning(f"❌ [EXPLAIN V5] Article not found: {clean_law} - {clean_art}")

        async def stream_error():
            yield error_message

        return StreamingResponse(stream_error(), media_type="text/plain")

    # ═══ 3. BUILD PROMPT ME TEKSTIN E SAKTË ═══
    system_prompt = library_service.build_explain_prompt(
        law_title=clean_law,
        article_number=clean_art,
        article_context=article_context,
    )

    logger.info(
        f"📖 [EXPLAIN V5] Context found: {article_context['law_title']} — "
        f"Neni {clean_art}, {len(article_context['text'])} chars"
    )

    # ═══ 4. GENERATE + POST-CHECK ═══
    try:
        generator = ResponseGenerator()

        user_query = req.prompt or f"Analizo nenin {clean_art} sipas tekstit të dhënë."

        user_id_str = "system"
        if hasattr(current_user, "id"):
            user_id_str = str(current_user.id)
        elif hasattr(current_user, "_id"):
            user_id_str = str(current_user._id)
        elif isinstance(current_user, dict):
            user_id_str = str(current_user.get("_id") or current_user.get("id") or "system")

        async def stream_and_cache():
            accumulated = []
            async for chunk in generator.generate_stream(system_prompt, user_query, ""):
                accumulated.append(chunk)
                yield chunk

            full_content = "".join(accumulated).strip()

            # ═══ 5. POST-CHECK ═══
            verification = library_service.verify_output(
                output_text=full_content,
                article_context=article_context,
                article_number=clean_art,
            )

            # Nëse ka probleme → shto shënimin
            if not verification["is_clean"]:
                correction = verification["correction_note"]
                logger.warning(
                    f"⚠️ [EXPLAIN V5] Output has issues: "
                    f"extra_articles={verification['extra_articles']}, "
                    f"extra_laws={verification['extra_law_numbers']}"
                )
                yield correction
                full_content += correction

            # ═══ 6. SAVE TO CACHE ═══
            if full_content and not full_content.startswith("[") and len(full_content) > 80:
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
                            "created_by": user_id_str,
                            "v5_verified": verification["is_clean"],
                        }},
                        upsert=True
                    )
                    logger.info(f"💾 [CACHE SAVED V5] {clean_law} - Art {art_key}")
                except Exception as save_err:
                    logger.error(f"❌ Cache save failed: {save_err}")

        return StreamingResponse(stream_and_cache(), media_type="text/plain")

    except Exception as e:
        logger.error(f"[LawAuditRouter] Explain error: {e}")
        raise HTTPException(status_code=500, detail=f"Dështoi analiza: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════
# CLEAR CACHE
# ═══════════════════════════════════════════════════════════════════════════

@router.delete("/explain/cache")
async def clear_law_article_cache(
    law_title: str = Query(...),
    article_number: str = Query(...),
    current_user = Depends(get_current_user)
):
    try:
        db = get_db_instance()
        clean_law, law_key, clean_art, art_key = _canonical_keys(law_title, article_number)

        result = db.legal_analysis_cache.delete_many({
            "$or": [
                {"law_key": law_key, "art_key": art_key},
                {"law_title": {"$regex": f"^{re.escape(clean_law)}$", "$options": "i"},
                 "article_number": {"$regex": f"^{art_key}$|^Neni\\s*{art_key}$", "$options": "i"}}
            ]
        })
        logger.info(f"🗑️ [CACHE PURGED] {clean_law} - Art {art_key} (Deleted: {result.deleted_count})")
        return {"success": True, "deleted_count": result.deleted_count, "message": "Analiza u shlye me sukses."}
    except Exception as e:
        logger.error(f"Error purging cache: {e}")
        raise HTTPException(status_code=500, detail=f"Dështoi shlyerja: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════
# AUDIT CHAT — V5
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/audit-chat")
async def audit_law_chat(
    req: AuditChatRequest,
    current_user = Depends(get_current_user)
):
    """
    V5: Chat me auditorin DUKE PASUR TEKSTIN E NENIT NË KONTEKST.
    """
    db = get_db_instance()
    library_service = get_law_library_service(db)

    # ═══ 1. VERIFY ARTICLE EXISTS ═══
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

        async def stream_error():
            yield error_message

        return StreamingResponse(stream_error(), media_type="text/plain")

    # ═══ 2. BUILD PROMPT ME KONTEKST ═══
    system_prompt = library_service.build_audit_prompt(
        law_title=req.law_title,
        article_number=req.article_number,
        article_context=article_context,
    )

    try:
        generator = ResponseGenerator()

        async def stream_output():
            accumulated = []
            async for chunk in generator.generate_stream(system_prompt, req.query, ""):
                accumulated.append(chunk)
                yield chunk

            full_content = "".join(accumulated).strip()
            verification = library_service.verify_output(
                output_text=full_content,
                article_context=article_context,
                article_number=req.article_number,
            )

            if not verification["is_clean"]:
                yield verification["correction_note"]

        return StreamingResponse(stream_output(), media_type="text/plain")
    except Exception as e:
        logger.error(f"[LawAuditRouter] Audit chat error: {e}")
        raise HTTPException(status_code=500, detail=f"Dështoi komunikimi: {str(e)}")