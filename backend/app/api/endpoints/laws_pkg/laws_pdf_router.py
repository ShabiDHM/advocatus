# FILE: backend/app/api/endpoints/laws_pkg/laws_pdf_router.py
# PHOENIX PROTOCOL - LAWS PDF ROUTER V93.2
#
# V93.2: FIX UnicodeDecodeError në Content-Disposition header.
#   - Shkaku: filename me diakritika (Ë, Ç) nuk lejohet në HTTP headers
#   - Zgjidhja: RFC 5987 encoding (`filename*=UTF-8''...`)
#   - FileResponse: përdor `filename=` param (Starlette e encode vetë)
#   - StreamingResponse: encode manual me urllib.parse.quote
#
# V93.1: DEFENSIVE WRAPPING + DIAGNOSTICS.
# V93.0: FIX R1-R13 (auditim i Bibliotekës Ligjore).

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse, StreamingResponse
import os
import re
import time
import urllib.parse
import unicodedata
import logging
from pathlib import Path
from typing import Optional, Tuple, List, Dict

from app.services import storage_service
from app.api.endpoints.dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


_DIACRITIC_MAP = {
    'ë': 'e', 'ç': 'c',
    'â': 'a', 'î': 'i', 'û': 'u',
    'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
}


def _normalize_str(text: str) -> str:
    if not text:
        return ""
    return unicodedata.normalize('NFC', text).strip()


def _to_alpha_key(name: str) -> str:
    if not name:
        return ""
    nfc = _normalize_str(name)
    clean = re.sub(r'\.pdf$', '', nfc, flags=re.IGNORECASE).lower()
    for k, v in _DIACRITIC_MAP.items():
        clean = clean.replace(k, v)
    return re.sub(r'[^a-z0-9]', '', clean)


def _safe_header_filename(filename: str) -> str:
    """
    V93.2: Kthen filename të sigurt për HTTP header (RFC 5987).
    Shembull: "KODI_Ë.pdf" → "UTF-8''KODI_%C3%8B.pdf"
    Returns: vlera e plotë për Content-Disposition.
    """
    if not filename:
        return "document.pdf"
    # Fallback ASCII (heq jo-ASCII)
    ascii_fallback = (
        unicodedata.normalize('NFKD', filename)
        .encode('ascii', 'ignore')
        .decode('ascii')
    ) or "document.pdf"
    # Versioni i encoded për klientët modernë
    encoded = urllib.parse.quote(filename, safe='')
    return f"UTF-8''{encoded}"


def _content_disposition(filename: str) -> str:
    """
    V93.2: Ndërton header Content-Disposition të sigurt (RFC 5987).
    Përdor të dyja: `filename` (ASCII fallback) + `filename*` (UTF-8).
    """
    if not filename:
        filename = "document.pdf"

    ascii_fallback = (
        unicodedata.normalize('NFKD', filename)
        .encode('ascii', 'ignore')
        .decode('ascii')
    ) or "document.pdf"
    # Heq karakteret e rrezikshme nga fallback (quotes, backslash)
    ascii_fallback = re.sub(r'["\\\r\n]', '_', ascii_fallback)

    encoded = urllib.parse.quote(filename, safe='')

    return f"inline; filename=\"{ascii_fallback}\"; filename*=UTF-8''{encoded}"


def _parse_supreme_case_components(filename_or_query: str) -> Optional[Tuple[str, str, str]]:
    if not filename_or_query:
        return None
    clean_text = urllib.parse.unquote(filename_or_query).strip()
    match = re.search(
        r'\b(REV|PML|KMLP|ANR|A\.?NR|PZR)\.?\s*(?:nr|nr\.)?\s*(\d+)\s*[\/\-_\.\s]\s*(\d{2,4})\b',
        clean_text,
        re.IGNORECASE,
    )
    if match:
        prefix = match.group(1).replace(".", "").lower()
        number = str(int(match.group(2)))
        raw_year = match.group(3)
        year = f"20{raw_year}" if len(raw_year) == 2 else raw_year
        return prefix, number, year
    return None


def _matches_case_components(filename: str, prefix: str, number: str, year: str) -> bool:
    if not filename:
        return False
    clean_f = filename.lower()
    for k, v in _DIACRITIC_MAP.items():
        clean_f = clean_f.replace(k, v)

    if prefix not in clean_f:
        return False

    short_year = year[-2:]
    year_pattern = rf'(?:^|[\D])(?:{year}|{short_year})(?:[\D]|$)'
    if not re.search(year_pattern, clean_f):
        return False

    num_pattern = rf'(?:^|[\D])0*{number}(?:[\D]|$)'
    if not re.search(num_pattern, clean_f):
        return False

    return True


