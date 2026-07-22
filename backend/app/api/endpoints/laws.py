# FILE: backend/app/api/endpoints/laws.py
# PHOENIX PROTOCOL - LAWS ENDPOINTS V25.0 (EXPLICIT NDARJA MARKER PROMPT)

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse, FileResponse, RedirectResponse
from pydantic import BaseModel
from typing import Optional, List, Set, Any
import re
import os
import unicodedata
import logging

try:
    from app.services import vector_store_service, llm_service, storage_service
    from app.api.endpoints.dependencies import get_current_user
except ImportError:
    from ...services import vector_store_service, llm_service, storage_service
    from .dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Laws"])

class LawExplainRequest(BaseModel):
    law_title: str
    article_number: str
    prompt: str

class AuditChatRequest(BaseModel):
    law_title: str
    article_number: str
    query: str

def _safe_int(value: Any) -> int:
    if value is None: return 0
    try: return int(value)
    except (ValueError, TypeError): return 0

def _natural_sort_key(article_any: Any) -> List[int]:
    article = str(article_any) if article_any is not None else "0"
    parts = article.split('.')
    return [int(p) for p in parts if p.isdigit()]

def find_law_documents(db, raw_law_title: str, raw_article_num: str) -> List[dict]:
    clean_art = str(raw_article_num).replace('Neni', '').replace('neni', '').replace('.', '').strip()
    art_variants = [clean_art, f"{clean_art}.", f"Neni {clean_art}", f"NENI {clean_art}"]

    law_num_match = re.search(r'\b(\d{2,4}[\/\-][L\d\-]+(?:\d+)?)\b', raw_law_title, re.I)
    if law_num_match:
        law_code = law_num_match.group(1)
        query = {
            "law_title": {"$regex": re.escape(law_code), "$options": "i"},
            "article_number": {"$in": art_variants}
        }
        cursor = db.legal_knowledge_base.find(query).sort("chunk_index", 1)
        docs = list(cursor)
        if docs:
            return docs

    query = {
        "law_title": {"$regex": f"^{re.escape(raw_law_title.strip())}$", "$options": "i"},
        "article_number": {"$in": art_variants}
    }
    cursor = db.legal_knowledge_base.find(query).sort("chunk_index", 1)
    docs = list(cursor)
    if docs:
        return docs

    words = [w for w in raw_law_title.split() if len(w) > 3 and w.lower() not in ['ligji', 'ligjit', 'kodi', 'kodin', 'për', 'per', 'dhe']]
    if words:
        key_pattern = "|".join([re.escape(w) for w in words[:3]])
        query = {
            "law_title": {"$regex": key_pattern, "$options": "i"},
            "article_number": {"$in": art_variants}
        }
        cursor = db.legal_knowledge_base.find(query).sort("chunk_index", 1)
        docs = list(cursor)
        if docs:
            return docs

    return []

def find_pdf_by_number_pair(requested_name: str) -> Optional[str]:
    clean_requested = os.path.basename(requested_name).strip()

    current_file = os.path.abspath(__file__)
    endpoints_dir = os.path.dirname(current_file)
    api_dir = os.path.dirname(endpoints_dir)
    app_dir = os.path.dirname(api_dir)
    backend_dir = os.path.dirname(app_dir)
    project_root = os.path.dirname(backend_dir)

    search_dirs = [
        os.path.join(project_root, "data", "laws", "ks"),
        os.path.join(project_root, "data", "laws"),
        os.path.join(backend_dir, "data", "laws", "ks"),
        os.path.join(backend_dir, "data", "laws"),
        "data/laws/ks",
        "data/laws"
    ]

    digits = re.findall(r'\b\d+\b', clean_requested)

    for search_dir in search_dirs:
        if not os.path.exists(search_dir):
            continue

        for root, _, files in os.walk(search_dir):
            for f in files:
                if not f.lower().endswith('.pdf'):
                    continue

                if f.lower() == clean_requested.lower():
                    return os.path.join(root, f)

                if len(digits) >= 2:
                    primary_nums = [d for d in digits if len(d) >= 2 or d != '0']
                    if primary_nums and all(num in f for num in primary_nums):
                        return os.path.join(root, f)

                if 'kushtetuta' in clean_requested.lower() and 'kushtetuta' in f.lower():
                    return os.path.join(root, f)

    return None

RIGID_AUDITOR_PROMPT = """
ROLI: Ti je 'Krye-Auditori Forenzik' i certifikuar për juridiksionin e Kosovës.
DETYRA: Përgjigju pyetjeve të përdoruesit BAZUAR VETËM NË KONTEKSTIN E DHËNË.

1. **MOS SHPIK ASNJË LIGJ, NEN, APO DATË.**
2. **PËR ÇDO DEKLARATË LIGJORE, CITO BURIMIN E SAKTË.** Formati: "[Burimi: {emri_i_ligjit}, Neni X]"
3. **NUMRAT DHE DATAT DUHET TË EKZISTOJNË NË KONTEKST.**
4. **NËSE NUK JE I SIGURTË, THUAJ "NUK DI".**
5. **DELEGIMI I MATEMATIKËS:** Llogaritja kërkon përpunim nga motori tatimor.

STILI: Shqip standard, i qartë, me pika dhe lista për lehtësi.
"""

