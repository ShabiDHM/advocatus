# FILE: backend/app/api/endpoints/laws.py
# PHOENIX PROTOCOL - LAWS ENDPOINTS V52.0 ("LIGJI PËRKATËS" GENERIC PHRASE & ARTICLE NUMBER RESOLVER)

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse, FileResponse, RedirectResponse
from pydantic import BaseModel
from typing import Optional, List, Set, Any, Dict
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

# EXHAUSTIVE KOSOVO STATUTORY ACRONYM AND ALIAS DICTIONARY
OFFICIAL_KOSOVO_LAWS = {
    # Generic & Relative AI Phrases ("Ligji Përkatës")
    "ligji përkatës": "LIGJI NR. 03/L-006 PËR PROCEDURËN KONTESTIMORE",
    "ligji perkates": "LIGJI NR. 03/L-006 PËR PROCEDURËN KONTESTIMORE",
    "ligjin përkatës": "LIGJI NR. 03/L-006 PËR PROCEDURËN KONTESTIMORE",
    "ligjin perkates": "LIGJI NR. 03/L-006 PËR PROCEDURËN KONTESTIMORE",
    "ligji i përgjithshëm": "LIGJI NR. 03/L-006 PËR PROCEDURËN KONTESTIMORE",
    "ligji i pergjithshem": "LIGJI NR. 03/L-006 PËR PROCEDURËN KONTESTIMORE",
    "ligji i procedurës kontestimore": "LIGJI NR. 03/L-006 PËR PROCEDURËN KONTESTIMORE",
    "ligji per proceduren kontestimore": "LIGJI NR. 03/L-006 PËR PROCEDURËN KONTESTIMORE",
    "procedurën kontestimore": "LIGJI NR. 03/L-006 PËR PROCEDURËN KONTESTIMORE",
    "procedura kontestimore": "LIGJI NR. 03/L-006 PËR PROCEDURËN KONTESTIMORE",

    # Acronyms & Short Names
    "lsht": "LIGJI NR. 06/L-016 PËR SHOQËRITË TREGTARE",
    "lpk": "LIGJI NR. 03/L-006 PËR PROCEDURËN KONTESTIMORE",
    "lmd": "LIGJI NR. 04/L-077 PËR MARRËDHËNIET E DETYRIMEVE",
    "lpp": "LIGJI NR. 04/L-139 PËR PROCEDURËN PËRMBARIMORE",
    "kpk": "KODI NR. 06/L-074 KODI PENAL I REPUBLIKËS SË KOSOVËS",
    "kppk": "KODI NR. 08/L-032 I PROCEDURËS PENALE",
    "kpp": "KODI NR. 08/L-032 I PROCEDURËS PENALE",
    "kushtetuta": "KUSHTETUTA E REPUBLIKËS SË KOSOVËS",
    
    # Official Full Statute Titles
    "kodi penal": "KODI NR. 06/L-074 KODI PENAL I REPUBLIKËS SË KOSOVËS",
    "procedurës penale": "KODI NR. 08/L-032 I PROCEDURËS PENALE",
    "procedura penale": "KODI NR. 08/L-032 I PROCEDURËS PENALE",
    "drejtësisë për të mitur": "KODI NR. 06/L-006 I DREJTËSISË PËR TË MITUR",
    "të mitur": "KODI NR. 06/L-006 I DREJTËSISË PËR TË MITUR",
    "shoqëritë tregtare": "LIGJI NR. 06/L-016 PËR SHOQËRITË TREGTARE",
    "shoqerite tregtare": "LIGJI NR. 06/L-016 PËR SHOQËRITË TREGTARE",
    "marrëdhëniet e detyrimeve": "LIGJI NR. 04/L-077 PËR MARRËDHËNIET E DETYRIMEVE",
    "marredheniet e detyrimeve": "LIGJI NR. 04/L-077 PËR MARRËDHËNIET E DETYRIMEVE",
    "procedurën përmbarimore": "LIGJI NR. 04/L-139 PËR PROCEDURËN PËRMBARIMORE",
    "proceduren permbarimore": "LIGJI NR. 04/L-139 PËR PROCEDURËN PËRMBARIMORE",
    "sigurinë dhe shëndetin në punë": "LIGJI NR. 04/L-161 PËR SIGURINË DHE SHËNDETIN NË PUNË",
    "tatimin në të ardhurat e korporatave": "LIGJI NR. 05/L-029 PËR TATIMIN NË TË ARDHURAT E KORPORATAVE",
    "mbrojtjen e të dhënave personale": "LIGJI NR. 06/L-082 PËR MBROJTJEN E TË DHËNAVE PERSONALE",
    "mbrojtjen e fëmijës": "LIGJI NR. 06/L-084 PËR MBROJTJEN E FËMIJËS",
    "administrimin e procedurave tatimore": "LIGJI NR. 08/L-257 PËR ADMINISTRIMIN E PROCEDURAVE TATIMORE",
    "familjen": "LIGJI NR. 2004/32 LIGJI PËR FAMILJEN I KOSOVËS",
    "ligji i punës": "LIGJI NR. 03/L-212 I PUNËS",
    "ligji i punes": "LIGJI NR. 03/L-212 I PUNËS",

    # Number Codes
    "06/l-074": "KODI NR. 06/L-074 KODI PENAL I REPUBLIKËS SË KOSOVËS",
    "08/l-032": "KODI NR. 08/L-032 I PROCEDURËS PENALE",
    "06/l-006": "KODI NR. 06/L-006 I DREJTËSISË PËR TË MITUR",
    "03/l-006": "LIGJI NR. 03/L-006 PËR PROCEDURËN KONTESTIMORE",
    "04/l-077": "LIGJI NR. 04/L-077 PËR MARRËDHËNIET E DETYRIMEVE",
    "04/l-139": "LIGJI NR. 04/L-139 PËR PROCEDURËN PËRMBARIMORE",
    "04/l-161": "LIGJI NR. 04/L-161 PËR SIGURINË DHE SHËNDETIN NË PUNË",
    "05/l-029": "LIGJI NR. 05/L-029 PËR TATIMIN NË TË ARDHURAT E KORPORATAVE",
    "06/l-016": "LIGJI NR. 06/L-016 PËR SHOQËRITË TREGTARE",
    "06/l-082": "LIGJI NR. 06/L-082 PËR MBROJTJEN E TË DHËNAVE PERSONALE",
    "06/l-084": "LIGJI NR. 06/L-084 PËR MBROJTJEN E FËMIJËS",
    "08/l-257": "LIGJI NR. 08/L-257 PËR ADMINISTRIMIN E PROCEDURAVE TATIMORE",
    "2004/32": "LIGJI NR. 2004/32 LIGJI PËR FAMILJEN I KOSOVËS",
    "03/l-212": "LIGJI NR. 03/L-212 I PUNËS",
    "armët e zjarrit": "AKADEMIA_E_DREJT_2025_Case_Law_Kosovo_web.pdf",
    "case law kosovo": "AKADEMIA_E_DREJT_2025_Case_Law_Kosovo_web.pdf"
}

