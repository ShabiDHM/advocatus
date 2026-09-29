# FILE: backend/app/api/endpoints/laws_pkg/laws_query_router.py
# PHOENIX PROTOCOL - JURIDICAL RAG ENGINE V208.6
#
# V208.6: BURIME NDËRKOMBËTARE (KEDNJ / OKB / Hagë).
#   - `/article` tani njeh burime eksterne (KEDNJ, OKB, Hagë) dhe kthen 200
#     me `is_external: true` në vend të 404.
#   - Përdoret `find_external_source` nga `mongo_verifier.external_registry`.
#   - Frontend-i (LawCitationLink) mund t'i shfaqë si "🌐 Ekstern" (blu).
#   - Nuk prish funksionalitetin ekzistues për ligjet e Kosovës.
#
# V208.5: FIX confidence 45% për akronime.
# V208.4: OPTIMIZIME /case-page.
# V208.3: FIX CONFIDENCE 40% FIKSE në /article.

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import Set, List, Optional, Dict, Any, Tuple
from pathlib import Path
import asyncio
import logging
import os
import re
import time
import json

from app.services import vector_store_service, storage_service
from app.services.llm.llm_client import _call_llm_async, clean_and_parse_json, FAST_SEARCH_MODEL
from app.api.endpoints.dependencies import get_current_user
from app.api.endpoints.laws_pkg.laws_dictionary import (
    _normalize_hallucinated_title,
    _natural_sort_key,
    _normalize_diacritics,
)
from app.api.endpoints.laws_pkg.laws_search_service import (
    find_documents_by_title,
    find_law_documents,
    _generate_source_info,
)
from app.api.endpoints.laws_pkg.repealed_registry import (
    find_repealed_info,
    get_all_repealed_titles,
    clear_registry_cache,
)

# V208.6: External sources registry (shared me mongo_verifier)
try:
    from app.services.document_review.mongo_verifier.external_registry import (
        find_external_source,
        get_all_external_sources,
        clear_registry_cache as clear_external_registry_cache,
    )
    _EXTERNAL_REGISTRY_AVAILABLE = True
except ImportError as _e:
    logging.getLogger(__name__).warning(
        f"[EXTERNAL_REGISTRY] Import failed: {_e} — burimet eksterne joaktive"
    )
    find_external_source = lambda x: None  # noqa: E731
    get_all_external_sources = lambda: []  # noqa: E731
    clear_external_registry_cache = lambda: None  # noqa: E731
    _EXTERNAL_REGISTRY_AVAILABLE = False


logger = logging.getLogger(__name__)
router = APIRouter()

CASE_NO_REGEX = re.compile(
    r'\b(?:PA1|PKR|PML|REV|KMLP|ANR|A\.NR|PZR)\.?\s*(?:nr|Nr|NR)?\.?\s*(\d+[\w\/\.\-]*)',
    re.IGNORECASE,
)
ARTICLE_EXTRACT_REGEX = re.compile(
    r'\b(?:neni|nenit|nenin|artikulli|art\.?)\s*(\d+[a-zA-Z]?)\b',
    re.IGNORECASE,
)

DOMAIN_GENERIC_STOPWORDS = frozenset({
    "procedurë", "procedure", "procedurës", "procedura", "gjyqësore", "gjyqesore",
    "gjykata", "gjykate", "vendim", "vendimi", "aktgjykim", "aktgjykimi", "republika",
    "kosovës", "kosoves", "ligji", "kodi", "neni", "nenit", "çështje", "ceshtje",
    "lëndë", "lende", "kolegji", "suprem", "supreme", "i", "e", "të", "te", "së", "se",
    "në", "ne", "me", "nga", "për", "per", "para", "pas", "ose", "dhe", "si", "ka",
})

JUNK_TEXT_PATTERNS = [
    r"PARATHËNIE", r"PARATHENIE", r"PËRMBAJTJA", r"PERMBAJTJA",
    r"TRYEZA E PUNËS", r"KOLOFONI", r"PËRMBLEDHJE E PRAKTIKËS GJYQËSORE",
    r"VENDIME TË PËRZGJEDHURA",
]

JUNK_TITLE_PATTERNS = [
    re.compile(r"PËRMBLEDHJE\s+E\s+PRAKTIKËS\s+GJYQËSORE", re.IGNORECASE),
    re.compile(r"PERMBLEDHJE\s+E\s+PRAKTIKES\s+GJYQESORE", re.IGNORECASE),
    re.compile(r"VENDIME\s+TË\s+PËRZGJEDHURA", re.IGNORECASE),
    re.compile(r"VENDIME\s+TE\s+PERZGJEDHURA", re.IGNORECASE),
    re.compile(r"PARATHËNIE", re.IGNORECASE),
    re.compile(r"PARATHENIE", re.IGNORECASE),
    re.compile(r"^PËRMBAJTJA", re.IGNORECASE),
    re.compile(r"^PERMBAJTJA", re.IGNORECASE),
]

_LAW_CODE_REGEX = re.compile(
    r'\d{2,4}\s*[\/\-_\s]?\s*[Ll]\s*[\/\-_\s]?\s*\d{2,4}|\d{4}\s*\/\s*\d{1,4}',
    re.IGNORECASE,
)


def _normalize_code(t: str) -> str:
    return re.sub(r'[\s\-_/]+', '', t.lower())


