# FILE: backend/app/api/endpoints/laws_pkg/laws_audit_router.py
# PHOENIX PROTOCOL - DEDICATED LAW AUDIT & AI EXPLAIN ROUTER (ISOLATED MODULE)

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import logging

from app.services.rag.response_generator import ResponseGenerator
from app.api.endpoints.dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


class ExplainLawRequest(BaseModel):
    prompt: Optional[str] = None
    law_title: str
    article_number: str


class AuditChatRequest(BaseModel):
    article_id: Optional[str] = ""
    law_title: Optional[str] = ""
    article_number: Optional[str] = ""
    query: str


@router.post("/explain")
async def explain_law_article(
    req: ExplainLawRequest,
    current_user = Depends(get_current_user)
):
    """
    Gjeneron analizë dhe sqarim inteligjent në kohë reale mbi nenin e ligjit.
    Modul i izoluar për shpjegim ligjor.
    """
    try:
        generator = ResponseGenerator()
        
        system_prompt = (
            "Ti je 'Sokrati' - Eksperti Kryesor Ligjor dhe Juristi AI i Kosovës.\n"
            "Detyra jote është të bësh një ANALIZË TË THELLË DHE TË QARTË JURIDIKE mbi këtë nen.\n"
            "Strukturo përgjigjen me tituj të qartë:\n"
            "1. 📌 **Qëllimi Kryesor dhe Ratio Legis**\n"
            "2. ⚖️ **Zbatimi Praktik dhe Kushtet Ligjore**\n"
            "3. ⚠️ **Rreziqet, Pasojat dhe Afatet Procedurale**\n"
            "4. 🔗 **Ndërlidhja me Ligjet dhe Praktikën Gjyqësore të Kosovës**\n"
            "Përgjigju në shqip të pastër standard, me saktësi absolute dhe autoritet profesional."
        )

        user_query = req.prompt or f"Shpjego Nenin {req.article_number} të ligjit '{req.law_title}'"

        async def stream_output():
            async for chunk in generator.generate_stream(system_prompt, user_query, ""):
                yield chunk

        return StreamingResponse(stream_output(), media_type="text/plain")
    except Exception as e:
        logger.error(f"[LawAuditRouter] Explain streaming error: {e}")
        raise HTTPException(status_code=500, detail=f"Dështoi analiza: {str(e)}")


@router.post("/audit-chat")
async def audit_law_chat(
    req: AuditChatRequest,
    current_user = Depends(get_current_user)
):
    """
    Mundëson bisedë interaktive dhe auditim profesional për nenin përkatës.
    Modul i izoluar për bashkëbisedim me auditorin.
    """
    try:
        generator = ResponseGenerator()

        system_prompt = (
            "Ti je 'Auditori Ligjor' i platformës Juristi.tech në Kosovë.\n"
            f"Po auditon ligjin: **{req.law_title}**, Neni: **{req.article_number}**.\n"
            "Përgjigju pyetjes së përdoruesit duke u bazuar me përpikmëri në frymën dhe tekstin e ligjit, "
            "pa sajuar asnjë normë, dhe ofro këshilla konkrete profesionale procedurale."
        )

        async def stream_output():
            async for chunk in generator.generate_stream(system_prompt, req.query, ""):
                yield chunk

        return StreamingResponse(stream_output(), media_type="text/plain")
    except Exception as e:
        logger.error(f"[LawAuditRouter] Audit chat error: {e}")
        raise HTTPException(status_code=500, detail=f"Dështoi komunikimi me auditorin: {str(e)}")