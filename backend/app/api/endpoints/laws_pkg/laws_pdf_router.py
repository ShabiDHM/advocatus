# FILE: backend/app/api/endpoints/laws_pkg/laws_pdf_router.py
# PHOENIX PROTOCOL - LAWS PDF ROUTER V80.0 (ALBANIAN TRANSLITERATION MATCH & ZERO 404 B2 RETRIEVER)

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


def _normalize_str(text: str) -> str:
    if not text:
        return ""
    return unicodedata.normalize('NFC', text).strip()


def _to_alpha_key(name: str) -> str:
    """
    Kthen emrin në çelës alfanumerik duke konvertuar shkronjat shqipe:
    'ë' -> 'e', 'ç' -> 'c' për të garantuar përputhje 100% me B2 dhe diskun.
    """
    if not name:
        return ""
    nfc = _normalize_str(name)
    clean = re.sub(r'\.pdf$', '', nfc, flags=re.IGNORECASE).lower()
    # Transliterim shqip
    clean = clean.replace('ë', 'e').replace('ç', 'c')
    return re.sub(r'[^a-z0-9]', '', clean)


def _extract_law_number_code(name: str) -> str:
    if not name:
        return ""
    match = re.search(r'(\d{2})[-_\s\/]?L[-_\s\/]?(\d{2,4})', name, re.IGNORECASE)
    if match:
        return f"{match.group(1)}l{match.group(2)}".lower()
    return ""


def _find_file_recursively(search_roots: list[Path], target_filename: str, alpha_target: str, law_code: str) -> Path | None:
    clean_target_pdf = target_filename.lower() if target_filename.lower().endswith('.pdf') else f"{target_filename.lower()}.pdf"
    clean_target_pdf = _normalize_str(clean_target_pdf)

    for root_dir in search_roots:
        if not root_dir or not root_dir.exists():
            continue

        try:
            for p in root_dir.rglob("*.pdf"):
                fname = _normalize_str(p.name)
                f_alpha = _to_alpha_key(fname)
                f_code = _extract_law_number_code(fname)

                if (
                    fname.lower() == clean_target_pdf.lower()
                    or (alpha_target and f_alpha and (f_alpha == alpha_target or alpha_target in f_alpha or f_alpha in alpha_target))
                    or (law_code and f_code and f_code == law_code)
                ):
                    return p
        except Exception as scan_err:
            logger.warning(f"Disk scan warning at {root_dir}: {scan_err}")

    return None


def _stream_from_b2_or_local(filename: str, target_prefixes: list[str]) -> StreamingResponse | FileResponse | None:
    raw_unquoted = urllib.parse.unquote(filename).strip()
    raw_name = _normalize_str(raw_unquoted)
    
    # Ruaj numrin e lëndës me slash (p.sh. REV.Nr.114/22.pdf)
    if "/" in raw_name and not any(raw_name.lower().startswith(p) for p in ["laws/", "academic/", "case_law/"]):
        raw_basename = raw_name
    else:
        raw_basename = os.path.basename(raw_name) if "/" in raw_name else raw_name

    clean_search_name = re.sub(r'\.pdf$', '', raw_basename, flags=re.IGNORECASE).strip()
    law_code = _extract_law_number_code(raw_basename)
    alpha_target = _to_alpha_key(raw_basename)

    # --- STEP 1: MONGODB REZOLVIMI I NUMRIT TË LËNDËS ---
    try:
        from app.core.db import get_db_instance
        db = get_db_instance()

        clean_regex = re.escape(clean_search_name)
        doc = db.legal_knowledge_base.find_one({
            "$or": [
                {"source": raw_basename},
                {"source": {"$regex": clean_regex, "$options": "i"}},
                {"case_number": {"$regex": clean_regex, "$options": "i"}},
                {"title": {"$regex": clean_regex, "$options": "i"}},
                {"law_title": {"$regex": clean_regex, "$options": "i"}}
            ]
        })
        if doc and doc.get("source"):
            raw_basename = _normalize_str(doc.get("source"))
            alpha_target = _to_alpha_key(raw_basename)
            logger.info(f"✅ [PDF Router] MongoDB mapped '{filename}' -> '{raw_basename}'")
    except Exception as db_err:
        logger.warning(f"MongoDB source mapping skipped: {db_err}")

    clean_name_pdf = raw_basename if raw_basename.lower().endswith('.pdf') else f"{raw_basename}.pdf"

    # --- STEP 2: KËRKIMI NË DISKUN LOKAL ---
    this_file = Path(__file__).resolve()
    search_roots = [
        Path("/app/data"),
        Path("/app/backend/data"),
        this_file.parents[4] / "data",
        this_file.parents[3] / "data",
        Path.cwd() / "data",
        Path.cwd() / "backend" / "data",
        Path("data").resolve(),
    ]

    local_file = _find_file_recursively(search_roots, clean_name_pdf, alpha_target, law_code)
    if local_file and local_file.exists():
        f_nfc = _normalize_str(local_file.name)
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

    # --- STEP 3: BACKBLAZE B2 CLOUD ME TRANSLITERIM 'ë' -> 'e' ---
    try:
        s3 = storage_service.get_s3_client()
        bucket = storage_service.B2_BUCKET_NAME

        all_prefixes = target_prefixes + ["case_law/", "data/case_law/", "laws/ks/", "academic/", ""]
        unique_prefixes = list(dict.fromkeys(all_prefixes))

        for prefix in unique_prefixes:
            try:
                b2_response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
                contents = b2_response.get('Contents', [])
                for obj in contents:
                    key = obj.get('Key', '')
                    b2_filename = _normalize_str(os.path.basename(key))
                    if not b2_filename or not b2_filename.lower().endswith('.pdf'):
                        continue

                    b2_alpha = _to_alpha_key(b2_filename)
                    b2_code = _extract_law_number_code(b2_filename)

                    # PHOENIX MATCH: Përputhje alfanumerike pa u penguar nga 'ë' apo 'e'
                    if (
                        b2_filename.lower() == clean_name_pdf.lower()
                        or (alpha_target and b2_alpha and (b2_alpha == alpha_target or alpha_target in b2_alpha or b2_alpha in alpha_target))
                        or (law_code and b2_code == law_code)
                    ):
                        stream, content_length = storage_service.get_file_stream_with_meta(key)
                        if stream:
                            logger.info(f"☁️ [B2 Match Success] Stream -> {key}")
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
    res = _stream_from_b2_or_local(filename, ["case_law/", "data/case_law/", "jurisprudence/", "decisions/", ""])
    if res:
        return res
    raise HTTPException(status_code=404, detail=f"Aktgjykimi PDF '{filename}' nuk u gjet në server apo cloud.")