@router.get("/pdf/{filename}")
async def get_law_pdf(filename: str):
    clean_name = os.path.basename(filename)

    try:
        s3 = storage_service.get_s3_client()
        bucket = storage_service.B2_BUCKET_NAME
        digits = re.findall(r'\b\d+\b', clean_name)

        b2_response = s3.list_objects_v2(Bucket=bucket, Prefix="laws/")
        b2_items = b2_response.get('Contents', [])

        for obj in b2_items:
            key = obj.get('Key', '')
            b2_filename = os.path.basename(key)

            is_exact = b2_filename.lower() == clean_name.lower()
            primary_nums = [d for d in digits if len(d) >= 2 or d != '0']
            is_number_match = len(primary_nums) >= 2 and all(num in b2_filename for num in primary_nums)

            if is_exact or is_number_match:
                presigned_url = storage_service.generate_presigned_url(key)
                if presigned_url:
                    return RedirectResponse(url=presigned_url)
    except Exception as e:
        logger.warning(f"B2 cloud PDF search skipped: {e}")

    found_file = find_pdf_by_number_pair(clean_name)
    if found_file:
        return FileResponse(found_file, media_type="application/pdf", filename=os.path.basename(found_file))

    raise HTTPException(
        status_code=404, 
        detail=f"Dokumenti PDF '{clean_name}' nuk u gjet në server."
    )

@router.post("/sync-to-b2")
async def sync_laws_to_b2(current_user = Depends(get_current_user)):
    try:
        s3 = storage_service.get_s3_client()
        bucket = storage_service.B2_BUCKET_NAME

        existing_b2_files = set()
        try:
            b2_res = s3.list_objects_v2(Bucket=bucket, Prefix="laws/")
            for obj in b2_res.get('Contents', []):
                k = obj.get('Key', '')
                f_name = os.path.basename(k)
                if f_name:
                    existing_b2_files.add(f_name)
                    existing_b2_files.add(k)
        except Exception as err:
            logger.warning(f"Could not list existing B2 files: {err}")

        current_file = os.path.abspath(__file__)
        endpoints_dir = os.path.dirname(current_file)
        api_dir = os.path.dirname(endpoints_dir)
        app_dir = os.path.dirname(api_dir)
        backend_dir = os.path.dirname(app_dir)
        project_root = os.path.dirname(backend_dir)

        search_dirs = [
            os.path.join(project_root, "data", "laws"),
            os.path.join(backend_dir, "data", "laws"),
            "data/laws"
        ]

        uploaded = []
        skipped = []

        for s_dir in search_dirs:
            if not os.path.exists(s_dir):
                continue
            for root, _, files in os.walk(s_dir):
                rel_path = os.path.relpath(root, s_dir)
                subfolder = '' if rel_path == '.' else rel_path.replace('\\', '/')

                for f in files:
                    if f.lower().endswith('.pdf'):
                        b2_key = f"laws/{subfolder}/{f}".replace('//', '/') if subfolder else f"laws/{f}"

                        if f in existing_b2_files or b2_key in existing_b2_files:
                            skipped.append(f)
                            continue

                        local_path = os.path.join(root, f)
                        try:
                            s3.upload_file(
                                local_path, 
                                bucket, 
                                b2_key, 
                                ExtraArgs={'ContentType': 'application/pdf'}
                            )
                            uploaded.append(f)
                            existing_b2_files.add(f)
                            existing_b2_files.add(b2_key)
                        except Exception as e:
                            logger.error(f"[B2 Cloud Sync Error] {f}: {e}")

        return {
            "status": "SUCCESS", 
            "message": f"Sinkronizimi u krye. U ngarkuan {len(uploaded)} skedarë të rinj, u anashkaluan {len(skipped)} ekzistues.",
            "uploaded_files": uploaded,
            "skipped_files": skipped
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dështoi sinkronizimi në B2: {str(e)}")

@router.post("/explain")
async def explain_law_article(request: LawExplainRequest, current_user = Depends(get_current_user)):
    system_prompt = (
        "ROLI: Ti je partneri kryesor (Senior Legal Partner) në zyrën më prestigjioze ligjore në Kosovë.\n\n"
        "DUHET TË STRUKTUROSH PËRGJIGJEN SAKTËSISHT NË DY SEKSIONE TË NDARA ME MARKERIN [NDARJA]:\n\n"
        "NIVELI 1: OPINIONI PROFESIONAL (Për Juristët)\n"
        "Analizë e thellë doktrinare, precedentet dhe interpretimi i nenit.\n\n"
        "[NDARJA]\n\n"
        "NIVELI 2: KËSHILLIM PËR QYTETARIN\n"
        "Shpjegim jashtëzakonisht i thjeshtë me fjalë të përditshme se çfarë do të thotë ky nen për jetën e tij."
    )
    try:
        generator = llm_service.stream_text_async(sys_p=system_prompt, user_p=request.prompt, temp=0.3)
        return StreamingResponse(generator, media_type="text/plain")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Synthesis failed: {str(e)}")

@router.post("/audit-chat")
async def audit_chat(request: AuditChatRequest, current_user = Depends(get_current_user)):
    try:
        from app.core.db import get_db_instance
        db = get_db_instance()
        
        documents = find_law_documents(db, request.law_title, request.article_number)
        
        if not documents:
            raise HTTPException(status_code=404, detail=f"Article not found: {request.law_title}, Neni {request.article_number}")
        
        full_article_text = "\n\n".join([doc.get("text", "") for doc in documents])
        
        context = f"=== KONTEKSTI I DOKUMENTEVE ===\nTitulli i Ligjit: {request.law_title}\nNumri i Nenit: {request.article_number}\nPërmbajtja e Nenit:\n{full_article_text}\n"
        full_user_prompt = f"{context}\n\nPyetja e përdoruesit në lidhje me këtë nen: {request.query}"
        
        generator = llm_service.stream_text_async(sys_p=RIGID_AUDITOR_PROMPT, user_p=full_user_prompt, temp=0.0)
        return StreamingResponse(generator, media_type="text/plain")
        
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=f"Audit chat failed: {str(e)}")