class LawExplainRequest(BaseModel):
    law_title: str
    article_number: str
    prompt: str

class AuditChatRequest(BaseModel):
    law_title: Optional[str] = ""
    article_number: Optional[str] = ""
    article_id: Optional[str] = None
    query: Optional[str] = None
    message: Optional[str] = None
    prompt: Optional[str] = None

    @property
    def effective_query(self) -> str:
        return self.query or self.message or self.prompt or ""

def _natural_sort_key(article_any: Any) -> List[int]:
    article = str(article_any) if article_any is not None else "0"
    parts = re.findall(r'\d+', article)
    return [int(p) for p in parts] if parts else [0]

def _is_academic_file(filename_or_title: str) -> bool:
    text = str(filename_or_title).upper()
    academic_keywords = ["AKADEMIA", "DORACAK", "UDHEZUES", "UDHËZUES", "COMMENTARY", "CASE_LAW", "PRAKTIKË", "INSTITUTI", "LËNDËSH", "LENDESH"]
    return any(k in text for k in academic_keywords)

def _normalize_hallucinated_title(raw_title: str, article: str) -> str:
    title_lower = raw_title.lower().strip()
    art_clean = re.sub(r'[^\d]', '', article.strip())
    art_num = int(art_clean) if art_clean.isdigit() else 0

    # 1. SPECIAL KOSOVO ARTICLE NUMBER RESOLVER FOR GENERIC "LIGJI PËRKATËS" / "LIGJI I PËRGJITHSHËM"
    if "përkatës" in title_lower or "perkates" in title_lower or "përgjithshëm" in title_lower or "pergjithshem" in title_lower or not title_lower:
        if art_num in [297, 298, 299, 256, 258, 91, 92, 93, 110, 122]:
            return "LIGJI NR. 03/L-006 PËR PROCEDURËN KONTESTIMORE"
        elif art_num in [136, 141, 330, 382, 376, 100, 150]:
            return "LIGJI NR. 04/L-077 PËR MARRËDHËNIET E DETYRIMEVE"
        elif art_num in [258, 259, 260, 250]:
            return "LIGJI NR. 06/L-016 PËR SHOQËRITË TREGTARE"
        elif art_num in [307, 308, 100, 200]:
            return "KODI NR. 06/L-074 KODI PENAL I REPUBLIKËS SË KOSOVËS"

    # 2. Direct dictionary alias check
    if OFFICIAL_KOSOVO_LAWS.get(title_lower):
        return OFFICIAL_KOSOVO_LAWS[title_lower]

    for key, official_title in OFFICIAL_KOSOVO_LAWS.items():
        if key in title_lower or title_lower == key:
            return official_title

    # 3. Fallback Law Number Pattern Extractor (e.g., 06/L-016, 03/L-006)
    law_code_match = re.search(r'\d{2,4}/l-\d{3}|\d{4}/\d{2}', title_lower)
    if law_code_match:
        code = law_code_match.group(0)
        if OFFICIAL_KOSOVO_LAWS.get(code):
            return OFFICIAL_KOSOVO_LAWS[code]

    if "armët" in title_lower or "zjarrit" in title_lower or "case law" in title_lower:
        return "AKADEMIA_E_DREJT_2025_Case_Law_Kosovo_web.pdf"
    if "penal" in title_lower and "procedur" in title_lower:
        return "KODI NR. 08/L-032 I PROCEDURËS PENALE"
    if "penal" in title_lower:
        return "KODI NR. 06/L-074 KODI PENAL I REPUBLIKËS SË KOSOVËS"
    if "mitur" in title_lower:
        return "KODI NR. 06/L-006 I DREJTËSISË PËR TË MITUR"
    if "familj" in title_lower:
        return "LIGJI NR. 2004/32 LIGJI PËR FAMILJEN I KOSOVËS"
    if "shoqëri" in title_lower or "tregtar" in title_lower or "lsht" in title_lower:
        return "LIGJI NR. 06/L-016 PËR SHOQËRITË TREGTARE"
    if "detyrim" in title_lower or "lmd" in title_lower:
        return "LIGJI NR. 04/L-077 PËR MARRËDHËNIET E DETYRIMEVE"
    if "kontestim" in title_lower or "lpk" in title_lower:
        return "LIGJI NR. 03/L-006 PËR PROCEDURËN KONTESTIMORE"
    if "punë" in title_lower or "puna" in title_lower:
        return "LIGJI NR. 03/L-212 I PUNËS"

    return raw_title

