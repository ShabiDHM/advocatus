# FILE: backend/app/api/endpoints/laws_pkg/laws_query_router.py
# PHOENIX PROTOCOL - JURISDICTIONAL DOMAIN ISOLATION & STOP-WORD PURGED RAG V130.0

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import Set, List, Optional, Dict, Any, Tuple
import logging
import os
import re
import json

from app.services import vector_store_service, storage_service
from app.api.endpoints.dependencies import get_current_user
from app.api.endpoints.laws_pkg.laws_dictionary import _normalize_hallucinated_title, _natural_sort_key
from app.api.endpoints.laws_pkg.laws_search_service import find_documents_by_title, find_law_documents, _generate_source_info

logger = logging.getLogger(__name__)
router = APIRouter()

# 1. SHKURTESAT ZYRTARE TË LIGJEVE TË KOSOVËS
LAW_ACRONYMS: Dict[str, str] = {
    "lmd": "Ligji për Marrëdhëniet e Detyrimeve",
    "lpk": "Ligji për Procedurën Kontestimore",
    "lpp": "Ligji për Procedurën Përmbarimore",
    "kpk": "Kodi Penal i Republikës së Kosovës",
    "kprk": "Kodi Penal i Republikës së Kosovës",
    "kpprk": "Kodi i Procedurës Penale",
    "lfk": "Ligji për Familjen i Kosovës",
    "lsht": "Ligji për Shoqëritë Tregtare",
    "lp": "Ligji i Punës",
}

CASE_NO_REGEX = re.compile(r'\b(REV|PML|PA1|A|CP|PKR|P|KMLP|ANR)\s*\.?\s*NR\s*\.?\s*(\d+[\w\/\.\-]*)', re.IGNORECASE)

ALBANIAN_STOP_WORDS = {
    "i", "e", "të", "te", "së", "se", "më", "me", "në", "ne", "nga", "për", "per", 
    "ndaj", "tek", "ku", "ka", "pa", "brenda", "para", "pas", "si", "ose", "dhe", 
    "po", "jo", "një", "nje", "çdo", "cdo", "këtë", "kete", "atij", "asaj", "keta",
    "keto", "derisa", "nuk", "eshte", "është", "jane", "janë", "ditor", "ditëve"
}

CIVIL_COMMERCIAL_ENFORCEMENT_INDICATORS = [
    "prapësim", "prapesim", "përmbarim", "permbarim", "urdhër përmbarimor", "urdher", 
    "kontrat", "qira", "dëmshpërblim", "demshperblim", "pasurim", "kamata", "kamate", 
    "ortak", "aksion", "shoqëri tregtare", "shoqeri", "fiduciar", "fajde", "detyrim", 
    "taksa gjyqesore", "shpenzime", "masë sigurimi", "masa e sigurimit", "autorizim", "prokur"
]

PENAL_INDICATORS = [
    "vepër penale", "veper penale", "vjedhje", "mashtrim", "vrasje", "paraburgim", 
    "dënim", "denim", "burgim", "armëmbajtje", "narkotik", "korrupsion", "keqpërdorim"
]


def _get_b2_filenames(prefix: str) -> List[str]:
    filenames = []
    try:
        s3 = storage_service.get_s3_client()
        bucket = storage_service.B2_BUCKET_NAME
        b2_response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
        for obj in b2_response.get('Contents', []):
            key = obj.get('Key', '')
            fname = os.path.basename(key)
            if fname and fname.lower().endswith('.pdf'):
                filenames.append(fname)
    except Exception as e:
        logger.warning(f"B2 list failed for prefix '{prefix}': {e}")
    return filenames


def _determine_legal_domain(query_lower: str) -> str:
    is_civil = any(ind in query_lower for ind in CIVIL_COMMERCIAL_ENFORCEMENT_INDICATORS)
    is_penal = any(ind in query_lower for ind in PENAL_INDICATORS)

    if is_civil and not is_penal:
        return "CIVIL_ENFORCEMENT"
    if is_penal and not is_civil:
        return "PENAL"
    return "GENERAL"


