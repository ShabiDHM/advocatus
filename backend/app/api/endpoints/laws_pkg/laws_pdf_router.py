# FILE: backend/app/api/endpoints/laws_pkg/laws_pdf_router.py
# PHOENIX PROTOCOL - LAWS PDF ROUTER V72.0 (ABSOLUTE PATHLIB RECURSIVE DISK STREAMER)

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
import os
import re
import urllib.parse
import unicodedata
import logging
from pathlib import Path

from app.services import storage_service

logger = logging.getLogger(__name__)
router = APIRouter()


def _to_alpha_key(name: str) -> str:
    if not name:
        return ""
    nfc = unicodedata.normalize('NFC', name)
    clean = re.sub(r'\.pdf$', '', nfc, flags=re.IGNORECASE).lower()
    return re.sub(r'[^a-z0-9]', '', clean)


def _extract_law_number_code(name: str) -> str:
    """Extracts standardized law codes like '03l052', '04l077', '08l032'."""
    if not name:
        return ""
    match = re.search(r'(\d{2})[-_\s\/]?L[-_\s\/]?(\d{2,4})', name, re.IGNORECASE)
    if match:
        return f"{match.group(1)}l{match.group(2)}".lower()
    return ""


def _find_file_recursively(search_roots: list[Path], target_filename: str, alpha_target: str, law_code: str) -> Path | None:
    """Recursively scans all directories on local disk with 3-tier fallback."""
    clean_target_pdf = target_filename.lower() if target_filename.lower().endswith('.pdf') else f"{target_filename.lower()}.pdf"

    for root_dir in search_roots:
        if not root_dir.exists():
            continue

        for p in root_dir.rglob("*.pdf"):
            fname = p.name
            
            # Tier 1: Exact Filename Match
            if fname.lower() == clean_target_pdf:
                return p

            # Tier 2: Official Law Number Code Match (e.g. 03l052)
            if law_code:
                f_code = _extract_law_number_code(fname)
                if f_code and f_code == law_code:
                    return p

            # Tier 3: Alphanumeric Key Match
            if alpha_target:
                f_alpha = _to_alpha_key(fname)
                if f_alpha and (f_alpha == alpha_target or alpha_target in f_alpha or f_alpha in alpha_target):
                    return p

    return None


def _stream_from_b2_or_local(filename: str, target_prefixes: list[str]) -> StreamingResponse | FileResponse | None:
    raw_unquoted = urllib.parse.unquote(filename).strip()
    raw_name = unicodedata.normalize('NFC', raw_unquoted)
    raw_basename = os.path.basename(raw_name) if "/" in raw_name else raw_name
    if not raw_basename:
        return None

    clean_search_name = re.sub(r'\.pdf$', '', raw_basename, flags=re.IGNORECASE).strip()
    law_code = _extract_law_number_code(raw_basename)
    alpha_target = _to_alpha_key(raw_basename)

    # --- STEP 1: DYNAMIC MONGODB RESOLUTION ---
    try:
        from app.core.db import get_db_instance
        db = get_db_instance()

        query_conditions: list[dict] = [
            {"source": raw_basename},
            {"source": {"$regex": re.escape(clean_search_name), "$options": "i"}},
            {"law_title": {"$regex": re.escape(clean_search_name), "$options": "i"}}
        ]
        if law_code:
            query_conditions.append({"source": {"$regex": law_code.replace("l", ".*L.*"), "$options": "i"}})
            query_conditions.append({"law_title": {"$regex": law_code.replace("l", ".*L.*"), "$options": "i"}})

        doc = db.legal_knowledge_base.find_one({"$or": query_conditions})
        if doc and doc.get("source"):
            raw_basename = doc.get("source")
            alpha_target = _to_alpha_key(raw_basename)
            if not law_code:
                law_code = _extract_law_number_code(raw_basename)
            logger.info(f"MongoDB resolved '{filename}' -> exact source '{raw_basename}'")
    except Exception as db_err:
        logger.warning(f"MongoDB source mapping skipped: {db_err}")

    clean_name_pdf = raw_basename if raw_basename.lower().endswith('.pdf') else f"{raw_basename}.pdf"

    # --- STEP 2: ROBUST PATHLIB ROOT RECURSIVE DISK SCAN ---
    this_file = Path(__file__).resolve()
    
    # Check all possible root data directories safely
    search_roots = [
        this_file.parents[5] / "data",              # advocatus/data
        this_file.parents[4] / "data",              # advocatus/backend/data
        Path.cwd() / "data",                        # cwd/data
        Path.cwd().parent / "data",                 # cwd/../data
        Path("data").resolve(),
        Path("../data").resolve(),
    ]

    local_file = _find_file_recursively(search_roots, clean_name_pdf, alpha_target, law_code)
    if local_file and local_file.exists():
        f_nfc = unicodedata.normalize('NFC', local_file.name)
        logger.info(f"⚡ [Instant Local Disk Stream] Found -> {local_file}")
        return FileResponse(
            str(local_file),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="{f_nfc}"',
                "Cache-Control": "public, max-age=86400",
                "Accept-Ranges": "bytes"
            }
        )

    # --- STEP 3: BACKBLAZE B2 CLOUD STREAMING ---
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

                    b2_code = _extract_law_number_code(b2_filename)
                    b2_alpha = _to_alpha_key(b2_filename)

                    if (
                        b2_filename.lower() == clean_name_pdf.lower()
                        or (law_code and b2_code == law_code)
                        or (alpha_target and b2_alpha and b2_alpha == alpha_target)
                    ):
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