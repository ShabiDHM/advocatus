# FILE: backend/app/api/endpoints/laws_pkg/laws_pdf_router.py
# PHOENIX PROTOCOL - LAWS PDF ROUTER V70.0 (CLEAN ALPHANUMERIC MATCHER & ZERO 404s)

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
import os
import re
import urllib.parse
import unicodedata
import logging

from app.services import storage_service

logger = logging.getLogger(__name__)
router = APIRouter()

CURRENT_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_FILE_DIR)))
WORKSPACE_ROOT = os.path.dirname(BACKEND_DIR)


def _to_alpha_key(name: str) -> str:
    """Strips all punctuation, underscores, hyphens, and whitespace for bulletproof matching."""
    if not name:
        return ""
    nfc = unicodedata.normalize('NFC', name)
    clean = re.sub(r'\.pdf$', '', nfc, flags=re.IGNORECASE).lower()
    return re.sub(r'[^a-z0-9]', '', clean)


def _find_file_recursively(search_roots: list[str], target_filename: str, alpha_target: str) -> str | None:
    """Recursively scans all directories and subdirectories on local disk."""
    clean_target_pdf = target_filename.lower() if target_filename.lower().endswith('.pdf') else f"{target_filename.lower()}.pdf"

    for root_dir in search_roots:
        if not os.path.exists(root_dir):
            continue

        for root, _, files in os.walk(root_dir):
            # Pass 1: Exact filename match (case-insensitive)
            for f in files:
                if not f.lower().endswith('.pdf'):
                    continue
                if f.lower() == clean_target_pdf:
                    return os.path.join(root, f)

            # Pass 2: Alphanumeric Key Match (ignores double underscores, spaces, hyphens)
            for f in files:
                if not f.lower().endswith('.pdf'):
                    continue
                f_alpha = _to_alpha_key(f)
                if alpha_target and f_alpha and (f_alpha == alpha_target or alpha_target in f_alpha or f_alpha in alpha_target):
                    return os.path.join(root, f)

    return None


def _stream_from_b2_or_local(filename: str, target_prefixes: list[str]) -> StreamingResponse | FileResponse | None:
    raw_unquoted = urllib.parse.unquote(filename).strip()
    raw_name = unicodedata.normalize('NFC', raw_unquoted)
    raw_basename = os.path.basename(raw_name) if "/" in raw_name else raw_name
    if not raw_basename:
        return None

    clean_search_name = re.sub(r'\.pdf$', '', raw_basename, flags=re.IGNORECASE).strip()

    # --- STEP 1: DYNAMIC MONGODB RESOLUTION ---
    try:
        from app.core.db import get_db_instance
        db = get_db_instance()

        alpha_query = _to_alpha_key(clean_search_name)

        doc = db.legal_knowledge_base.find_one({
            "$or": [
                {"source": raw_basename},
                {"source": {"$regex": re.escape(clean_search_name), "$options": "i"}},
                {"law_title": {"$regex": re.escape(clean_search_name), "$options": "i"}}
            ]
        })
        if doc and doc.get("source"):
            raw_basename = doc.get("source")
            logger.info(f"MongoDB resolved '{filename}' -> source '{raw_basename}'")
    except Exception as db_err:
        logger.warning(f"MongoDB source mapping skipped: {db_err}")

    # --- STEP 2: PREPARE SEARCH TARGETS ---
    clean_name_pdf = raw_basename if raw_basename.lower().endswith('.pdf') else f"{raw_basename}.pdf"
    alpha_target = _to_alpha_key(raw_basename)

    # --- STEP 3: RECURSIVE LOCAL DISK SCAN ---
    search_roots = [
        os.path.join(WORKSPACE_ROOT, "data", "laws"),
        os.path.join(WORKSPACE_ROOT, "data", "academic"),
        os.path.join(WORKSPACE_ROOT, "data", "case_law"),
        os.path.join(WORKSPACE_ROOT, "data"),
        os.path.join(BACKEND_DIR, "data", "laws"),
        os.path.join(BACKEND_DIR, "data", "academic"),
        os.path.join(BACKEND_DIR, "data", "case_law"),
        os.path.join(BACKEND_DIR, "data"),
        "data/laws", "data/academic", "data/case_law", "data"
    ]

    local_file_path = _find_file_recursively(search_roots, clean_name_pdf, alpha_target)
    if local_file_path and os.path.exists(local_file_path):
        f_nfc = unicodedata.normalize('NFC', os.path.basename(local_file_path))
        logger.info(f"⚡ [Instant Local Disk Stream] Found -> {local_file_path}")
        return FileResponse(
            local_file_path,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="{f_nfc}"',
                "Cache-Control": "public, max-age=86400",
                "Accept-Ranges": "bytes"
            }
        )

    # --- STEP 4: BACKBLAZE B2 CLOUD STREAMING ---
    try:
        s3 = storage_service.get_s3_client()
        bucket = storage_service.B2_BUCKET_NAME

        for prefix in target_prefixes:
            try:
                b2_response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
                contents = b2_response.get('Contents', [])
                for obj in contents:
                    key = obj.get('Key', '')
                    b2_filename = os.path.basename(key)
                    if not b2_filename or not b2_filename.lower().endswith('.pdf'):
                        continue

                    b2_alpha = _to_alpha_key(b2_filename)
                    if alpha_target and b2_alpha and (b2_alpha == alpha_target or alpha_target in b2_alpha or b2_alpha in alpha_target):
                        stream, content_length = storage_service.get_file_stream_with_meta(key)
                        if stream:
                            logger.info(f"☁️ Cloud B2 stream -> {key}")
                            headers = {
                                "Content-Disposition": f'inline; filename="{b2_filename}"',
                                "Cache-Control": "public, max-age=86400",
                                "Accept-Ranges": "bytes"
                            }
                            if content_length > 0:
                                headers["Content-Length"] = str(content_length)

                            return StreamingResponse(
                                stream,
                                media_type="application/pdf",
                                headers=headers
                            )
            except Exception:
                continue
    except Exception as e:
        logger.warning(f"B2 cloud search exception: {e}")

    raise HTTPException(status_code=404, detail=f"Dokumenti PDF '{raw_basename}' nuk u gjet në server apo cloud.")


@router.get("/pdf/{filename:path}")
async def get_law_pdf(filename: str):
    res = _stream_from_b2_or_local(filename, ["laws/ks/", "academic/", "case_law/", "laws/", ""])
    if res:
        return res
    raise HTTPException(status_code=404, detail=f"Dokumenti PDF '{filename}' nuk u gjet në server apo cloud.")


@router.get("/academia/pdf/{filename:path}")
async def get_academia_pdf(filename: str):
    res = _stream_from_b2_or_local(filename, ["academic/", "academic_manuals/", ""])
    if res:
        return res
    raise HTTPException(status_code=404, detail=f"Materiali akademik PDF '{filename}' nuk u gjet në server apo cloud.")


@router.get("/caselaw/pdf/{filename:path}")
async def get_caselaw_pdf(filename: str):
    res = _stream_from_b2_or_local(filename, ["case_law/", "jurisprudence/", "decisions/", ""])
    if res:
        return res
    raise HTTPException(status_code=404, detail=f"Aktgjykimi PDF '{filename}' nuk u gjet në server apo cloud.")