def _calculate_doc_relevance(doc: dict, meaningful_tokens: List[str], raw_query_lower: str, domain: str) -> int:
    score = 0
    law_title = str(doc.get("law_title", "")).lower()
    text = str(doc.get("text", "")).lower()

    # 1. DOMAIN FILTERING (BLOKIMI I KODIT PENAL KUR KËRKOHET CIVIL/PËRMBARIM)
    if domain == "CIVIL_ENFORCEMENT":
        if "penal" in law_title or "mitur" in law_title:
            return -1000  # ZERO & ELIMINO KODIN PENAL
        
        if "përmbarim" in raw_query_lower or "permbarim" in raw_query_lower or "prapësim" in raw_query_lower or "prapesim" in raw_query_lower:
            if "përmbarimore" in law_title or "permbarimore" in law_title or "04/l-139" in law_title or "04 l 139" in law_title:
                score += 300
            elif "kontestimore" in law_title:
                score += 80

    elif domain == "PENAL":
        if "kontestimore" in law_title or "detyrimeve" in law_title or "tregtare" in law_title:
            return -1000
        if "penal" in law_title:
            score += 200

    # 2. MATCHING I TOKENEVE TË VLEFSHME (PA STOP-WORDS)
    for token in meaningful_tokens:
        if token in law_title:
            score += 40
        if token in text:
            score += 15

    # 3. PËRPUTHJE ME FRAZA
    if "prapësim" in text or "prapesim" in text:
        score += 80
    if "urdhrit përmbarimor" in text or "urdhrit permbarimor" in text:
        score += 100

    return score