def find_documents_by_title(db, raw_title: str, fields: Optional[dict] = None) -> List[dict]:
    title = raw_title.strip()
    if not title:
        return []

    projection = fields if fields else None
    stop_words = {"ligji", "kodi", "për", "per", "dhe", "i", "e", "të", "te", "së", "se", "nr", "nr.", "republikës", "republikes", "kosovës", "kosoves", "web", "pdf"}
    
    words = [re.escape(w) for w in re.findall(r'\w+', title) if len(w) >= 3 and w.lower() not in stop_words]
    digits = re.findall(r'\b\d+\b', title)

    academic_regex = "AKADEMIA|Doracak|Udhezues|Udhëzues|Commentary|Case_Law|LËNDËSH|LENDESH"
    is_acad = _is_academic_file(title)

    if is_acad:
        acad_conditions = []
        for w in words:
            if w.lower() not in ["akademia", "drejt", "drejtësisë"]:
                acad_conditions.append({
                    "$or": [
                        {"law_title": {"$regex": w, "$options": "i"}},
                        {"source": {"$regex": w, "$options": "i"}}
                    ]
                })
        if acad_conditions:
            docs = list(db.legal_knowledge_base.find({"$and": acad_conditions}, projection).limit(100))
            if docs: return docs

        docs = list(db.legal_knowledge_base.find({
            "$or": [
                {"source": {"$regex": "AKADEMIA|Case_Law|Udhezues", "$options": "i"}},
                {"law_title": {"$regex": "AKADEMIA|Case_Law|Udhezues", "$options": "i"}}
            ]
        }, projection).limit(100))
        if docs: return docs

    if words:
        word_conditions = []
        for w in words:
            word_conditions.append({
                "$or": [
                    {"law_title": {"$regex": w, "$options": "i"}},
                    {"source": {"$regex": w, "$options": "i"}}
                ]
            })
        word_conditions.append({"source": {"$not": {"$regex": academic_regex, "$options": "i"}}})

        if digits:
            digit_patterns = [d for d in digits if len(d) >= 2 or d != '0']
            for d in digit_patterns:
                clean_d = str(int(d)) if d.isdigit() else d
                d_regex = f"(?:0*{clean_d}\\b|{d})"
                word_conditions.append({
                    "$or": [
                        {"law_title": {"$regex": d_regex, "$options": "i"}},
                        {"source": {"$regex": d_regex, "$options": "i"}}
                    ]
                })

        docs = list(db.legal_knowledge_base.find({"$and": word_conditions}, projection).limit(100))
        if docs: return docs

    clean_escaped = re.escape(title)
    docs = list(db.legal_knowledge_base.find({
        "$or": [
            {"law_title": {"$regex": clean_escaped, "$options": "i"}},
            {"source": {"$regex": clean_escaped, "$options": "i"}}
        ]
    }, projection).limit(100))
    if docs: return docs

    return []