def _infer_match_type(doc_law_title: str, requested_title: str) -> str:
    if not doc_law_title or not requested_title:
        return "unknown"

    a = _normalize_diacritics(doc_law_title.lower().strip())
    b = _normalize_diacritics(requested_title.lower().strip())

    if not a or not b:
        return "unknown"

    if a == b:
        return "exact"

    a_codes = {_normalize_code(m.group(0)) for m in _LAW_CODE_REGEX.finditer(a)}
    b_codes = {_normalize_code(m.group(0)) for m in _LAW_CODE_REGEX.finditer(b)}
    if a_codes and b_codes and (a_codes & b_codes):
        return "code"

    if a in b or b in a:
        return "substring"

    a_words = {
        w for w in re.findall(r'\w+', a)
        if len(w) >= 4 and w not in DOMAIN_GENERIC_STOPWORDS
    }
    b_words = {
        w for w in re.findall(r'\w+', b)
        if len(w) >= 4 and w not in DOMAIN_GENERIC_STOPWORDS
    }
    if a_words and b_words and (a_words & b_words):
        return "word"

    return "unknown"


def _is_junk_title(title: str) -> bool:
    if not title:
        return True
    t = title.strip()
    if not t:
        return True
    for pattern in JUNK_TITLE_PATTERNS:
        if pattern.search(t):
            return True
    return False


def _is_valid_article_number(art: Any) -> bool:
    if art is None:
        return False
    s = str(art).strip()
    if not s:
        return False
    if s in ("0", "0.", "00"):
        return False
    return True


_ARTICLE_PAGE_CACHE: Dict[str, Optional[int]] = {}
_ARTICLE_PAGE_CACHE_MAX = 5000

_B2_FILENAMES_CACHE: Dict[str, tuple] = {}
_B2_FILENAMES_TTL = 300


def clear_query_router_caches() -> None:
    _ARTICLE_PAGE_CACHE.clear()
    _B2_FILENAMES_CACHE.clear()
    clear_registry_cache()
    clear_external_registry_cache()
    logger.info("[QUERY_ROUTER] Caches cleared")


def _get_project_data_dir() -> Optional[Path]:
    current = Path(__file__).resolve()
    for parent in [current, *current.parents]:
        for sub in ("data", "backend/data"):
            d = parent / sub
            if d.exists() and d.is_dir():
                return d
    return None


def _scan_exact_article_page(pdf_source_name: str, article_num: str) -> Optional[int]:
    if not pdf_source_name or not article_num:
        return None

    cache_key = f"{pdf_source_name}::{article_num}"
    if cache_key in _ARTICLE_PAGE_CACHE:
        return _ARTICLE_PAGE_CACHE[cache_key]

    try:
        import fitz
        data_dir = _get_project_data_dir()
        if not data_dir:
            _ARTICLE_PAGE_CACHE[cache_key] = None
            return None

        clean_target = os.path.basename(pdf_source_name).strip().lower()
        clean_art = str(article_num).strip().replace("Neni", "").replace("neni", "").strip()

        pdf_file_path: Optional[Path] = None
        for candidate in data_dir.rglob("*.pdf"):
            if candidate.name.lower() == clean_target:
                pdf_file_path = candidate
                break

        if not pdf_file_path:
            for candidate in data_dir.rglob("*.pdf"):
                c_name = candidate.name.lower()
                if "penal" in clean_target and "penal" in c_name and "procedur" not in c_name:
                    pdf_file_path = candidate
                    break

        if not pdf_file_path or not pdf_file_path.exists():
            _ARTICLE_PAGE_CACHE[cache_key] = None
            return None

        header_regex = re.compile(
            rf'(?:^|\n)\s*(?:Neni|NENI|Artikulli|ARTIKULLI)\s+{re.escape(clean_art)}\b',
            re.MULTILINE,
        )

        doc = fitz.open(str(pdf_file_path))
        try:
            for page_idx in range(len(doc)):
                page_text = doc[page_idx].get_text("text") or ""
                if header_regex.search(page_text):
                    found_page = page_idx + 1
                    _ARTICLE_PAGE_CACHE[cache_key] = found_page
                    return found_page

            loose_regex = re.compile(rf'\b(?:Neni|NENI)\s+{re.escape(clean_art)}\b')
            for page_idx in range(len(doc)):
                page_text = doc[page_idx].get_text("text") or ""
                if loose_regex.search(page_text):
                    found_page = page_idx + 1
                    _ARTICLE_PAGE_CACHE[cache_key] = found_page
                    return found_page
        finally:
            doc.close()
    except Exception as ex:
        logger.debug(f"[SCAN_PAGE] Exception for {article_num}: {ex}")

    _ARTICLE_PAGE_CACHE[cache_key] = None
    if len(_ARTICLE_PAGE_CACHE) > _ARTICLE_PAGE_CACHE_MAX:
        for k in list(_ARTICLE_PAGE_CACHE.keys())[:1000]:
            _ARTICLE_PAGE_CACHE.pop(k, None)
    return None