@router.post("/ai-semantic-search")
@router.get("/ai-semantic-search")
async def ai_semantic_law_search(
    query: str = Query(None),
    payload: Optional[Dict[str, Any]] = Body(None),
    current_user = Depends(get_current_user)
):
    user_query = query or (payload.get("query") if payload else "")
    if not user_query or not user_query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    clean_q = user_query.strip()
    raw_query_lower = clean_q.lower()
    
    try:
        from app.core.db import get_db_instance
        db = get_db_instance()

        # 1. TOKENIZIMI I PASTRUAR NGA STOP-WORDS
        raw_tokens = [w.lower() for w in re.findall(r'\w+', clean_q)]
        meaningful_tokens = [t for t in raw_tokens if len(t) >= 3 and t not in ALBANIAN_STOP_WORDS]
        
        domain = _determine_legal_domain(raw_query_lower)

        # 2. STATUTES RETRIEVAL WITH DOMAIN FILTER
        statute_regex_conditions = []
        for t in meaningful_tokens[:5]:
            statute_regex_conditions.append({"text": {"$regex": re.escape(t), "$options": "i"}})
            statute_regex_conditions.append({"law_title": {"$regex": re.escape(t), "$options": "i"}})

        statute_query = {
            "is_article": True,
            "article_number": {"$exists": True, "$ne": None, "$ne": ""},
            "$nor": [
                {"category": "caselaw"},
                {"is_case_law": True},
                {"source": {"$regex": "case_law|supreme", "$options": "i"}}
            ]
        }
        if statute_regex_conditions:
            statute_query["$or"] = statute_regex_conditions

        candidate_chunks = list(db.legal_knowledge_base.find(statute_query).limit(120))

        # PIKËZIMI DHE RENDITJA
        scored_docs: List[Tuple[int, dict]] = []
        for doc in candidate_chunks:
            score = _calculate_doc_relevance(doc, meaningful_tokens, raw_query_lower, domain)
            if score > 0:
                scored_docs.append((score, doc))

        scored_docs.sort(key=lambda x: x[0], reverse=True)

        seen_articles = set()
        matched_statutes = []

        for _, doc in scored_docs:
            law_t = doc.get("law_title") or "Ligji Zyrtar"
            art_num = str(doc.get("article_number", "")).strip()
            clean_num = re.sub(r'^[^\d]*', '', art_num)
            clean_num = clean_num.split()[0] if clean_num else art_num

            key = f"{law_t}_{clean_num}"
            if clean_num and key not in seen_articles and len(matched_statutes) < 6:
                seen_articles.add(key)
                raw_text = doc.get("text", "")
                snippet = (raw_text[:120] + '...') if len(raw_text) > 120 else raw_text

                matched_statutes.append({
                    "law_title": law_t,
                    "article_number": clean_num,
                    "explanation": snippet,
                    "confidence": 0.99
                })

        # 3. CASELAW RETRIEVAL WITH DOMAIN FILTER
        caselaw_query: Dict[str, Any] = {
            "$or": [
                {"category": "caselaw"},
                {"is_case_law": True},
                {"source": {"$regex": "case_law|supreme|PML|REV|PA1|PKR", "$options": "i"}},
                {"law_title": {"$regex": "Gjykata\\s+Supreme|PML|REV", "$options": "i"}}
            ]
        }

        if domain == "CIVIL_ENFORCEMENT":
            caselaw_query["$and"] = [
                {"source": {"$not": {"$regex": "PML|PA1|PKR|penal", "$options": "i"}}},
                {"law_title": {"$not": {"$regex": "PML|PA1|PKR|penal", "$options": "i"}}}
            ]
        elif domain == "PENAL":
            caselaw_query["$and"] = [
                {"$or": [
                    {"source": {"$regex": "PML|PA1|PKR|penal", "$options": "i"}},
                    {"law_title": {"$regex": "PML|PA1|PKR|penal", "$options": "i"}}
                ]}
            ]

        if meaningful_tokens:
            token_search = [{"text": {"$regex": re.escape(t), "$options": "i"}} for t in meaningful_tokens[:3]]
            if "$and" in caselaw_query:
                caselaw_query["$and"].append({"$or": token_search})
            else:
                caselaw_query["$and"] = [{"$or": token_search}]

        caselaw_chunks = list(db.legal_knowledge_base.find(caselaw_query).limit(10))
        if not caselaw_chunks:
            fallback_regex = "REV|civil" if domain == "CIVIL_ENFORCEMENT" else "PML|PA1" if domain == "PENAL" else "supreme"
            caselaw_chunks = list(db.legal_knowledge_base.find({
                "source": {"$regex": fallback_regex, "$options": "i"}
            }).limit(4))

        clean_caselaw = []
        seen_case_numbers = set()

        for c in caselaw_chunks:
            raw_text = c.get("text", "")
            raw_title = c.get("law_title", "")
            source_file = c.get("source", "")
            page_val = c.get("page") or c.get("page_number") or 1

            match = CASE_NO_REGEX.search(raw_text) or CASE_NO_REGEX.search(raw_title) or CASE_NO_REGEX.search(source_file)
            if match:
                case_tag = f"Gjykata Supreme • {match.group(0).upper().replace('  ', ' ')} (Faqja {page_val})"
            else:
                case_tag = raw_title if ("Supreme" in raw_title or "REV" in raw_title or "PML" in raw_title) else f"Gjykata Supreme (Faqja {page_val})"

            if case_tag not in seen_case_numbers and len(clean_caselaw) < 4:
                seen_case_numbers.add(case_tag)
                clean_caselaw.append({
                    "title": case_tag,
                    "source": source_file,
                    "page": page_val
                })

        # 4. KUALIFIKIMI JURIDIK ME LLM OSE DINAMIK
        legal_institute = "Procedura Përmbarimore dhe Mjetet Juridike (Prapësimi)" if domain == "CIVIL_ENFORCEMENT" else "Kualifikim Juridik i Zbatueshëm"
        plain_explanation = f"Kërkesa juaj rregullohet nga dispozitat e procedurës përkatëse në Republikën e Kosovës."

        if matched_statutes:
            legal_institute = f"Baza Ligjore: {matched_statutes[0]['law_title']}"
            plain_explanation = f"Çështja rregullohet nga Nenet e {matched_statutes[0]['law_title']} (shih nenet më poshtë)."

        try:
            from app.services.llm_service import llm_service
            system_prompt = (
                "Ti je Krye-Eksperti Juridik i Kosovës. Kthe VETËM JSON me këtë format:\n"
                "{\n"
                '  "legal_institute": "Instituti ligjor (p.sh. Procedura Përmbarimore dhe Prapësimi ndaj Urdhrit)",\n'
                '  "plain_explanation": "Shpjegim i thjeshtë me 1-2 fjali mbi afatet dhe mjetet juridike"\n'
                "}"
            )
            raw_llm = llm_service.generate_text(
                prompt=f"Kualifiko këtë situatë ligjore të Kosovës: \"{clean_q}\"",
                system_prompt=system_prompt
            )
            json_match = re.search(r'\{.*\}', raw_llm, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(0))
                legal_institute = parsed.get("legal_institute", legal_institute)
                plain_explanation = parsed.get("plain_explanation", plain_explanation)
        except Exception as llm_err:
            logger.warning(f"LLM diagnostic fallback: {llm_err}")

        return {
            "query": clean_q,
            "ai_diagnostic": {
                "legal_institute": legal_institute,
                "plain_explanation": plain_explanation,
                "matched_statutes": matched_statutes
            },
            "caselaw_precedents": clean_caselaw,
            "success": True
        }

    except Exception as e:
        logger.error(f"Error in dynamic ai_semantic_law_search: {e}")
        raise HTTPException(status_code=500, detail=f"Dynamic search error: {str(e)}")