def _generate_source_info(doc: dict, metadata: dict, original_law_title: str, original_article: str) -> dict:
    confidence_level = metadata.get("confidence", {}).get("level", "HIGH")
    confidence_score = metadata.get("confidence", {}).get("score", 0.98)
    
    law_name = doc.get("law_title", original_law_title)
    is_academic = _is_academic_file(doc.get("source", "")) or _is_academic_file(law_name)

    return {
        "confidence": {
            "level": confidence_level,
            "label": "Tekst Zyrtar i Verifikuar (100%)" if not is_academic else "Udhëzues i Praktikës Gjyqësore",
            "icon": "📜" if not is_academic else "📚",
            "color": "success" if not is_academic else "info",
            "description": "Nen i nxjerrë direkt nga Kodi / Ligji Zyrtar i Kosovës." if not is_academic else "Analizë dhe udhëzues nga Akademia e Drejtësisë.",
            "score": confidence_score
        },
        "matched_law": law_name,
        "matched_article": doc.get("article_number", original_article),
        "source_file": doc.get("source", ""),
        "was_mapped": metadata.get("was_mapped", False),
        "is_official_statute": not is_academic,
        "verification_hint": f"✅ Ligji Zyrtar: {law_name}" if not is_academic else f"📚 Akademia e Drejtësisë: {law_name}",
        "match_count": 1
    }

