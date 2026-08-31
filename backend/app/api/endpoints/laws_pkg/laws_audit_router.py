# FILE: backend/app/api/endpoints/laws_pkg/laws_audit_router.py
# PHOENIX PROTOCOL - LAW AUDIT ROUTER WITH FLEXIBLE REGEX CACHE MATCHING

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import logging
import re

from app.core.db import get_db_instance
from app.services.rag.response_generator import ResponseGenerator
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


def _clean_article_query(art: str) -> str:
    """Nxjerr vetëm numrin e pastër të nenit për kërkim të sigurt në cache."""
    clean = str(art).strip().replace("Neni", "").replace("neni", "").strip()
    match = re.search(r'\d+', clean)
    return match.group(0) if match else clean


@router.get("/explain/cached")
async def get_cached_law_analysis(
    law_title: str = Query(...),
    article_number: str = Query(...),
    current_user = Depends(get_current_user)
):
    """Kthen menjëherë analizën e ruajtur në MongoDB me kërkim fleksibil."""
    try:
        db = get_db_instance()
        clean_law = law_title.strip()
        clean_art = _clean_article_query(article_number)

        # Kërkim fleksibil që gjen nenin pavarësisht fjalës 'Neni' apo hapësirave
        cached_doc = db.legal_analysis_cache.find_one({
            "law_title": {"$regex": f"^{re.escape(clean_law)}$", "$options": "i"},
            "article_number": {"$regex": f"^{clean_art}$|^Neni\\s*{clean_art}$", "$options": "i"}
        })

        if cached_doc and cached_doc.get("content"):
            content = cached_doc.get("content")
            if not content.startswith("[") and len(content) > 60:
                logger.info(f"⚡ [CACHE FOUND ON GET] {clean_law} - Art {clean_art}")
                return {"cached": True, "content": content}

        return {"cached": False, "content": None}
    except Exception as e:
        logger.warning(f"Error reading cache: {e}")
        return {"cached": False, "content": None}


@router.post("/explain")
async def explain_law_article(
    req: ExplainLawRequest,
    current_user = Depends(get_current_user)
):
    """Gjeneron analizë ligjore në shqip të pastër me DeepSeek dhe Multi-Device Cache."""
    db = get_db_instance()
    clean_law = req.law_title.strip()
    clean_art = _clean_article_query(req.article_number)

    # 1. KONTROLLO CACHE-IN NË MONGODB
    if not req.force_refresh:
        cached_doc = db.legal_analysis_cache.find_one({
            "law_title": {"$regex": f"^{re.escape(clean_law)}$", "$options": "i"},
            "article_number": {"$regex": f"^{clean_art}$|^Neni\\s*{clean_art}$", "$options": "i"}
        })
        if cached_doc and cached_doc.get("content"):
            cached_text = cached_doc.get("content")
            if not cached_text.startswith("[") and len(cached_text) > 60:
                logger.info(f"⚡ [CACHE HIT ON POST] DeepSeek analysis for {clean_law} - Art {clean_art}")

                async def stream_cached():
                    yield cached_text

                return StreamingResponse(stream_cached(), media_type="text/plain")

    # 2. GJENERIMI ME DEEPSEEK (100% SHQIP PA LATINISHT)
    try:
        generator = ResponseGenerator()
        
        system_prompt = (
            "Ti je 'Sokrati' - Eksperti Kryesor Ligjor dhe Juristi AI i Kosovës.\n"
            "Detyra jote është të bësh një ANALIZË TË THELLË DHE TË QARTË JURIDIKE në gjuhën shqipe mbi këtë nen.\n\n"
            "RREGULLAT GJUHËSORE DHE FORMATIMI:\n"
            "1. Përdor VETËM gjuhë të pastër shqipe standarde. MOS përdor asnjë term në latinisht (si 'ratio legis', 'de jure', 'de facto', etj.) apo gjuhë të huaja.\n"
            "2. Mos përdor linqe URL.\n"
            "3. Strukturo përgjigjen me këta 4 tituj kryesorë ekzaktësisht:\n"
            "📌 **Qëllimi Kryesor dhe Fryma e Ligjit**\n"
            "⚖️ **Zbatimi Praktik dhe Kushtet Ligjore**\n"
            "⚠️ **Rreziqet, Pasojat dhe Afatet Procedurale**\n"
            "🔗 **Ndërlidhja me Ligjet dhe Praktikën Gjyqësore të Kosovës**"
        )

        user_query = req.prompt or f"Shpjego Nenin {clean_art} të ligjit '{clean_law}'"

        async def stream_and_cache():
            accumulated = []
            async for chunk in generator.generate_stream(system_prompt, user_query, ""):
                accumulated.append(chunk)
                yield chunk
            
            full_content = "".join(accumulated).strip()
            if full_content and not full_content.startswith("[") and len(full_content) > 80:
                try:
                    db.legal_analysis_cache.update_one(
                        {"law_title": clean_law, "article_number": clean_art},
                        {"$set": {
                            "law_title": clean_law,
                            "article_number": clean_art,
                            "content": full_content,
                            "updated_at": datetime.now(timezone.utc),
                            "created_by": str(current_user.get("_id", "system"))
                        }},
                        upsert=True
                    )
                    logger.info(f"💾 [CACHE SAVED PERMANENTLY] DeepSeek analysis for {clean_law} - Art {clean_art}")
                except Exception as save_err:
                    logger.warning(f"Cache save error: {save_err}")

        return StreamingResponse(stream_and_cache(), media_type="text/plain")
    except Exception as e:
        logger.error(f"[LawAuditRouter] Explain streaming error: {e}")
        raise HTTPException(status_code=500, detail=f"Dështoi analiza: {str(e)}")