@router.get("/case-page")
async def get_case_starting_page(law_title: str = Query(...), current_user = Depends(get_current_user)):
    try:
        from app.core.db import get_db_instance
        db = get_db_instance()
        clean_title = law_title.strip()

        doc = db.legal_knowledge_base.find_one(
            {"$or": [
                {"law_title": clean_title},
                {"law_title": {"$regex": re.escape(clean_title), "$options": "i"}},
                {"source": {"$regex": re.escape(clean_title), "$options": "i"}}
            ]},
            sort=[("page", 1)]
        )
        if doc:
            raw_page = doc.get("page") or doc.get("page_number") or 1
            try:
                page_val = int(raw_page)
            except Exception:
                page_val = 1
            return {"page": page_val, "page_number": page_val, "law_title": clean_title}
        return {"page": 1, "page_number": 1, "law_title": clean_title}
    except Exception as e:
        logger.warning(f"Error fetching starting page: {e}")
        return {"page": 1, "page_number": 1, "law_title": law_title}


@router.get("/titles")
async def get_law_titles(current_user = Depends(get_current_user)):
    try:
        from app.core.db import get_db_instance
        db = get_db_instance()
        
        # 1. AKADEMIA JURIDIKE
        academic_filter = {
            "$or": [
                {"category": "academic"},
                {"is_academic": True},
                {"source": {"$regex": "akademia|doracak|komentar", "$options": "i"}}
            ]
        }
        academic_db_sources = db.legal_knowledge_base.distinct("source", academic_filter)
        academic_db_titles = db.legal_knowledge_base.distinct("law_title", academic_filter)
        b2_academic = _get_b2_filenames("academic/")
        
        raw_academic_sources = set([
            s.strip() for s in (academic_db_sources + academic_db_titles + b2_academic) 
            if s and s.strip()
        ])
        clean_academic = sorted(list(raw_academic_sources))

        # 2. AKTGJYKIMET E GJYKATËS SUPREME
        caselaw_filter = {
            "$or": [
                {"category": "caselaw"},
                {"is_case_law": True},
                {"case_number": {"$exists": True, "$ne": None, "$ne": ""}},
                {"law_title": {"$regex": r"Gjykata\s+Supreme|PML|REV|PA1|PKR", "$options": "i"}}
            ]
        }
        caselaw_db_titles = db.legal_knowledge_base.distinct("law_title", caselaw_filter)
        caselaw_db_sources = db.legal_knowledge_base.distinct("source", caselaw_filter)
        b2_caselaw = _get_b2_filenames("case_law/")

        raw_caselaw = set([t.strip() for t in (caselaw_db_titles + caselaw_db_sources + b2_caselaw) if t and t.strip()])
        clean_caselaw = sorted(list(raw_caselaw))

        # 3. KODET DHE LIGJET STATUTORE (19 LIGJET E KOSOVËS)
        statutes_filter = {
            "is_article": True,
            "$nor": [
                {"category": "caselaw"},
                {"is_case_law": True},
                {"category": "academic"},
                {"is_academic": True},
                {"law_title": {"$regex": r"Gjykata\s+Supreme|PML|REV|PA1|PKR", "$options": "i"}}
            ]
        }
        all_statute_titles = db.legal_knowledge_base.distinct("law_title", statutes_filter)
        
        raw_statutes = []
        for t in all_statute_titles:
            t_clean = t.strip()
            if t_clean and not t_clean.lower().endswith('.pdf') and not CASE_NO_REGEX.search(t_clean) and "supreme" not in t_clean.lower():
                raw_statutes.append(t_clean)

        clean_statutes = sorted(list(set(raw_statutes)))

        return {
            "statutes": clean_statutes,
            "academic_manuals": clean_academic,
            "case_law": clean_caselaw,
            "all_titles": sorted(list(set(clean_statutes + clean_academic + clean_caselaw)))
        }
    except Exception as e:
        logger.error(f"Error fetching law titles: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching titles: {str(e)}")


@router.get("/library")
async def get_laws_library(
    q: Optional[str] = Query(None), 
    limit: int = Query(50, ge=1, le=200),
    current_user = Depends(get_current_user)
):
    try:
        if q and q.strip():
            return vector_store_service.query_global_knowledge_base(q.strip(), n_results=limit)
        return await get_law_titles(current_user=current_user)
    except Exception as e:
        logger.error(f"Error in /library endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Library error: {str(e)}")