def _score_filename_match(
    requested_alpha: str,
    candidate_alpha: str,
    requested_raw: str,
    candidate_raw: str,
) -> int:
    if not requested_alpha or not candidate_alpha:
        return 0

    if requested_raw.lower() == candidate_raw.lower():
        return 100
    if requested_alpha == candidate_alpha:
        return 95

    shorter = min(len(requested_alpha), len(candidate_alpha))
    longer = max(len(requested_alpha), len(candidate_alpha))
    if longer == 0:
        return 0

    if requested_alpha in candidate_alpha or candidate_alpha in requested_alpha:
        diff_ratio = (longer - shorter) / longer
        if diff_ratio <= 0.20:
            return 80
        elif diff_ratio <= 0.40:
            return 50
        else:
            return 20

    common = 0
    for a, b in zip(requested_alpha, candidate_alpha):
        if a == b:
            common += 1
        else:
            break
    if common >= 8 and common / max(shorter, 1) >= 0.80:
        return 70

    return 0


# ═══════════════════════════════════════════════════════════════════════════
# CACHE
# ═══════════════════════════════════════════════════════════════════════════

_PDF_DISK_INDEX: Dict[str, List[str]] = {}
_PDF_DISK_INDEX_BUILT = False

_B2_INDEX_CACHE: Dict[str, Tuple[float, List[str]]] = {}
_B2_CACHE_TTL = 300

_B2_AVAILABLE: Optional[bool] = None


def _check_b2_available() -> bool:
    global _B2_AVAILABLE
    if _B2_AVAILABLE is not None:
        return _B2_AVAILABLE

    try:
        s3 = storage_service.get_s3_client()
        bucket = getattr(storage_service, "B2_BUCKET_NAME", None)
        _B2_AVAILABLE = bool(s3) and bool(bucket)
        if not _B2_AVAILABLE:
            logger.warning("[PDF_ROUTER] B2 jo e disponueshme (s3/bucket mungon)")
    except Exception as e:
        logger.warning(f"[PDF_ROUTER] B2 kontroll dështoi: {e}")
        _B2_AVAILABLE = False

    return _B2_AVAILABLE


def _build_pdf_disk_index(search_roots: List[Path]) -> None:
    global _PDF_DISK_INDEX_BUILT
    if _PDF_DISK_INDEX_BUILT:
        return

    t0 = time.time()
    total = 0
    for root in search_roots:
        try:
            for p in root.rglob("*.pdf"):
                key = _to_alpha_key(p.name)
                if not key:
                    continue
                _PDF_DISK_INDEX.setdefault(key, []).append(str(p))
                total += 1
        except Exception as e:
            logger.debug(f"[PDF_DISK_INDEX] Skip {root}: {e}")

    _PDF_DISK_INDEX_BUILT = True
    logger.info(
        f"[PDF_DISK_INDEX] Built: {total} PDFs from "
        f"{len(search_roots)} roots in {int((time.time() - t0) * 1000)}ms"
    )


def clear_pdf_disk_index() -> None:
    global _PDF_DISK_INDEX_BUILT
    _PDF_DISK_INDEX.clear()
    _PDF_DISK_INDEX_BUILT = False
    logger.info("[PDF_DISK_INDEX] Cleared")


def _get_b2_listing_cached(s3, bucket: str, prefix: str) -> List[str]:
    now = time.time()
    cached = _B2_INDEX_CACHE.get(prefix)
    if cached and (now - cached[0]) < _B2_CACHE_TTL:
        return cached[1]

    keys: List[str] = []
    try:
        paginator = s3.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get('Contents', []):
                key = obj.get('Key', '')
                if key and key.lower().endswith('.pdf'):
                    keys.append(key)
    except Exception as e:
        logger.warning(f"[B2_CACHE] Listing failed for prefix '{prefix}': {e}")
        return []

    _B2_INDEX_CACHE[prefix] = (now, keys)
    logger.info(f"[B2_CACHE] Cached {len(keys)} keys for prefix '{prefix}'")
    return keys


# ═══════════════════════════════════════════════════════════════════════════
# MAIN STREAM FUNCTION (V93.2: RFC 5987 headers)
# ═══════════════════════════════════════════════════════════════════════════