@router.delete("/explain/cache")
async def clear_law_article_cache(
    law_title: str = Query(...),
    article_number: str = Query(...),
    current_user = Depends(get_current_user)
):
    """Fshin analizën e ruajtur në cache për këtë nen."""
    try:
        db = get_db_instance()
        clean_law = law_title.strip()
        clean_art = _clean_article_query(article_number)

        result = db.legal_analysis_cache.delete_many({
            "law_title": {"$regex": f"^{re.escape(clean_law)}$", "$options": "i"},
            "article_number": {"$regex": f"^{clean_art}$|^Neni\\s*{clean_art}$", "$options": "i"}
        })
        logger.info(f"🗑️ [CACHE PURGED] {clean_law} - Art {clean_art} (Deleted: {result.deleted_count})")
        return {"success": True, "deleted_count": result.deleted_count, "message": "Analiza u shlye me sukses nga memoria."}
    except Exception as e:
        logger.error(f"Error purging cache: {e}")
        raise HTTPException(status_code=500, detail=f"Dështoi shlyerja e memories: {str(e)}")


@router.post("/audit-chat")
async def audit_law_chat(
    req: AuditChatRequest,
    current_user = Depends(get_current_user)
):
    """Mundëson bisedë interaktive me DeepSeek në shqip të pastër."""
    try:
        generator = ResponseGenerator()

        system_prompt = (
            "Ti je 'Auditori Ligjor' i platformës Juristi.tech në Kosovë.\n"
            f"Po auditon ligjin: **{req.law_title}**, Neni: **{req.article_number}**.\n"
            "Përgjigju në shqip të pastër standard me saktësi absolute juridike sipas ligjeve të Kosovës, "
            "pa përdorur terma të huaj apo latinisht."
        )

        async def stream_output():
            async for chunk in generator.generate_stream(system_prompt, req.query, ""):
                yield chunk

        return StreamingResponse(stream_output(), media_type="text/plain")
    except Exception as e:
        logger.error(f"[LawAuditRouter] Audit chat error: {e}")
        raise HTTPException(status_code=500, detail=f"Dështoi komunikimi me auditorin: {str(e)}")