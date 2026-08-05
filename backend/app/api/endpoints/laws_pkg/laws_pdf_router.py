# FILE: backend/app/api/endpoints/laws_pkg/laws_pdf_router.py
# PHOENIX PROTOCOL - LAWS PDF ROUTER V58.0 (UNIFIED NON-ALPHANUMERIC STRIPPER)

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
import os
import re
import urllib.parse
import logging

from app.services import storage_service
from app.api.endpoints.laws_pkg.laws_dictionary import _strip_alpha
from app.api.endpoints.laws_pkg.laws_search_service import find_pdf_by_number_pair

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/pdf/{filename}")
async def get_law_pdf(filename: str):
    raw_name = urllib.parse.unquote(os.path.basename(filename)).strip()
    clean_target = _strip_alpha(raw_name)
    
    clean_name_pdf = raw_name if raw_name.lower().endswith('.pdf') else f"{raw_name}.pdf"

    # 1. Query MongoDB for exact 'source' filename
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
                clean_target = _strip_alpha(exact_source)
    except Exception as db_err:
        logger.warning(f"DB source resolution skipped: {db_err}")

    # 2. Local Filesystem Search (data/laws/ks & data/academic)
    found = find_pdf_by_number_pair(clean_name_pdf) or find_pdf_by_number_pair(raw_name)
    if found and os.path.exists(found):
        return FileResponse(
            found, 
            media_type="application/pdf", 
            filename=os.path.basename(found),
            headers={"Content-Disposition": f'inline; filename="{os.path.basename(found)}"'}
        )

    # 3. Backblaze B2 Cloud Storage Search
    try:
        s3 = storage_service.get_s3_client()
        bucket = storage_service.B2_BUCKET_NAME
        
        for prefix in ["laws/ks/", "academic/", "laws/", "case_law/", ""]:
            try:
                b2_response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
                for obj in b2_response.get('Contents', []):
                    key = obj.get('Key', '')
                    b2_filename = os.path.basename(key)
                    
                    if _strip_alpha(b2_filename) == clean_target:
                        stream = storage_service.get_file_stream(key)
                        if stream:
                            return StreamingResponse(
                                stream,
                                media_type="application/pdf",
                                headers={
                                    "Content-Disposition": f'inline; filename="{b2_filename}"',
                                    "Cache-Control": "no-cache"
                                }
                            )
            except Exception:
                continue
    except Exception as e:
        logger.warning(f"B2 cloud search skipped: {e}")

    raise HTTPException(status_code=404, detail=f"Dokumenti PDF '{raw_name}' nuk u gjet ne server apo cloud.")