@router.get("/by-title")
async def get_law_articles(law_title: str = Query(...), current_user = Depends(get_current_user)):
    try:
        from app.core.db import get_db_instance
        db = get_db_instance()
        
        clean_title = law_title.strip()
        clean_key = clean_title.lower()
        if clean_key in LAW_ACRONYMS:
            clean_title = LAW_ACRONYMS[clean_key]

        mapped_title = _normalize_hallucinated_title(clean_title, "")

        docs = find_documents_by_title(
            db, 
            mapped_title if mapped_title else clean_title, 
            fields={"law_title": 1, "article_number": 1, "source": 1, "chunk_index": 1, "page": 1, "page_number": 1, "text": 1}
        )

        if not docs:
            raise HTTPException(status_code=404, detail=f"Ligji '{law_title}' nuk u gjet në bazën e të dhënave.")
        
        canonical_title = docs[0].get("law_title", mapped_title if mapped_title else clean_title)

        articles: Set[str] = {str(d.get("article_number")) for d in docs if d.get("article_number") and str(d.get("article_number")) != ""}
        sorted_articles = sorted(list(articles), key=_natural_sort_key)
        
        raw_page = docs[0].get("page") or docs[0].get("page_number") or 1
        try:
            page_val = int(raw_page)
        except Exception:
            page_val = 1

        return {
            "law_title": canonical_title,
            "source": str(docs[0].get("source", "")),
            "page": page_val,
            "page_number": page_val,
            "is_official_statute": True,
            "article_count": len(sorted_articles),
            "articles": sorted_articles
        }
    except HTTPException: raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/article")
async def get_law_article(
    law_title: str = Query(...), 
    article_number: str = Query(...), 
    current_user = Depends(get_current_user)
):
    try:
        from app.core.db import get_db_instance
        db = get_db_instance()
        
        clean_law_title = law_title.strip()
        clean_art = str(article_number).strip()

        clean_key = clean_law_title.lower()
        if clean_key in LAW_ACRONYMS:
            clean_law_title = LAW_ACRONYMS[clean_key]

        if clean_law_title.lower().startswith("neni") or clean_law_title == clean_art or clean_law_title == "Ligji përkatës":
            fallback_doc = db.legal_knowledge_base.find_one({
                "article_number": clean_art,
                "is_article": True
            })
            if fallback_doc and fallback_doc.get("law_title"):
                clean_law_title = fallback_doc.get("law_title")

        try:
            statute_docs, academic_doc, metadata = find_law_documents(db, clean_law_title, clean_art)
        except Exception as find_err:
            logger.warning(f"find_law_documents warning: {find_err}")
            statute_docs, academic_doc, metadata = [], None, {}
        
        if not statute_docs or len(statute_docs) == 0:
            fallback_docs = list(db.legal_knowledge_base.find({
                "article_number": clean_art,
                "is_article": True
            }).limit(5))
            if fallback_docs:
                statute_docs = fallback_docs

        if not statute_docs or len(statute_docs) == 0 or not statute_docs[0]: 
            raise HTTPException(status_code=404, detail=f"Neni {clean_art} i ligjit '{clean_law_title}' nuk u gjet.")

        primary_doc = statute_docs[0]
        source_info = _generate_source_info(primary_doc, metadata or {}, clean_law_title, clean_art)

        raw_page = primary_doc.get("page") or primary_doc.get("page_number") or 1
        try:
            page_val = int(raw_page)
        except Exception:
            page_val = 1

        response_data = {
            "law_title": primary_doc.get("law_title", clean_law_title),
            "article_number": primary_doc.get("article_number", clean_art),
            "source": primary_doc.get("source", ""),
            "page": page_val,
            "page_number": page_val,
            "text": "\n\n".join([doc.get("text", "") for doc in statute_docs if doc and doc.get("text")]),
            "source_info": source_info
        }

        return response_data
    except HTTPException: raise
    except Exception as e: 
        logger.error(f"Article endpoint error handled: {e}")
        raise HTTPException(status_code=404, detail=f"Baza ligjore nuk u gjet: {str(e)}")


@router.get("/search")
async def search_laws(q: str = Query(...), limit: int = Query(50, ge=1, le=200), current_user = Depends(get_current_user)):
    try:
        return vector_store_service.query_global_knowledge_base(q, n_results=limit)
    except Exception as e: raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get(path="/{chunk_id}")
async def get_law_chunk(chunk_id: str, current_user = Depends(get_current_user)):
    try:
        from app.core.db import get_db_instance
        db = get_db_instance()
        doc = db.legal_knowledge_base.find_one({"chunk_id": chunk_id})
        if not doc: raise HTTPException(status_code=404, detail="Chunk not found")
            
        raw_page = doc.get("page") or doc.get("page_number") or 1
        try:
            page_val = int(raw_page)
        except Exception:
            page_val = 1

        return {
            "law_title": str(doc.get("law_title", "Ligji")),
            "article_number": str(doc.get("article_number", "")),
            "source": str(doc.get("source", "")),
            "page": page_val,
            "page_number": page_val,
            "text": doc.get("text", "")
        }
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")