def _stream_from_b2_or_local(
    filename: str,
    target_prefixes: List[str],
) -> StreamingResponse | FileResponse:
    if not target_prefixes:
        raise HTTPException(status_code=400, detail="target_prefixes required")

    raw_unquoted = urllib.parse.unquote(filename).strip()
    raw_name = _normalize_str(raw_unquoted)

    raw_basename = os.path.basename(raw_name) if "/" in raw_name and not raw_name.startswith("data/") else raw_name
    clean_search_name = re.sub(r'\.pdf$', '', raw_basename, flags=re.IGNORECASE).strip()
    alpha_target = _to_alpha_key(raw_basename)

    case_components = _parse_supreme_case_components(raw_name)

    # ─── MongoDB mapping ────────────────────────────────────────────────
    try:
        from app.core.db import get_db_instance
        db = get_db_instance()

        mongo_queries = [
            {"source": raw_basename},
            {"source": {"$regex": re.escape(clean_search_name), "$options": "i"}},
            {"case_number": {"$regex": re.escape(clean_search_name), "$options": "i"}},
            {"law_title": {"$regex": re.escape(clean_search_name), "$options": "i"}},
        ]

        if case_components:
            p_prefix, p_num, p_year = case_components
            short_y = p_year[-2:]
            flex_regex = (
                rf"{p_prefix}\.?\s*(?:nr\.?\s*)?0*{p_num}"
                rf"\s*[\/\-_\.\s]\s*(?:{p_year}|{short_y})"
            )
            mongo_queries.extend([
                {"case_number": {"$regex": flex_regex, "$options": "i"}},
                {"source": {"$regex": flex_regex, "$options": "i"}},
            ])

        doc = db.legal_knowledge_base.find_one(
            {"$or": mongo_queries},
            {"source": 1, "law_title": 1, "case_number": 1, "_id": 0},
        )
        if doc and doc.get("source"):
            found_source = _normalize_str(doc["source"])
            new_basename = os.path.basename(found_source) if "/" in found_source else found_source
            if new_basename and new_basename != raw_basename:
                logger.info(
                    f"[PDF_ROUTER] MongoDB mapped '{raw_basename}' → '{new_basename}'"
                )
                raw_basename = new_basename
                alpha_target = _to_alpha_key(new_basename)
    except Exception as e:
        logger.debug(f"[PDF_ROUTER] MongoDB mapping skipped: {e}")

    # ─── Disk search ────────────────────────────────────────────────────
    try:
        this_file = Path(__file__).resolve()
        disk_search_roots: List[Path] = []
        for p_idx in range(len(this_file.parents)):
            for sub in ("data", "data/case_law"):
                candidate = this_file.parents[p_idx] / sub
                if candidate.exists() and candidate.is_dir():
                    disk_search_roots.append(candidate)
        for base in (Path.cwd(), Path.cwd().parent):
            for sub in ("data", "backend/data"):
                candidate = base / sub
                if candidate.exists() and candidate.is_dir():
                    disk_search_roots.append(candidate)
        for p in (Path("/app/data"), Path("/app/backend/data")):
            if p.exists() and p.is_dir():
                disk_search_roots.append(p)

        seen = set()
        unique_roots: List[Path] = []
        for r in disk_search_roots:
            try:
                key = str(r.resolve())
                if key not in seen:
                    seen.add(key)
                    unique_roots.append(r)
            except Exception:
                pass

        _build_pdf_disk_index(unique_roots)

        best_disk_match: Optional[Tuple[int, str]] = None

        candidates = _PDF_DISK_INDEX.get(alpha_target, [])
        for path_str in candidates:
            fname = _normalize_str(os.path.basename(path_str))
            score = _score_filename_match(alpha_target, _to_alpha_key(fname), raw_basename, fname)
            if score >= 60 and (best_disk_match is None or score > best_disk_match[0]):
                best_disk_match = (score, path_str)

        if best_disk_match is None and alpha_target:
            for key, paths in _PDF_DISK_INDEX.items():
                score = _score_filename_match(alpha_target, key, raw_basename, key)
                if score >= 60:
                    for p in paths:
                        fname = _normalize_str(os.path.basename(p))
                        s2 = _score_filename_match(alpha_target, _to_alpha_key(fname), raw_basename, fname)
                        s2 = max(s2, score)
                        if s2 >= 60 and (best_disk_match is None or s2 > best_disk_match[0]):
                            best_disk_match = (s2, p)

        if best_disk_match is None and case_components:
            for key, paths in _PDF_DISK_INDEX.items():
                for p in paths:
                    fname = _normalize_str(os.path.basename(p))
                    if _matches_case_components(fname, *case_components):
                        best_disk_match = (75, p)
                        break
                if best_disk_match:
                    break

        if best_disk_match:
            best_path = best_disk_match[1]
            if os.path.exists(best_path):
                fname = _normalize_str(os.path.basename(best_path))
                logger.info(
                    f"[PDF_ROUTER] Disk match ({best_disk_match[0]}/100): "
                    f"'{raw_basename}' → {best_path}"
                )
                # V93.2: Content-Disposition RFC 5987-safe
                return FileResponse(
                    best_path,
                    media_type="application/pdf",
                    headers={
                        "Content-Disposition": _content_disposition(fname),
                        "Cache-Control": "public, max-age=86400",
                    },
                )
            else:
                logger.warning(f"[PDF_ROUTER] Disk match path missing: {best_path}")
    except Exception as e:
        logger.error(f"[PDF_ROUTER] Disk search error: {e}", exc_info=True)

    # ─── B2 (defensive) ─────────────────────────────────────────────────
    if _check_b2_available():
        try:
            s3 = storage_service.get_s3_client()
            bucket = storage_service.B2_BUCKET_NAME

            prefixes = [p for p in target_prefixes if p != ""]
            if not prefixes:
                prefixes = [""]

            best_b2_match: Optional[Tuple[int, str, str]] = None

            for prefix in prefixes:
                listing = _get_b2_listing_cached(s3, bucket, prefix)
                for key in listing:
                    b2_filename = _normalize_str(os.path.basename(key))
                    if not b2_filename or not b2_filename.lower().endswith('.pdf'):
                        continue

                    b2_alpha = _to_alpha_key(b2_filename)
                    score = _score_filename_match(alpha_target, b2_alpha, raw_basename, b2_filename)

                    if score < 60 and case_components:
                        if _matches_case_components(b2_filename, *case_components):
                            score = 75

                    if score >= 60:
                        if best_b2_match is None or score > best_b2_match[0]:
                            best_b2_match = (score, key, b2_filename)

            if best_b2_match:
                score, key, b2_filename = best_b2_match
                try:
                    stream, content_length = storage_service.get_file_stream_with_meta(key)
                    if stream:
                        logger.info(
                            f"[PDF_ROUTER] B2 match ({score}/100): "
                            f"'{raw_basename}' → {key}"
                        )
                        # V93.2: Content-Disposition RFC 5987-safe
                        headers = {
                            "Content-Disposition": _content_disposition(b2_filename),
                            "Cache-Control": "public, max-age=86400",
                        }
                        if content_length and content_length > 0:
                            headers["Content-Length"] = str(content_length)
                        return StreamingResponse(
                            stream,
                            media_type="application/pdf",
                            headers=headers,
                        )
                except Exception as e:
                    logger.warning(f"[PDF_ROUTER] B2 stream error for '{key}': {e}")

        except Exception as e:
            logger.warning(f"[PDF_ROUTER] B2 search exception: {e}", exc_info=True)
    else:
        logger.info("[PDF_ROUTER] B2 jo e disponueshme — kalojmë në 404")

    logger.error(
        f"[PDF_ROUTER 404] filename='{raw_name}' basename='{raw_basename}' "
        f"prefixes={target_prefixes} case_components={case_components}"
    )
    raise HTTPException(
        status_code=404,
        detail=f"Dokumenti '{raw_basename}' nuk u gjet në arkivën zyrtare.",
    )


# ═══════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/pdf/{filename:path}")
async def get_law_pdf(
    filename: str,
    current_user = Depends(get_current_user),
):
    try:
        return _stream_from_b2_or_local(
            filename,
            target_prefixes=["laws/ks/", "laws/", "case_law/"],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[PDF_ROUTER] Unhandled error for '{filename}': {e}", exc_info=True)
        raise HTTPException(
            status_code=404,
            detail=f"Dokumenti '{filename}' nuk u gjet.",
        )


@router.get("/caselaw/pdf/{filename:path}")
async def get_caselaw_pdf(
    filename: str,
    current_user = Depends(get_current_user),
):
    try:
        return _stream_from_b2_or_local(
            filename,
            target_prefixes=["case_law/", "data/case_law/", "jurisprudence/", "decisions/", "laws/"],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[PDF_ROUTER] Unhandled caselaw error for '{filename}': {e}", exc_info=True)
        raise HTTPException(
            status_code=404,
            detail=f"Aktgjykimi '{filename}' nuk u gjet.",
        )


__all__ = ["clear_pdf_disk_index"]