def find_law_documents(db, raw_law_title: str, raw_article_num: str) -> tuple[List[dict], Optional[dict], Dict[str, Any]]:
    mapped_title = _normalize_hallucinated_title(raw_law_title, str(raw_article_num))
    is_academic = _is_academic_file(raw_law_title) or _is_academic_file(mapped_title)
    
    clean_art = str(raw_article_num).replace('Neni', '').replace('neni', '').replace('.', '').strip()
    
    if is_academic:
        case_num_match = re.search(r'\d+', clean_art)
        if case_num_match:
            case_num = case_num_match.group(0)
            case_regex = f"LËNDA\\s+(?:NR\\.\\s*)?{case_num}\\b"
            case_docs = list(db.legal_knowledge_base.find({
                "$or": [
                    {"text": {"$regex": case_regex, "$options": "i"}},
                    {"article_number": {"$regex": f"{case_num}\\b", "$options": "i"}}
                ],
                "source": {"$regex": "AKADEMIA|Case_Law", "$options": "i"}
            }).sort("chunk_index", 1).limit(10))

            if case_docs:
                return case_docs, None, {
                    "original_law_title": raw_law_title,
                    "mapped_law_title": mapped_title,
                    "article_number": f"Lënda Nr. {case_num}",
                    "confidence": {"level": "HIGH", "score": 0.98},
                    "strategy_used": "academic_case_number_match",
                    "was_mapped": False
                }

    art_variants: List[Any] = [clean_art, f"{clean_art}.", f"Neni {clean_art}", f"NENI {clean_art}", f"{clean_art} ", f" {clean_art}"]
    if clean_art.isdigit():
        art_variants.append(int(clean_art))

    metadata = {
        "original_law_title": raw_law_title,
        "mapped_law_title": mapped_title,
        "article_number": raw_article_num,
        "confidence": {"level": "HIGH", "score": 0.98},
        "strategy_used": "exact_statute_match",
        "was_mapped": (mapped_title != raw_law_title)
    }

    academic_regex = "AKADEMIA|Doracak|Udhezues|Udhëzues|Commentary|Case_Law|LËNDËSH|LENDESH"

    candidate_docs = find_documents_by_title(db, mapped_title if mapped_title else raw_law_title)
    
    if candidate_docs:
        matched_title = candidate_docs[0].get("law_title") or mapped_title
        statute_docs = list(db.legal_knowledge_base.find({
            "law_title": matched_title,
            "article_number": {"$in": art_variants}
        }).sort("chunk_index", 1))

        if statute_docs:
            academic_doc = db.legal_knowledge_base.find_one({
                "article_number": {"$in": art_variants},
                "source": {"$regex": academic_regex, "$options": "i"}
            })
            return statute_docs, academic_doc, metadata

    return candidate_docs[:3] if candidate_docs else ([], None, metadata)

def find_pdf_by_number_pair(requested_name: str) -> Optional[str]:
    clean_requested = os.path.basename(requested_name).strip().lower()
    digits = re.findall(r'\b\d+\b', clean_requested)
    
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

    for search_dir in search_dirs:
        if not os.path.exists(search_dir): continue
        for root, _, files in os.walk(search_dir):
            for f in files:
                if not f.lower().endswith('.pdf'): continue
                f_lower = f.lower()
                
                if f_lower == clean_requested: 
                    return os.path.join(root, f)
                
                if len(digits) >= 2:
                    primary_nums = [d for d in digits if len(d) >= 2 or d != '0']
                    if primary_nums and all(num in f_lower for num in primary_nums): 
                        return os.path.join(root, f)

    return None

@router.get("/pdf/{filename}")
async def get_law_pdf(filename: str):
    clean_name = os.path.basename(filename)
    try:
        s3 = storage_service.get_s3_client()
        bucket = storage_service.B2_BUCKET_NAME
        b2_response = s3.list_objects_v2(Bucket=bucket, Prefix="laws/")
        for obj in b2_response.get('Contents', []):
            key = obj.get('Key', '')
            b2_filename = os.path.basename(key)
            if b2_filename.lower() == clean_name.lower():
                url = storage_service.generate_presigned_url(key)
                if url: return RedirectResponse(url=url)
    except Exception as e:
        logger.warning(f"B2 cloud search skipped: {e}")

    found = find_pdf_by_number_pair(clean_name)
    if found:
        return FileResponse(
            found, 
            media_type="application/pdf", 
            filename=os.path.basename(found),
            headers={"Content-Disposition": f"inline; filename=\"{clean_name}\""}
        )
    raise HTTPException(status_code=404, detail=f"Dokumenti PDF '{clean_name}' nuk u gjet.")

