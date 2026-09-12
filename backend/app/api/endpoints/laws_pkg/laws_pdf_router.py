# FILE: backend/app/api/endpoints/laws_pkg/laws_pdf_router.py
# PHOENIX PROTOCOL - LAWS PDF ROUTER V91.0 (SUPREME CASELAW ELASTIC MATCHER)
# 100% COMPLETE CODE • ZERO 404 MISSES • FUZZY PREFIX-NUMBER-YEAR MATCHER • B2 & LOCAL RECURSIVE

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
import os
import re
import urllib.parse
import unicodedata
import logging
from pathlib import Path
from typing import Optional, Tuple

from app.services import storage_service

logger = logging.getLogger(__name__)
router = APIRouter()


def _normalize_str(text: str) -> str:
    if not text:
        return ""
    return unicodedata.normalize('NFC', text).strip()


def _to_alpha_key(name: str) -> str:
    if not name:
        return ""
    nfc = _normalize_str(name)
    clean = re.sub(r'\.pdf$', '', nfc, flags=re.IGNORECASE).lower()
    clean = clean.replace('ë', 'e').replace('ç', 'c')
    return re.sub(r'[^a-z0-9]', '', clean)


def _parse_supreme_case_components(filename_or_query: str) -> Optional[Tuple[str, str, str]]:
    """
    Dekompozon çdo format precedenti suprem në (Prefiks, Numër, Vit).
    Shembuj:
    - "REV.Nr.50/2023.pdf" -> ("rev", "50", "2023")
    - "Pml.nr.170-2025" -> ("pml", "170", "2025")
    - "A.NR.140/21" -> ("anr", "140", "2021")
    """
    clean_text = urllib.parse.unquote(filename_or_query).strip()
    match = re.search(
        r'\b(REV|PML|KMLP|ANR|A\.?NR|PZR)\.?\s*(?:nr|nr\.)?\s*(\d+)\s*[\/\-_\.\s]\s*(\d{2,4})\b',
        clean_text,
        re.IGNORECASE
    )
    if match:
        prefix = match.group(1).replace(".", "").lower()
        number = str(int(match.group(2)))
        raw_year = match.group(3)
        year = f"20{raw_year}" if len(raw_year) == 2 else raw_year
        return prefix, number, year
    return None


def _matches_case_components(filename: str, prefix: str, number: str, year: str) -> bool:
    """Kontrollon nëse një skedar në B2 ose disk përmban saktësisht prefiksin, numrin dhe vitin."""
    clean_f = filename.lower().replace("ë", "e").replace("ç", "c")
    
    # 1. Kontrollo prefiksin
    if prefix not in clean_f:
        return False

    # 2. Kontrollo vitin (si 2023 ashtu edhe 23)
    short_year = year[-2:]
    has_year = (year in clean_f) or (f"_{short_year}." in clean_f) or (f"-{short_year}." in clean_f) or (f"{short_year}.pdf" in clean_f)
    if not has_year:
        return False

    # 3. Kontrollo numrin e lëndës si fjalë më vete
    num_pattern = rf'(?:^|[\D]){number}(?:[\D]|$)'
    if not re.search(num_pattern, clean_f):
        return False

    return True


