# FILE: backend/app/api/endpoints/laws.py
# PHOENIX PROTOCOL - LAWS ENDPOINTS V8.0 (UNABRIDGED DUAL PERSPECTIVE)
# 1. ENHANCED: /explain generates Senior Partner AND Normal Citizen analysis.
# 2. FIXED: /explain is at the top to prevent wildcard shadowing (405 errors).
# 3. FIXED: Pylance type-safety (safe casting for metadata sets and sorts).
# 4. RETAINED: 100% of retrieval, search, title, and chunk logic. No omissions.

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Set, Any
from app.services import vector_store_service, llm_service
from app.api.endpoints.dependencies import get_current_user

router = APIRouter(tags=["Laws"])

# --- MODELS ---

class LawExplainRequest(BaseModel):
    law_title: str
    article_number: str
    prompt: str

# --- UTILITY FUNCTIONS ---

def _safe_int(value: Any) -> int:
    """Convert metadata value to int safely; return 0 if not possible."""
    if value is None:
        return 0
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0

def _natural_sort_key(article_any: Any) -> List[int]:
    """Split article number into parts for natural sorting (e.g., 5.1 -> [5,1])."""
    article = str(article_any) if article_any is not None else "0"
    parts = article.split('.')
    return [int(p) for p in parts if p.isdigit()]

# --- 1. AI ANALYSIS ENDPOINT (HIGHEST PRIORITY) ---

@router.post("/explain")
async def explain_law_article(
    request: LawExplainRequest,
    current_user = Depends(get_current_user)
):
    """
    PHOENIX: Streams a dual-layered AI explanation.
    Instructs the LLM to output a technical 'Senior Partner' analysis,
    followed by a '---' separator, and then a layman 'Citizen' explanation.
    """
    system_prompt = (
        "DETYRA: Analizo këtë nen ligjor nga dy perspektiva të ndryshme.\n\n"
        "PJESA 1: Perspektiva e 'Senior Legal Partner'\n"
        "- Toni: Autoritar, teknik, doktrinar.\n"
        "- Fokusohu: Lidhja me Kushtetutën e Kosovës, Konventën Evropiane për të Drejtat e Njeriut (KEDNJ), "
        "parimet e procedurës (p.sh. parimi i legalitetit) dhe rreziqet statutore.\n\n"
        "PJESA 2: Perspektiva e Qytetarit të Thjeshtë\n"
        "- Toni: Miqësor, i qartë, pa zhargon juridik.\n"
        "- Fokusohu: Çfarë do të thotë kjo për qytetarin? Cilat janë të drejtat apo detyrimet e tij "
        "në jetën e përditshme? Jep një shembull të thjeshtë praktik.\n\n"
        "FORMATI: Ndaji TË DY pjesët VETËM me markerin '---' në një rresht të ri.\n"
        "GJUHA: Përgjigju VETËM në gjuhën SHQIPE."
    )
    
    try:
        # Trigger the stream from llm_service (which appends the AI_DISCLAIMER)
        generator = llm_service.stream_text_async(
            sys_p=system_prompt,
            user_p=request.prompt,
            temp=0.2  # Low temperature for precise legal analysis
        )
        return StreamingResponse(generator, media_type="text/plain")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Synthesis failed: {str(e)}")

# --- 2. DATA RETRIEVAL ENDPOINTS ---

@router.get("/search")
async def search_laws(
    q: str = Query(..., description="Search query"),
    limit: int = Query(50, ge=1, le=200),
    current_user = Depends(get_current_user)
):
    """Semantic search for laws. Returns matching chunks with metadata."""
    try:
        results = vector_store_service.query_global_knowledge_base(q, n_results=limit)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/titles")
async def get_law_titles(
    current_user = Depends(get_current_user)
):
    """Get all distinct law titles, sorted alphabetically."""
    try:
        collection = vector_store_service.get_global_collection()
        # Fetch up to 10000 chunks (should cover all laws)
        results = collection.get(include=["metadatas"], limit=10000)
        metadatas = results.get("metadatas") or []
        
        titles: Set[str] = set()
        for m in metadatas:
            title = m.get("law_title")
            if isinstance(title, str):
                titles.add(title)
        
        sorted_titles = sorted(list(titles))
        return sorted_titles
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching titles: {str(e)}")

@router.get("/article")
async def get_law_article(
    law_title: str = Query(..., description="Law title"),
    article_number: str = Query(..., description="Article number"),
    current_user = Depends(get_current_user)
):
    """Retrieve all chunks belonging to a specific article and combine them."""
    try:
        collection = vector_store_service.get_global_collection()
        results = collection.get(
            where={
                "$and": [
                    {"law_title": {"$eq": law_title}},
                    {"article_number": {"$eq": article_number}}
                ]
            },
            include=["documents", "metadatas"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    documents = results.get("documents") or []
    metadatas = results.get("metadatas") or []
    
    if not documents:
        raise HTTPException(status_code=404, detail="Article not found")

    # Sort chunks by chunk_index if present
    if metadatas and all("chunk_index" in m for m in metadatas):
        pairs = list(zip(documents, metadatas))
        pairs.sort(key=lambda x: _safe_int(x[1].get("chunk_index")))
        documents = [d for d, _ in pairs]
        metadatas = [m for _, m in pairs]

    # Combine all chunks into a single text body
    full_text = "\n\n".join(documents)

    meta = metadatas[0] if metadatas else {}
    return {
        "law_title": str(meta.get("law_title", law_title)),
        "article_number": str(meta.get("article_number", article_number)),
        "source": str(meta.get("source", "")),
        "text": full_text
    }

@router.get("/by-title")
async def get_law_articles(
    law_title: str = Query(..., description="Law title"),
    current_user = Depends(get_current_user)
):
    """Retrieve article numbers for a law title (Table of Contents)."""
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

        # Collect unique article numbers safely (string cast for hashability)
        articles: Set[str] = set()
        for m in metadatas:
            art = m.get("article_number")
            if art is not None:
                articles.add(str(art))

        # Sort naturally
        sorted_articles = sorted(list(articles), key=_natural_sort_key)

        first = metadatas[0]
        return {
            "law_title": str(first.get("law_title", law_title)),
            "source": str(first.get("source", "")),
            "article_count": len(sorted_articles),
            "articles": sorted_articles
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@router.get("/{chunk_id}")
async def get_law_chunk(
    chunk_id: str,
    current_user = Depends(get_current_user)
):
    """
    WILDCARD ROUTE: Retrieve a specific law chunk by its ID. 
    Must remain at the bottom of the file so it doesn't intercept /explain or other specific paths.
    """
    try:
        collection = vector_store_service.get_global_collection()
        result = collection.get(ids=[chunk_id], include=["documents", "metadatas"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    if result is None:
        raise HTTPException(status_code=404, detail="Law chunk not found")

    documents = result.get("documents") or []
    metadatas = result.get("metadatas") or []

    if not documents:
        raise HTTPException(status_code=404, detail="Law chunk not found")

    law_text = documents[0]
    metadata = metadatas[0] if metadatas else {}

    return {
        "law_title": str(metadata.get("law_title", "Ligji i panjohur")),
        "article_number": str(metadata.get("article_number", "")),
        "source": str(metadata.get("source", "")),
        "text": law_text
    }