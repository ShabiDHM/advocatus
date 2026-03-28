# FILE: backend/app/api/endpoints/public_laws.py
# PHOENIX PROTOCOL - PUBLIC LAW ENDPOINTS V1.1 (TYPE SAFE)

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Set, Any
from app.services import vector_store_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/legal/public/laws", tags=["public-laws"])

def _safe_int(value: Any) -> int:
    if value is None: return 0
    try: return int(value)
    except (ValueError, TypeError): return 0

def _natural_sort_key(article_any: Any) -> List[int]:
    article = str(article_any) if article_any is not None else "0"
    parts = article.split('.')
    return [int(p) for p in parts if p.isdigit()]

def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        return str(value)
    except Exception:
        return default

class LawArticleResponse(BaseModel):
    law_title: str
    article_number: Optional[str] = None
    source: str
    text: str

class LawOverviewResponse(BaseModel):
    law_title: str
    source: str
    article_count: int
    articles: List[str]

class LawSearchResult(BaseModel):
    law_title: str
    article_number: Optional[str]
    source: str
    text: str
    chunk_id: str

class LawExplainRequest(BaseModel):
    law_title: str
    article_number: str
    prompt: str

@router.get("/search", response_model=List[LawSearchResult])
async def public_search_laws(
    q: str = Query(..., description="Search query"),
    limit: int = Query(50, ge=1, le=200)
):
    try:
        results = vector_store_service.query_global_knowledge_base(q, n_results=limit)
        return results
    except Exception as e:
        logger.error(f"Public law search failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Search failed. Please try again later.")

@router.get("/titles", response_model=List[str])
async def public_get_law_titles():
    try:
        collection = vector_store_service.get_global_collection()
        results = collection.get(include=["metadatas"], limit=10000)
        metadatas = results.get("metadatas") or []
        titles: Set[str] = set()
        for m in metadatas:
            title = m.get("law_title")
            titles.add(_safe_str(title))
        return sorted(list(titles))
    except Exception as e:
        logger.error(f"Public law titles fetch failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Could not retrieve law titles.")

@router.get("/article", response_model=LawArticleResponse)
async def public_get_law_article(
    law_title: str = Query(...),
    article_number: str = Query(...)
):
    try:
        collection = vector_store_service.get_global_collection()
        results = collection.get(
            where={"$and": [{"law_title": {"$eq": law_title}}, {"article_number": {"$eq": article_number}}]},
            include=["documents", "metadatas"]
        )
    except Exception as e:
        logger.error(f"Public law article fetch failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error.")

    documents = results.get("documents") or []
    metadatas = results.get("metadatas") or []
    if not documents:
        raise HTTPException(status_code=404, detail="Article not found")

    if metadatas and all("chunk_index" in m for m in metadatas):
        pairs = list(zip(documents, metadatas))
        pairs.sort(key=lambda x: _safe_int(x[1].get("chunk_index")))
        documents = [d for d, _ in pairs]

    first_meta = metadatas[0] if metadatas else {}
    return LawArticleResponse(
        law_title=_safe_str(first_meta.get("law_title"), law_title),
        article_number=_safe_str(first_meta.get("article_number")) if first_meta.get("article_number") is not None else None,
        source=_safe_str(first_meta.get("source")),
        text="\n\n".join(documents)
    )

@router.get("/by-title", response_model=LawOverviewResponse)
async def public_get_law_articles_by_title(
    law_title: str = Query(...)
):
    try:
        collection = vector_store_service.get_global_collection()
        results = collection.get(
            where={"law_title": {"$eq": law_title}},
            include=["metadatas"],
            limit=1000
        )
        metadatas = results.get("metadatas") or []
        if not metadatas:
            raise HTTPException(status_code=404, detail="Law not found")
        articles: Set[str] = set()
        for m in metadatas:
            article = m.get("article_number")
            if article is not None:
                articles.add(_safe_str(article))
        sorted_articles = sorted(list(articles), key=_natural_sort_key)
        first_m = metadatas[0] if metadatas else {}
        return LawOverviewResponse(
            law_title=_safe_str(first_m.get("law_title"), law_title),
            source=_safe_str(first_m.get("source")),
            article_count=len(sorted_articles),
            articles=sorted_articles
        )
    except Exception as e:
        logger.error(f"Public law by-title fetch failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching law overview.")