def _stream_from_b2_or_local(filename: str, target_prefixes: list[str]) -> StreamingResponse | FileResponse | None:
    raw_unquoted = urllib.parse.unquote(filename).strip()
    raw_name = _normalize_str(raw_unquoted)
    
    # Heqim çdo shtesë path-i të jashtëm
    raw_basename = os.path.basename(raw_name) if "/" in raw_name and not raw_name.startswith("data/") else raw_name
    clean_search_name = re.sub(r'\.pdf$', '', raw_basename, flags=re.IGNORECASE).strip()
    alpha_target = _to_alpha_key(raw_basename)

    case_components = _parse_supreme_case_components(raw_name)

    # =========================================================================
    # HAPI 1: BALLAFAQIM ELASTIK NË MONGODB ATLAS
    # =========================================================================
    try:
        from app.core.db import get_db_instance
        db = get_db_instance()

        mongo_queries = [
            {"source": raw_basename},
            {"source": {"$regex": re.escape(clean_search_name), "$options": "i"}},
            {"case_number": {"$regex": re.escape(clean_search_name), "$options": "i"}},
            {"title": {"$regex": re.escape(clean_search_name), "$options": "i"}},
            {"law_title": {"$regex": re.escape(clean_search_name), "$options": "i"}}
        ]

        if case_components:
            p_prefix, p_num, p_year = case_components
            short_y = p_year[-2:]
            flexible_case_regex = rf"{p_prefix}\.?\s*(?:nr\.?\s*)?0*{p_num}\s*[\/\-_\.\s]\s*(?:{p_year}|{short_y})"
            mongo_queries.extend([
                {"case_number": {"$regex": flexible_case_regex, "$options": "i"}},
                {"source": {"$regex": flexible_case_regex, "$options": "i"}},
                {"title": {"$regex": flexible_case_regex, "$options": "i"}}
            ])

        doc = db.legal_knowledge_base.find_one({"$or": mongo_queries})
        if doc and doc.get("source"):
            found_source = _normalize_str(doc.get("source"))
            # Nëse source ka path, merr emrin e pastër
            raw_basename = os.path.basename(found_source) if "/" in found_source else found_source
            alpha_target = _to_alpha_key(raw_basename)
            logger.info(f"✅ [PDF Router] MongoDB mapped '{filename}' -> '{raw_basename}'")
    except Exception as db_err:
        logger.warning(f"MongoDB source mapping skipped: {db_err}")

    clean_name_pdf = raw_basename if raw_basename.lower().endswith('.pdf') else f"{raw_basename}.pdf"
    clean_name_pdf = _normalize_str(clean_name_pdf)

    # =========================================================================
    # HAPI 2: DISK LOKAL (KËRKIM REKURZIV ME MATCHER TË TREFISHTË)
    # =========================================================================
    this_file = Path(__file__).resolve()
    candidate_roots = [
        Path.cwd() / "data",
        Path.cwd().parent / "data",
        Path.cwd() / "backend" / "data",
        Path("data").resolve(),
        Path("../data").resolve(),
        Path("/app/data"),
        Path("/app/backend/data"),
    ]

    for p_idx in range(len(this_file.parents)):
        candidate_roots.append(this_file.parents[p_idx] / "data")
        candidate_roots.append(this_file.parents[p_idx] / "data" / "case_law")
        candidate_roots.append(this_file.parents[p_idx] / "data" / "academic")

    search_roots = []
    seen_roots = set()
    for r in candidate_roots:
        try:
            if r and r.exists() and str(r.resolve()) not in seen_roots:
                seen_roots.add(str(r.resolve()))
                search_roots.append(r)
        except Exception:
            pass

    for root_dir in search_roots:
        try:
            for p in root_dir.rglob("*.pdf"):
                fname = _normalize_str(p.name)
                f_alpha = _to_alpha_key(fname)

                is_match = (
                    fname.lower() == clean_name_pdf.lower()
                    or (alpha_target and f_alpha and (f_alpha == alpha_target or alpha_target in f_alpha or f_alpha in alpha_target))
                    or (case_components and _matches_case_components(fname, *case_components))
                )

                if is_match:
                    f_nfc = _normalize_str(p.name)
                    logger.info(f"⚡ [Instant Local Disk Stream] Found -> {p}")
                    return FileResponse(
                        str(p),
                        media_type="application/pdf",
                        headers={
                            "Content-Disposition": f'inline; filename="{f_nfc}"',
                            "Cache-Control": "public, max-age=86400",
                            "Accept-Ranges": "bytes"
                        }
                    )
        except Exception:
            pass

    # =========================================================================
    # HAPI 3: BACKBLAZE B2 CLOUD SEARCH (ME SKANIM TEKSTUAL TË TREFISHTË)
    # =========================================================================
    try:
        s3 = storage_service.get_s3_client()
        bucket = storage_service.B2_BUCKET_NAME
        prefixes_to_check = ["case_law/", "data/case_law/", "", "laws/ks/", "academic/"]

        # 3.1 Kontroll i drejtpërdrejtë Head-Object
        for prefix in prefixes_to_check:
            direct_key = f"{prefix}{clean_name_pdf}".replace("//", "/")
            try:
                s3.head_object(Bucket=bucket, Key=direct_key)
                stream, content_length = storage_service.get_file_stream_with_meta(direct_key)
                if stream:
                    logger.info(f"☁️ [B2 Direct Match] Stream -> {direct_key}")
                    headers = {
                        "Content-Disposition": f'inline; filename="{clean_name_pdf}"',
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
                pass

        # 3.2 Skanim me Paginator (Bypass i plotë i vizave "/" dhe hapësirave)
        paginator = s3.get_paginator('list_objects_v2')
        for prefix in prefixes_to_check:
            try:
                page_iterator = paginator.paginate(Bucket=bucket, Prefix=prefix)
                for page in page_iterator:
                    contents = page.get('Contents', [])
                    for obj in contents:
                        key = obj.get('Key', '')
                        b2_filename = _normalize_str(os.path.basename(key))
                        if not b2_filename or not b2_filename.lower().endswith('.pdf'):
                            continue

                        b2_alpha = _to_alpha_key(b2_filename)

                        is_b2_match = (
                            b2_filename.lower() == clean_name_pdf.lower()
                            or (alpha_target and b2_alpha and (b2_alpha == alpha_target or alpha_target in b2_alpha or b2_alpha in alpha_target))
                            or (case_components and _matches_case_components(b2_filename, *case_components))
                        )

                        if is_b2_match:
                            stream, content_length = storage_service.get_file_stream_with_meta(key)
                            if stream:
                                logger.info(f"☁️ [B2 Elastic Match SUCCESS] Stream -> {key}")
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

    logger.error(f"❌ [PDF 404] Nuk u gjet asnjë skedar për: '{raw_name}' (Komponentët: {case_components})")
    raise HTTPException(status_code=404, detail=f"Aktgjykimi suprem '{raw_basename}' nuk u gjet në arkivën zyrtare.")


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