def _get_b2_filenames(prefix: str) -> List[str]:
    now = time.time()
    cached = _B2_FILENAMES_CACHE.get(prefix)
    if cached and (now - cached[0]) < _B2_FILENAMES_TTL:
        return cached[1]

    filenames: List[str] = []
    try:
        s3 = storage_service.get_s3_client()
        bucket = storage_service.B2_BUCKET_NAME
        paginator = s3.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get('Contents', []):
                key = obj.get('Key', '')
                fname = os.path.basename(key)
                if fname and fname.lower().endswith('.pdf'):
                    filenames.append(fname)
    except Exception as e:
        logger.warning(f"[B2_LIST] Failed for prefix '{prefix}': {e}")

    _B2_FILENAMES_CACHE[prefix] = (now, filenames)
    return filenames


def _is_junk_frontmatter(text: str) -> bool:
    if not text:
        return False
    first_lines = text[:250].upper()
    for pattern in JUNK_TEXT_PATTERNS:
        if re.search(pattern, first_lines):
            if "PARATHËNIE" in first_lines or "PËRMBAJTJA" in first_lines:
                return True
    return False


async def _rerank_and_verify_caselaw_with_ai(
    user_query: str,
    raw_caselaw_candidates: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    if not raw_caselaw_candidates:
        return []

    clean_candidates = [
        c for c in raw_caselaw_candidates
        if not _is_junk_frontmatter(c.get("text", "")) and len(c.get("text", "").strip()) > 80
    ]
    if not clean_candidates:
        return []

    candidates_context = []
    for idx, c in enumerate(clean_candidates[:8]):
        candidates_context.append({
            "candidate_id": idx,
            "case_number": c.get("case_number", "Aktgjykim"),
            "page": c.get("page", 1),
            "source": c.get("source", ""),
            "text_sample": c.get("text", "")[:450],
        })

    system_prompt = (
        "Ti je Gjyqtari Mbikëqyrës i Integritetit Ligjor në Republikën e Kosovës.\n"
        "Ke përpara pyetjen e avokatit dhe një listë aktgjykimesh kandidate të Gjykatës Supreme.\n"
        "DETYRA JOTE KRITIKE: Verifiko në mënyrë rigoroze nëse secili aktgjykim trajton VËRTET temën thelbësore të kërkuar.\n"
        "Nëse një aktgjykim është i parëndësishëm, REFUZOJE menjëherë.\n\n"
        "PËRGJIGJU VETËM ME JSON NË KËTË FORMAT:\n"
        "{\n"
        '  "relevant_candidates": [\n'
        '    {\n'
        '      "candidate_id": 0,\n'
        '      "is_substantively_relevant": true,\n'
        '      "ratio_decidendi": "Arsyetimi thelbësor dhe i plotë i Gjykatës Supreme për këtë çështje konkrete."\n'
        '    }\n'
        '  ]\n'
        "}\n"
        "Nëse ASNJE nga aktgjykimet nuk lidhet me temën, kthe listë boshe: {\"relevant_candidates\": []}."
    )

    user_prompt = (
        f"KËRKESA JURIDIKE:\n{user_query}\n\n"
        f"AKTGJYKIMET KANDIDATE:\n{json.dumps(candidates_context, ensure_ascii=False, indent=2)}"
    )

    try:
        raw_response = await _call_llm_async(
            system_prompt=system_prompt,
            user_content=user_prompt,
            json_mode=True,
            model=FAST_SEARCH_MODEL,
        )
        parsed = clean_and_parse_json(raw_response)

        verified_results = []
        if isinstance(parsed, dict) and "relevant_candidates" in parsed:
            for item in parsed["relevant_candidates"]:
                if item.get("is_substantively_relevant") is True:
                    c_id = item.get("candidate_id")
                    if isinstance(c_id, int) and 0 <= c_id < len(clean_candidates):
                        orig = clean_candidates[c_id]
                        ratio = item.get("ratio_decidendi") or orig.get("interpretation_commentary")
                        verified_results.append({
                            "case_number": orig.get("case_number", "Gjykata Supreme"),
                            "title": f"⚖️ {orig.get('case_number', 'Gjykata Supreme')} (Faqja {orig.get('page')})",
                            "interpretation_commentary": ratio,
                            "source": orig.get("source", ""),
                            "page": orig.get("page", 1),
                            "text": orig.get("text", ""),
                        })
        return verified_results
    except Exception as e:
        logger.warning(f"[RERANK] Fast reranking error: {e}")
        return []


async def _synthesize_legal_qualification(
    user_query: str,
    retrieved_statutes: List[Dict[str, Any]],
    retrieved_caselaw: List[Dict[str, Any]],
) -> Dict[str, str]:
    context_statutes = "\n---\n".join([
        f"LIGJI: {s.get('law_title')} | NENI: {s.get('article_number')}\nTEKSTI: {s.get('text', '')[:400]}"
        for s in retrieved_statutes[:4]
    ])
    context_caselaw = "\n---\n".join([
        f"AKTGJYKIM: {c.get('case_number')} | Faqja: {c.get('page')}\nARSYETIMI: {c.get('interpretation_commentary')}"
        for c in retrieved_caselaw[:3]
    ])

    system_prompt = (
        "Ti je Eksperti Kryesor Juridik i Republikës së Kosovës.\n"
        "Analizo këtë çështje juridike bazuar EKSKLUZIVISHT mbi normat ligjore dhe precedentët realë të ofruar.\n"
        "PËRGJIGJU VETËM ME JSON:\n"
        "{\n"
        '  "legal_institute": "Emërtimi i saktë juridik i institutit në Kosovë",\n'
        '  "plain_explanation": "Përmbledhje e thellë doktrinore me 2-3 fjali mbi standardet ligjore dhe vendimet përkatëse."\n'
        "}"
    )

    user_prompt = (
        f"PYETJA E AVOKATIT:\n{user_query}\n\n"
        f"DISPOZITAT E GJETURA:\n{context_statutes}\n\n"
        f"PRECEDENTËT E VERIFIKUAR:\n"
        f"{context_caselaw if context_caselaw else 'Nuk ka precedent të drejtpërdrejtë në fond.'}"
    )

    try:
        raw_response = await _call_llm_async(
            system_prompt=system_prompt,
            user_content=user_prompt,
            json_mode=True,
            model=FAST_SEARCH_MODEL,
        )
        parsed = clean_and_parse_json(raw_response)
        if isinstance(parsed, dict) and "legal_institute" in parsed:
            return parsed
    except Exception as e:
        logger.warning(f"[QUALIFICATION] Fallback: {e}")

    first_law = (
        retrieved_statutes[0].get("law_title", "Kodi Zyrtar i Kosovës")
        if retrieved_statutes else "Kualifikim Juridik"
    )
    return {
        "legal_institute": f"Analizë Juridike: {first_law}",
        "plain_explanation": "Çështja rregullohet sipas dispozitave pozitive të Republikës së Kosovës.",
    }


@router.get(
    "/ai-semantic-search",
    operation_id="laws_ai_semantic_search_get",
)
@router.post(
    "/ai-semantic-search",
    operation_id="laws_ai_semantic_search_post",
)
async def ai_semantic_law_search(
    query: str = Query(None),
    payload: Optional[Dict[str, Any]] = Body(None),
    current_user = Depends(get_current_user),
):
    user_query = query or (payload.get("query") if payload else "")
    if not user_query or not user_query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    clean_q = user_query.strip()

    try:
        from app.core.db import get_db_instance
        db = get_db_instance()
        coll = db["legal_knowledge_base"]

        raw_retrieved = vector_store_service.query_global_knowledge_base(clean_q, n_results=35)

        statute_candidates = []
        raw_caselaw_candidates = []
        seen_statute_keys = set()
        seen_case_keys = set()

        for item in raw_retrieved:
            source_tag = item.get("source", "")
            full_text = item.get("text", "")
            page_val = item.get("page", 1)
            law_t = item.get("law_title", "")
            art_num = str(item.get("article_number", "")).strip()

            is_case = (
                "PRECEDENT REAL" in source_tag
                or "Gjykata Supreme" in law_t
                or any(k in source_tag.lower() for k in ["praktikës", "praktikes", "vendime", "case_law"])
            )

            if is_case:
                m = CASE_NO_REGEX.search(full_text) or CASE_NO_REGEX.search(source_tag)
                case_no = m.group(0).upper().replace('  ', ' ') if m else "Aktgjykim i Gjykatës Supreme"
                case_key = f"{case_no}_{page_val}"
                if case_key not in seen_case_keys:
                    seen_case_keys.add(case_key)
                    raw_caselaw_candidates.append({
                        "case_number": case_no,
                        "source": (
                            source_tag.split("Burimi:")[-1].replace(")", "").strip()
                            if "Burimi:" in source_tag else source_tag
                        ),
                        "page": page_val,
                        "text": full_text,
                    })
            else:
                if _is_valid_article_number(art_num):
                    statute_key = f"{law_t}_{art_num}"
                    if statute_key not in seen_statute_keys:
                        seen_statute_keys.add(statute_key)
                        statute_candidates.append({
                            "law_title": law_t,
                            "article_number": art_num,
                            "paragraph_text": full_text,
                            "source": source_tag,
                            "page": page_val,
                            "text": full_text,
                        })

        direct_art_match = ARTICLE_EXTRACT_REGEX.search(clean_q)
        if direct_art_match:
            art_cand = direct_art_match.group(1)
            if not any(s.get("article_number") == art_cand for s in statute_candidates):
                exact_doc = coll.find_one(
                    {
                        "article_number": {
                            "$in": [art_cand, f"{art_cand}.",
                                    int(art_cand) if art_cand.isdigit() else art_cand]
                        },
                        "is_article": True,
                    },
                    sort=[("chunk_index", 1)],
                )
                if exact_doc:
                    statute_candidates.insert(0, {
                        "law_title": exact_doc.get("law_title", "Ligji Zyrtar"),
                        "article_number": art_cand,
                        "paragraph_text": exact_doc.get("text", ""),
                        "source": exact_doc.get("source", ""),
                        "page": (
                            exact_doc.get("actual_page")
                            or exact_doc.get("page")
                            or exact_doc.get("page_number")
                        ),
                        "text": exact_doc.get("text", ""),
                    })

        ranked_statutes = statute_candidates

        logger.info(
            f"[AI_SEARCH] '{clean_q[:60]}...' → "
            f"{len(ranked_statutes)} statutes, {len(raw_caselaw_candidates)} caselaw"
        )

        verified_caselaw, qualification = await asyncio.gather(
            _rerank_and_verify_caselaw_with_ai(clean_q, raw_caselaw_candidates),
            _synthesize_legal_qualification(clean_q, ranked_statutes, []),
        )

        matched_statutes = []
        for s in ranked_statutes[:4]:
            law_name = s.get("law_title", "Ligji Zyrtar")
            art_no = s.get("article_number", "")
            p_text = s.get("paragraph_text", "")
            doc_src = s.get("source", "")
            p_num = s.get("page")

            related_sc = []
            if art_no:
                art_pattern = rf'\b(?:Neni|neni|NENI)\s+{re.escape(str(art_no))}\b'
                for c in verified_caselaw:
                    if re.search(art_pattern, c.get("text", ""), re.IGNORECASE):
                        related_sc.append(c)

            is_verified = bool(doc_src) and bool(law_name) and law_name != "Ligji Zyrtar"

            repealed_info = find_repealed_info(law_name)

            entry = {
                "law_title": law_name,
                "article_number": art_no,
                "paragraph_text": p_text,
                "explanation": p_text[:260] + "..." if len(p_text) > 260 else p_text,
                "is_verified_in_db": is_verified,
                "verification_status": (
                    "VERIFIED" if is_verified else "UNVERIFIED"
                ),
                "verification_source": doc_src or "I panjohur",
                "page_number": p_num,
                "supreme_precedents_count": len(related_sc),
                "verification_tooltip": (
                    f"✅ Verifikuar në Fondin Zyrtar: {law_name}, Neni {art_no}"
                    + (f" (Faqja {p_num})." if p_num else ".")
                    if is_verified
                    else "⚠️ Nuk u verifikua në DB."
                ),
                "supreme_court_interpretations": related_sc,
            }

            if repealed_info:
                entry["is_repealed"] = True
                entry["repealed_info"] = repealed_info
                entry["warning"] = repealed_info.get("warning_message", "")
            else:
                entry["is_repealed"] = False

            matched_statutes.append(entry)

        return {
            "query": clean_q,
            "ai_diagnostic": {
                "legal_institute": qualification.get("legal_institute", "Kualifikim Ligjor"),
                "plain_explanation": qualification.get("plain_explanation", ""),
                "matched_statutes": matched_statutes,
            },
            "caselaw_precedents": verified_caselaw[:4],
            "success": True,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[AI_SEARCH] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Dynamic Search Error: {str(e)}")


_CASE_MATCH_STRATEGIES: List[Dict[str, Any]] = [
    {
        "name": "case_number_exact",
        "query_builder": lambda t: {"case_number": t},
        "confidence_level": "HIGH",
        "confidence_score": 0.95,
        "is_reference_only": False,
    },
    {
        "name": "case_number_regex",
        "query_builder": lambda t: {"case_number": {"$regex": re.escape(t), "$options": "i"}},
        "confidence_level": "MEDIUM",
        "confidence_score": 0.80,
        "is_reference_only": False,
    },
    {
        "name": "law_title_exact",
        "query_builder": lambda t: {"law_title": t},
        "confidence_level": "MEDIUM",
        "confidence_score": 0.75,
        "is_reference_only": False,
    },
    {
        "name": "law_title_regex",
        "query_builder": lambda t: {"law_title": {"$regex": re.escape(t), "$options": "i"}},
        "confidence_level": "LOW",
        "confidence_score": 0.60,
        "is_reference_only": False,
    },
    {
        "name": "text_reference",
        "query_builder": lambda t: {"text": {"$regex": re.escape(t), "$options": "i"}},
        "confidence_level": "LOW",
        "confidence_score": 0.40,
        "is_reference_only": True,
    },
]


def _try_case_page_strategy(
    coll,
    clean_title: str,
    strategy: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    projection = {
        "law_title": 1, "source": 1, "page": 1, "actual_page": 1,
        "page_number": 1, "case_number": 1, "_id": 0,
    }

    try:
        if "case_number" in strategy.get("name", "") and strategy["name"] == "case_number_exact":
            query = strategy["query_builder"](clean_title)
            doc = coll.find_one(
                {**query, "page": {"$gt": 20}},
                projection,
                sort=[("page", 1)],
            )
            if doc:
                return doc

        query = strategy["query_builder"](clean_title)

        if "case_number" in strategy["name"]:
            doc = coll.find_one(
                {**query, "page": {"$gt": 20}},
                projection,
                sort=[("page", 1)],
            )
            if doc:
                return doc

        return coll.find_one(
            query,
            projection,
            sort=[("page", 1)],
        )
    except Exception as e:
        logger.debug(f"[CASE_PAGE] Strategy '{strategy['name']}' error: {e}")
        return None


def _resolve_case_page(coll, clean_title: str) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    for strategy in _CASE_MATCH_STRATEGIES:
        doc = _try_case_page_strategy(coll, clean_title, strategy)
        if doc:
            return doc, strategy
    return None, None


@router.get("/case-page")
async def get_case_starting_page(
    law_title: str = Query(...),
    current_user = Depends(get_current_user),
):
    try:
        from app.core.db import get_db_instance
        db = get_db_instance()
        clean_title = law_title.strip()

        if not clean_title:
            return {
                "page": None,
                "page_number": None,
                "law_title": clean_title,
                "found": False,
                "source_info": None,
            }

        coll = db.legal_knowledge_base

        t0 = time.time()
        doc, strategy = _resolve_case_page(coll, clean_title)
        elapsed_ms = int((time.time() - t0) * 1000)

        if not doc:
            logger.info(f"[CASE_PAGE] '{clean_title}' → NOT FOUND ({elapsed_ms}ms)")
            return {
                "page": None,
                "page_number": None,
                "law_title": clean_title,
                "found": False,
                "source_info": None,
            }

        raw_page = (
            doc.get("actual_page")
            or doc.get("page")
            or doc.get("page_number")
        )
        page_val: Optional[int]
        try:
            page_val = int(raw_page) if raw_page is not None else None
        except (ValueError, TypeError):
            page_val = None

        strategy_name = strategy["name"] if strategy else "unknown"
        is_reference_only = strategy.get("is_reference_only", False) if strategy else False

        source_info: Dict[str, Any] = {
            "match_type": strategy_name,
            "confidence": {
                "level": strategy["confidence_level"] if strategy else "NONE",
                "score": strategy["confidence_score"] if strategy else 0.0,
            },
            "is_reference_only": is_reference_only,
        }

        logger.info(
            f"[CASE_PAGE] '{clean_title}' → found via {strategy_name} "
            f"(page={page_val}, ref_only={is_reference_only}) in {elapsed_ms}ms"
        )

        return {
            "page": page_val,
            "page_number": page_val,
            "law_title": doc.get("source") or clean_title,
            "found": page_val is not None,
            "source_info": source_info,
        }

    except Exception as e:
        logger.warning(f"[CASE_PAGE] Error: {e}")
        return {
            "page": None,
            "page_number": None,
            "law_title": law_title,
            "found": False,
            "source_info": None,
        }


@router.get("/titles")
async def get_law_titles(current_user = Depends(get_current_user)):
    try:
        from app.core.db import get_db_instance
        db = get_db_instance()

        caselaw_filter = {
            "$or": [
                {"category": "caselaw"},
                {"is_case_law": True},
                {
                    "case_number": {
                        "$exists": True,
                        "$nin": [None, ""],
                    }
                },
                {
                    "source": {
                        "$regex": r"case_law|supreme|praktikës|praktikes|vendime",
                        "$options": "i",
                    }
                },
                {
                    "law_title": {
                        "$regex": r"Gjykata\s+Supreme|PML|REV|PA1|PKR",
                        "$options": "i",
                    }
                },
            ]
        }
        caselaw_db_titles = db.legal_knowledge_base.distinct("law_title", caselaw_filter)
        caselaw_db_sources = db.legal_knowledge_base.distinct("source", caselaw_filter)
        b2_caselaw = _get_b2_filenames("case_law/")

        raw_caselaw = set(
            t.strip() for t in (caselaw_db_titles + caselaw_db_sources + b2_caselaw)
            if t and t.strip()
        )

        clean_caselaw = sorted([
            t for t in raw_caselaw if not _is_junk_title(t)
        ])

        statutes_filter = {
            "is_article": True,
            "$nor": [
                {"category": "caselaw"},
                {"is_case_law": True},
                {
                    "source": {
                        "$regex": r"case_law|supreme|praktikës|praktikes|vendime",
                        "$options": "i",
                    }
                },
                {
                    "law_title": {
                        "$regex": r"Gjykata\s+Supreme|PML|REV|PA1|PKR",
                        "$options": "i",
                    }
                },
            ],
        }
        all_statute_titles = db.legal_knowledge_base.distinct("law_title", statutes_filter)

        raw_statutes = []
        for t in all_statute_titles:
            t_clean = t.strip()
            if (
                t_clean
                and not t_clean.lower().endswith('.pdf')
                and not CASE_NO_REGEX.search(t_clean)
                and "supreme" not in t_clean.lower()
                and not _is_junk_title(t_clean)
            ):
                raw_statutes.append(t_clean)

        clean_statutes = sorted(list(set(raw_statutes)))

        repealed_statutes: List[Dict[str, Any]] = []
        for title in clean_statutes:
            info = find_repealed_info(title)
            if info:
                repealed_statutes.append({
                    "law_title": title,
                    "repealed_by": info.get("repealed_by", ""),
                    "repealed_date": info.get("repealed_date", ""),
                    "source": info.get("source", ""),
                    "reason": info.get("reason", ""),
                    "warning": info.get("warning_message", ""),
                })

        # V208.6: Shto burimet eksterne në listën e statutave (me flamur)
        external_sources: List[Dict[str, Any]] = []
        for src in get_all_external_sources():
            external_sources.append({
                "law_title": src.get("canonical_name", ""),
                "short_name": src.get("short_name", ""),
                "is_external": True,
                "category": src.get("category", "international_treaty"),
                "external_source_id": src.get("id", ""),
            })

        return {
            "statutes": clean_statutes,
            "repealed_statutes": repealed_statutes,
            "external_sources": external_sources,
            "case_law": clean_caselaw,
            "all_titles": sorted(list(set(clean_statutes + clean_caselaw))),
        }
    except Exception as e:
        logger.error(f"[TITLES] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching titles: {str(e)}")


@router.get("/by-title")
async def get_law_articles(
    law_title: str = Query(...),
    current_user = Depends(get_current_user),
):
    try:
        from app.core.db import get_db_instance
        db = get_db_instance()
        clean_title = law_title.strip()

        mapped_title = _normalize_hallucinated_title(clean_title, "", db=db)

        projection = {
            "law_title": 1, "article_number": 1, "source": 1,
            "chunk_index": 1, "page": 1, "page_number": 1, "actual_page": 1,
        }

        docs = find_documents_by_title(
            db,
            mapped_title if mapped_title else clean_title,
            fields=projection,
        )

        if not docs:
            words = [re.escape(w) for w in clean_title.split() if len(w) > 3]
            if words:
                docs = list(
                    db.legal_knowledge_base.find(
                        {
                            "is_article": True,
                            "$and": [
                                {"law_title": {"$regex": kw, "$options": "i"}}
                                for kw in words[:3]
                            ],
                        },
                        projection,
                    ).limit(600)
                )

        if not docs:
            raise HTTPException(
                status_code=404,
                detail=f"Ligji '{law_title}' nuk u gjet në bazën e të dhënave.",
            )

        canonical_title = docs[0].get("law_title", clean_title)

        articles: Set[str] = set()
        for d in docs:
            art = d.get("article_number")
            if _is_valid_article_number(art):
                articles.add(str(art))

        sorted_articles = sorted(list(articles), key=_natural_sort_key)

        raw_page = (
            docs[0].get("actual_page")
            or docs[0].get("page")
            or docs[0].get("page_number")
        )
        try:
            page_val = int(raw_page) if raw_page is not None else None
        except (ValueError, TypeError):
            page_val = None

        repealed_info = find_repealed_info(canonical_title)

        response = {
            "law_title": canonical_title,
            "source": str(docs[0].get("source", "")),
            "page": page_val,
            "page_number": page_val,
            "is_official_statute": True,
            "article_count": len(sorted_articles),
            "articles": sorted_articles,
        }

        if repealed_info:
            response["is_repealed"] = True
            response["repealed_info"] = repealed_info
            response["warning"] = repealed_info.get("warning_message", "")
        else:
            response["is_repealed"] = False

        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[BY_TITLE] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/article")
async def get_law_article(
    law_title: str = Query(...),
    article_number: str = Query(...),
    current_user = Depends(get_current_user),
):
    try:
        from app.core.db import get_db_instance
        db = get_db_instance()

        clean_law_title = law_title.strip()
        raw_art = str(article_number).strip()

        if not _is_valid_article_number(raw_art):
            raise HTTPException(
                status_code=404,
                detail=f"Neni '{raw_art}' nuk është nen valid.",
            )

        art_digits = re.sub(r'\D+', '', raw_art) or raw_art

        # ═══════════════════════════════════════════════════════════════════
        # V208.6: Kontrollo nëse është burim ekstern (KEDNJ, OKB, Hagë)
        #         PARA se të kërkojë në DB.
        # ═══════════════════════════════════════════════════════════════════
        external = find_external_source(clean_law_title)
        if external:
            logger.info(
                f"[ARTICLE] '{clean_law_title}' Neni {art_digits} → "
                f"EXTERNAL [{external['id']}] ({external['canonical_name'][:50]}...)"
            )

            return {
                "law_title": external["canonical_name"],
                "article_number": art_digits,
                "source": external["constitutional_basis"],
                "page": None,
                "page_number": None,
                "text": external["note"],
                "is_external": True,
                "external_source_id": external["id"],
                "external_category": external["category"],
                "external_short_name": external.get("short_name", ""),
                "is_repealed": False,
                "source_info": {
                    "confidence": {
                        "level": "HIGH",
                        "score": 1.0,
                        "label": "Traktat ndërkombëtar",
                        "icon": "🌐",
                        "color": "info",
                        "description": external["note"],
                    },
                    "matched_law": external["canonical_name"],
                    "matched_article": art_digits,
                    "source_file": external["constitutional_basis"],
                    "was_mapped": False,
                    "verification_hint": f"🌐 Traktat ndërkombëtar: {external['canonical_name']}",
                    "match_count": 1,
                    "is_official_statute": False,
                    "is_external": True,
                    "page": None,
                    "page_available": False,
                },
            }

        # ═══ Vazhdon me logjikën normale për ligjet e Kosovës ═══
        art_possible_forms = [
            art_digits,
            f"{art_digits}.",
            f"Neni {art_digits}",
            f"Neni {art_digits}.",
            raw_art,
            f"{raw_art}.",
        ]
        if art_digits.isdigit():
            art_possible_forms.append(int(art_digits))

        projection = {
            "law_title": 1, "article_number": 1, "source": 1,
            "chunk_index": 1, "page": 1, "page_number": 1,
            "actual_page": 1, "text": 1,
        }

        mapped_title = _normalize_hallucinated_title(clean_law_title, raw_art, db=db)

        statute_docs = list(
            db.legal_knowledge_base.find(
                {
                    "article_number": {"$in": art_possible_forms},
                    "is_article": True,
                    "law_title": {
                        "$regex": f"^{re.escape(mapped_title)}$",
                        "$options": "i",
                    },
                },
                projection,
            ).sort([("chunk_index", 1), ("_id", 1)])
        )

        if not statute_docs:
            statute_docs = list(
                db.legal_knowledge_base.find(
                    {
                        "article_number": {"$in": art_possible_forms},
                        "is_article": True,
                        "law_title": {
                            "$regex": re.escape(mapped_title),
                            "$options": "i",
                        },
                    },
                    projection,
                ).sort([("chunk_index", 1), ("_id", 1)])
            )

        if not statute_docs:
            words = [w for w in re.findall(r'[\w\d]+', mapped_title) if len(w) >= 3]
            if words:
                statute_docs = list(
                    db.legal_knowledge_base.find(
                        {
                            "article_number": {"$in": art_possible_forms},
                            "is_article": True,
                            "$and": [
                                {"law_title": {"$regex": re.escape(w), "$options": "i"}}
                                for w in words[:3]
                            ],
                        },
                        projection,
                    ).sort([("chunk_index", 1), ("_id", 1)])
                )

        doc_source = ""
        matched_canonical_title = clean_law_title

        if statute_docs:
            doc_source = statute_docs[0].get("source", "")
            matched_canonical_title = statute_docs[0].get("law_title", clean_law_title)
        else:
            candidate = db.legal_knowledge_base.find_one(
                {"law_title": {"$regex": re.escape(mapped_title), "$options": "i"}},
                projection,
            )
            if candidate:
                doc_source = candidate.get("source", "")
                matched_canonical_title = candidate.get("law_title", clean_law_title)

        if not doc_source:
            raise HTTPException(
                status_code=404,
                detail=f"Ligji '{clean_law_title}' nuk u gjet.",
            )

        cached_page = None
        if statute_docs:
            cached_page = (
                statute_docs[0].get("actual_page")
                or statute_docs[0].get("page")
                or statute_docs[0].get("page_number")
            )

        try:
            cached_page_int = int(cached_page) if cached_page else 0
        except (ValueError, TypeError):
            cached_page_int = 0

        if cached_page_int > 0:
            page_val: Optional[int] = cached_page_int
        else:
            real_page = _scan_exact_article_page(doc_source, art_digits)
            if real_page:
                page_val = real_page
                if statute_docs:
                    try:
                        db.legal_knowledge_base.update_many(
                            {"_id": {"$in": [d["_id"] for d in statute_docs]}},
                            {"$set": {"page": page_val, "actual_page": page_val}},
                        )
                    except Exception as e:
                        logger.warning(f"[ARTICLE] Cache page update failed: {e}")
            else:
                page_val = None

        full_text = "\n\n".join([
            doc.get("text", "") for doc in statute_docs if doc and doc.get("text")
        ])
        if not full_text:
            full_text = f"Neni {art_digits} i {matched_canonical_title}."

        primary_doc = statute_docs[0] if statute_docs else {}

        match_type = _infer_match_type(matched_canonical_title, mapped_title)

        metadata = {
            "title_match_type": match_type,
            "article_matches": len(statute_docs),
            "candidate_count": 1,
            "was_mapped": mapped_title != clean_law_title,
        }

        logger.info(
            f"[ARTICLE] '{clean_law_title}' Neni {art_digits} → "
            f"mapped='{mapped_title[:50]}...' "
            f"matched='{matched_canonical_title[:50]}...' "
            f"match_type={match_type} "
            f"article_matches={len(statute_docs)}"
        )

        source_info = _generate_source_info(
            primary_doc,
            metadata,
            clean_law_title,
            art_digits,
        )
        source_info["page"] = page_val
        source_info["source_file"] = doc_source

        repealed_info = find_repealed_info(matched_canonical_title)

        response = {
            "law_title": matched_canonical_title,
            "article_number": art_digits,
            "source": doc_source,
            "page": page_val,
            "page_number": page_val,
            "text": full_text,
            "source_info": source_info,
            "is_external": False,
        }

        if repealed_info:
            response["is_repealed"] = True
            response["repealed_info"] = repealed_info
            response["warning"] = repealed_info.get("warning_message", "")
        else:
            response["is_repealed"] = False

        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ARTICLE] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Gabim gjatë hapjes së nenit: {str(e)}")


@router.get("/search")
async def search_laws(
    q: str = Query(...),
    limit: int = Query(50, ge=1, le=200),
    current_user = Depends(get_current_user),
):
    if not q or not q.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    try:
        results = vector_store_service.query_global_knowledge_base(q, n_results=limit)
        if not isinstance(results, list):
            logger.warning(f"[SEARCH] Vector store returned non-list: {type(results)}")
            return []
        return results
    except Exception as e:
        logger.error(f"[SEARCH] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get(path="/{chunk_id}")
async def get_law_chunk(
    chunk_id: str,
    current_user = Depends(get_current_user),
):
    try:
        from app.core.db import get_db_instance
        db = get_db_instance()
        doc = db.legal_knowledge_base.find_one({"chunk_id": chunk_id})
        if not doc:
            raise HTTPException(status_code=404, detail="Chunk not found")

        raw_page = (
            doc.get("actual_page")
            or doc.get("page")
            or doc.get("page_number")
        )
        try:
            page_val = int(raw_page) if raw_page is not None else None
        except (ValueError, TypeError):
            page_val = None

        return {
            "law_title": str(doc.get("law_title", "Ligji")),
            "article_number": str(doc.get("article_number", "")),
            "source": str(doc.get("source", "")),
            "page": page_val,
            "page_number": page_val,
            "text": doc.get("text", ""),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


__all__ = ["clear_query_router_caches"]