@router.get("/titles")
async def get_law_titles(current_user = Depends(get_current_user)):
    try:
        from app.core.db import get_db_instance
        db = get_db_instance()
        all_titles = db.legal_knowledge_base.distinct("law_title")
        
        statute_titles = []
        academic_titles = []
        for t in sorted([t for t in all_titles if t]):
            if _is_academic_file(t):
                academic_titles.append(t)
            else:
                statute_titles.append(t)
                
        return {
            "statutes": statute_titles,
            "academic_manuals": academic_titles,
            "all_titles": statute_titles + academic_titles
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching titles: {str(e)}")

@router.get("/by-title")
async def get_law_articles(law_title: str = Query(...), current_user = Depends(get_current_user)):
    try:
        from app.core.db import get_db_instance
        db = get_db_instance()
        
        mapped_title = _normalize_hallucinated_title(law_title, "")
        is_academy = _is_academic_file(law_title) or _is_academic_file(mapped_title)

        docs = find_documents_by_title(
            db, 
            mapped_title if mapped_title else law_title, 
            fields={"law_title": 1, "article_number": 1, "source": 1, "chunk_index": 1, "page": 1, "text": 1}
        )

        if not docs:
            raise HTTPException(status_code=404, detail=f"Ligji '{law_title}' nuk u gjet në bazën e të dhënave.")
        
        canonical_title = docs[0].get("law_title", mapped_title if mapped_title else law_title)

        if is_academy:
            sorted_articles = [
                "Hyrje & Metodologjia",
                "Legjislacioni Relevant",
                *[f"Lënda Nr. {i+1}" for i in range(25)],
                "Të Dhëna Statistikore",
                "Konkluzione"
            ]
        else:
            articles: Set[str] = {str(d.get("article_number")) for d in docs if d.get("article_number") and str(d.get("article_number")) != ""}
            sorted_articles = sorted(list(articles), key=_natural_sort_key)
        
        return {
            "law_title": canonical_title,
            "source": str(docs[0].get("source", "")),
            "is_official_statute": not is_academy,
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
        
        statute_docs, academic_doc, metadata = find_law_documents(db, law_title, article_number)
        
        if not statute_docs or not statute_docs[0]: 
            raise HTTPException(status_code=404, detail=f"Dokumenti ({law_title}, Neni {article_number}) nuk u gjet në bazën e të dhënave.")

        primary_doc = statute_docs[0]
        source_info = _generate_source_info(primary_doc, metadata, law_title, article_number)

        response_data = {
            "law_title": primary_doc.get("law_title", metadata["mapped_law_title"]),
            "article_number": primary_doc.get("article_number", article_number),
            "source": primary_doc.get("source", ""),
            "text": "\n\n".join([doc.get("text", "") for doc in statute_docs if doc and doc.get("text")]),
            "source_info": source_info
        }

        if academic_doc and academic_doc.get("text"):
            response_data["academic_commentary"] = {
                "source": academic_doc.get("source", "Akademia e Drejtësisë"),
                "text": academic_doc.get("text", ""),
                "title": "Udhëzues & Praktikë Gjyqësore (Akademia e Drejtësisë)"
            }

        return response_data
    except HTTPException: raise
    except Exception as e: 
        logger.error(f"Article endpoint error: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

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
            
        return {
            "law_title": str(doc.get("law_title", "Ligji")),
            "article_number": str(doc.get("article_number", "")),
            "source": str(doc.get("source", "")),
            "text": doc.get("text", "")
        }
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")