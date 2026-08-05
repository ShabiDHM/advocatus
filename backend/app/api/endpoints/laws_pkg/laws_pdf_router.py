# FILE: backend/app/api/endpoints/laws_pkg/laws_pdf_router.py
# PHOENIX PROTOCOL - LAWS PDF ROUTER V53.0 (DIRECT FASTAPI STREAMING - ZERO CORS ERROR)

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
import os
import re
import logging

from app.services import storage_service
from app.api.endpoints.laws_pkg.laws_search_service import find_pdf_by_number_pair

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/pdf/{filename}")
async def get_law_pdf(filename: str):
    raw_name = os.path.basename(filename).strip()
    
    # 1. Normalize name and ensure .pdf extension
    if not raw_name.lower().endswith('.pdf'):
        clean_name_pdf = f"{raw_name}.pdf"
    else:
        clean_name_pdf = raw_name

    target_keywords = [w.lower() for w in re.findall(r'\w+', raw_name) if len(w) >= 2]

    # 2. Query DB to resolve exact source file name if raw_name is a title
    try:
        from app.core.db import get_db_instance
        db = get_db_instance()
        doc = db.legal_knowledge_base.find_one({
            "$or": [
                {"law_title": {"$regex": re.escape(raw_name), "$options": "i"}},
                {"source": {"$regex": re.escape(raw_name), "$options": "i"}}
            ]
        })
        if doc and doc.get("source"):
            exact_source = doc.get("source")
            if exact_source.lower().endswith('.pdf'):
                clean_name_pdf = exact_source
    except Exception as db_err:
        logger.warning(f"DB source resolution skipped: {db_err}")

    # 3. Direct B2 Cloud Storage Stream (No CORS Redirect)
    try:
        candidate_keys = [
            clean_name_pdf,
            f"academic/{clean_name_pdf}",
            f"laws/{clean_name_pdf}",
            f"case_law/{clean_name_pdf}",
            clean_name_pdf.replace(" ", "_"),
            f"academic/{clean_name_pdf.replace(' ', '_')}"
        ]
        
        for key in candidate_keys:
            stream = storage_service.get_file_stream(key)
            if stream:
                return StreamingResponse(
                    stream,
                    media_type="application/pdf",
                    headers={
                        "Content-Disposition": f'inline; filename="{clean_name_pdf}"',
                        "Cache-Control": "no-cache"
                    }
                )

        # B2 Bucket Keyword Search Fallback
        s3 = storage_service.get_s3_client()
        bucket = storage_service.B2_BUCKET_NAME
        for prefix in ["academic/", "laws/", "case_law/", ""]:
            b2_response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
            for obj in b2_response.get('Contents', []):
                key = obj.get('Key', '')
                b2_file_lower = os.path.basename(key).lower()
                
                if target_keywords and all(kw in b2_file_lower for kw in target_keywords if kw not in ["web", "pdf"]):
                    stream = storage_service.get_file_stream(key)
                    if stream:
                        return StreamingResponse(
                            stream,
                            media_type="application/pdf",
                            headers={
                                "Content-Disposition": f'inline; filename="{os.path.basename(key)}"',
                                "Cache-Control": "no-cache"
                            }
                        )
    except Exception as e:
        logger.warning(f"B2 cloud search skipped: {e}")

    # 4. Local Filesystem Search Fallback
    found = find_pdf_by_number_pair(clean_name_pdf) or find_pdf_by_number_pair(raw_name)
    if found:
        return FileResponse(
            found, 
            media_type="application/pdf", 
            filename=os.path.basename(found),
            headers={"Content-Disposition": f'inline; filename="{os.path.basename(found)}"'}
        )
        
    raise HTTPException(status_code=404, detail=f"Dokumenti PDF '{raw_name}' nuk u gjet.")