@router.get("/search")
async def search_laws(q: str = Query(...), limit: int = Query(50, ge=1, le=200), current_user = Depends(get_current_user)):
    try:
        results = vector_store_service.query_global_knowledge_base(q, n_results=limit)
        return results
    except Exception as e: raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/titles")
async def get_law_titles(current_user = Depends(get_current_user)):
    try:
        from app.core.db import get_db_instance
        db = get_db_instance()
        titles = db.legal_knowledge_base.distinct("law_title")
        return sorted([t for t in titles if t])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching titles: {str(e)}")

@router.get("/article")
async def get_law_article(law_title: str = Query(...), article_number: str = Query(...), current_user = Depends(get_current_user)):
    try:
        from app.core.db import get_db_instance
        db = get_db_instance()
        
        documents = find_law_documents(db, law_title, article_number)
        
        if not documents: 
            raise HTTPException(status_code=404, detail=f"Neni nuk u gjet për ligjin '{law_title}', Neni {article_number}")

        return {
            "law_title": documents[0].get("law_title", law_title),
            "article_number": documents[0].get("article_number", article_number),
            "source": documents[0].get("source", ""),
            "text": "\n\n".join([doc.get("text", "") for doc in documents])
        }
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/by-title")
async def get_law_articles(law_title: str = Query(...), current_user = Depends(get_current_user)):
    try:
        from app.core.db import get_db_instance
        db = get_db_instance()
        
        query = {"law_title": law_title}
        law_num_match = re.search(r'\b(\d{2,4}[\/\-][L\d\-]+(?:\d+)?)\b', law_title, re.I)
        if law_num_match:
            query = {"law_title": {"$regex": re.escape(law_num_match.group(1)), "$options": "i"}}
        
        cursor = db.legal_knowledge_base.find(query, {"law_title": 1, "article_number": 1, "source": 1})
        docs = list(cursor)
        
        if not docs: 
            cursor = db.legal_knowledge_base.find({"law_title": {"$regex": f"^{re.escape(law_title)}$", "$options": "i"}}, {"law_title": 1, "article_number": 1, "source": 1})
            docs = list(cursor)

        if not docs:
            raise HTTPException(status_code=404, detail="Ligji nuk u gjet")
        
        canonical_title = docs[0].get("law_title", law_title)
        articles: Set[str] = {str(d.get("article_number")) for d in docs if d.get("article_number") is not None}
        sorted_articles = sorted(list(articles), key=_natural_sort_key)
        
        return {
            "law_title": canonical_title,
            "source": str(docs[0].get("source", "")),
            "article_count": len(sorted_articles),
            "articles": sorted_articles
        }
    except HTTPException: raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@router.get("/{chunk_id}")
async def get_law_chunk(chunk_id: str, current_user = Depends(get_current_user)):
    try:
        from app.core.db import get_db_instance
        db = get_db_instance()
        doc = db.legal_knowledge_base.find_one({"chunk_id": chunk_id})
        
        if not doc: 
            raise HTTPException(status_code=404, detail="Law chunk not found")

        return {
            "law_title": str(doc.get("law_title", "Ligji i panjohur")),
            "article_number": str(doc.get("article_number", "")),
            "source": str(doc.get("source", "")),
            "text": doc.get("text", "")
        }
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")