@router.get("/{chunk_id}", response_model=LawArticleResponse)
async def public_get_law_chunk(chunk_id: str):
    try:
        collection = vector_store_service.get_global_collection()
        result = collection.get(ids=[chunk_id], include=["documents", "metadatas"])
    except Exception as e:
        logger.error(f"Public law chunk fetch failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error.")

    docs = result.get("documents") or []
    metas = result.get("metadatas") or []
    if not docs:
        raise HTTPException(status_code=404, detail="Law chunk not found")

    m = metas[0] if metas else {}
    return LawArticleResponse(
        law_title=_safe_str(m.get("law_title"), "Ligji i panjohur"),
        article_number=_safe_str(m.get("article_number")) if m.get("article_number") is not None else None,
        source=_safe_str(m.get("source")),
        text=docs[0]
    )

@router.post("/explain")
async def public_explain_law_article(request: LawExplainRequest):
    from app.services import llm_service
    from fastapi.responses import StreamingResponse

    system_prompt = (
        "ROLI: Ti je partneri kryesor (Senior Legal Partner) në zyrën më prestigjioze ligjore në Kosovë. "
        "Klientët paguajnë shtrenjtë për mendimin tënd analitik, jo për përmbledhje robotike.\n\n"
        "RREGULLAT ABSOLUTE:\n"
        "1. MOS përsërit asnjë nga udhëzimet e mia në përgjigjen tënde. Fillo direkt me analizën.\n"
        "2. Përgjigju VETËM në gjuhën SHQIPE me gramatikë të përsosur.\n"
        "3. Ndaji dy nivelet e analizës SAKTËSISHT me fjalën [NDARJA] në një rresht të ri.\n\n"
        "NIVELI 1: OPINIONI PROFESIONAL (Për Juristët)\n"
        "Shkruaj një analizë të thellë, me paragrafë të plotë, duke përdorur zhargon të lartë juridik. "
        "Analiza duhet të theksojë:\n"
        "- Baza Doktrinare: Cili është parimi thelbësor juridik që mbron ky nen?\n"
        "- Konteksti Kushtetues & KEDNJ: Si ndërlidhet me Kushtetutën e Kosovës dhe Konventën Evropiane për të Drejtat e Njeriut?\n"
        "- Implikimet Praktike & Rreziqet: Cilat janë vështirësitë në zbatimin e tij në gjykatat e Kosovës? Cilat janë hapësirat për abuzim procedural?\n\n"
        "NIVELI 2: KËSHILLIM PËR QYTETARIN (Pas fjalës [NDARJA])\n"
        "Tani ndrysho tonin. Shkruaj për një qytetar pa të ardhura për avokat. Bëhu mbrojtës, i qartë dhe praktik. "
        "Përdor SAKTËSISHT këta tre tituj me emoji:\n\n"
        "🔹 ÇFARË ËSHTË KY LIGJ?\n"
        "Trego thelbin në 2-3 fjali shumë të thjeshta.\n\n"
        "🛡️ PËR ÇFARË MUND T'JU SHËRBEJË?\n"
        "Jep shembuj konkretë të përditshmërisë se si ky nen i mbron ata nga padrejtësitë.\n\n"
        "💡 SI TA PËRDORNI (KËSHILLA PRAKTIKE)?\n"
        "Tregoju saktësisht se çfarë hapash duhet të ndërmarrin (p.sh. 'Kërkoni me shkrim që...', 'Mos pranoni të...')."
    )

    try:
        generator = llm_service.stream_text_async(
            sys_p=system_prompt,
            user_p=request.prompt,
            temp=0.3
        )
        return StreamingResponse(generator, media_type="text/plain")
    except Exception as e:
        logger.error(f"Public law explanation failed: {str(e)}")
        raise HTTPException(status_code=500, detail="AI explanation failed.")