# FILE: backend/app/api/endpoints/laws.py
# PHOENIX PROTOCOL - LAWS ENDPOINTS V32.0 (HIGH-ACCURACY RESOLVED RESOLUTION MATCHING)

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

def _safe_int(value: Any) -> int:
    if value is None: return 0
    try: return int(value)
    except (ValueError, TypeError): return 0

def _natural_sort_key(article_any: Any) -> List[int]:
    article = str(article_any) if article_any is not None else "0"
    parts = article.split('.')
    return [int(p) for p in parts if p.isdigit()]

def _get_law_code_variations(raw_title: str) -> List[str]:
    """Extract law code and generate multiple variations for matching."""
    variations = set()
    
    # Extract the law code pattern
    law_num_match = re.search(r'\b(\d{2,4})\s*[\/\-]?\s*[L]?\s*[\/\-]?\s*(\d{1,4}[-]?\d*)\b', raw_title, re.I)
    if law_num_match:
        num_part = law_num_match.group(1)
        rest_part = law_num_match.group(2)
        
        # Generate variations with different separators
        # Database format: "03 L-006" (space)
        variations.add(f"{num_part} L-{rest_part}")
        variations.add(f"{num_part} L-{rest_part}".replace('  ', ' '))
        
        # Request format: "03/L-006" (slash)
        variations.add(f"{num_part}/L-{rest_part}")
        
        # Other common formats
        variations.add(f"{num_part}/{rest_part}")
        variations.add(f"{num_part}-{rest_part}")
        variations.add(f"{num_part} {rest_part}")
        variations.add(f"0{num_part}/L-{rest_part}")  # Some have leading 0
        
        # Clean versions (without "L-")
        variations.add(f"{num_part}/{rest_part}")
        variations.add(f"{num_part}-{rest_part}")
        variations.add(f"{num_part} {rest_part}")
    
    # Also try matching numeric parts only
    numbers = re.findall(r'\b\d+\b', raw_title)
    if len(numbers) >= 2:
        variations.add(' '.join(numbers))
        variations.add('-'.join(numbers))
        variations.add('/'.join(numbers))
    
    # Remove duplicates and empty strings
    result = [v for v in variations if v]
    logger.debug(f"Generated {len(result)} law code variations: {result}")
    return result

def _generate_source_info(doc: dict, metadata: dict, original_law_title: str, original_article: str) -> dict:
    """
    Generate user-friendly source information.
    This is what the user sees to build trust and transparency.
    """
    
    confidence_level = metadata.get("confidence", {}).get("level", "UNKNOWN")
    confidence_score = metadata.get("confidence", {}).get("score", 0.0)
    
    # User-friendly confidence labels
    confidence_labels = {
        "HIGH": {
            "label": "E verifikuar",
            "icon": "✅",
            "color": "success",
            "description": "Ky nen u gjet me saktësi në ligjin e specifikuar."
        },
        "MEDIUM": {
            "label": "Përputhje e mundshme",
            "icon": "🔍",
            "color": "warning",
            "description": "Ky nen u gjet në një ligj që lidhet me kërkimin tuaj."
        },
        "LOW": {
            "label": "Kërkon verifikim",
            "icon": "⚠️",
            "color": "danger",
            "description": "Ky nen u gjet në disa ligje. Ju lutemi verifikoni nëse është i saktë."
        },
        "LOWEST": {
            "label": "Kërkon verifikim",
            "icon": "⚠️",
            "color": "danger",
            "description": "Përputhja është e pjesshme. Ju lutemi verifikoni me burimin zyrtar."
        },
        "NONE": {
            "label": "Nuk u gjet",
            "icon": "❌",
            "color": "danger",
            "description": "Neni nuk u gjet në asnjë ligj."
        }
    }
    
    confidence_info = confidence_labels.get(confidence_level, confidence_labels["LOW"])
    
    # Generate verification hint based on confidence and metadata
    verification_hint = ""
    if confidence_level == "HIGH":
        verification_hint = "✅ Ky nen korrespondon saktësisht me kërkimin tuaj."
    elif confidence_level == "MEDIUM":
        verification_hint = "🔍 Ky nen lidhet me kërkimin tuaj. Verifikoni nëse ligji është i zbatueshëm për rastin tuaj."
    elif confidence_level == "LOW" and metadata.get("multiple_matches"):
        matching_laws = metadata.get("matching_laws", [])
        if matching_laws:
            verification_hint = f"⚠️ Ky nen u gjet në {len(matching_laws)} ligje të ndryshme. Kontrolloni që ligji i zgjedhur është i saktë për rastin tuaj."
        else:
            verification_hint = "⚠️ Ky nen kërkon verifikim me burimin zyrtar."
    else:
        verification_hint = "📋 Ju lutemi verifikoni këtë informacion me burimin zyrtar."
    
    return {
        "confidence": {
            "level": confidence_level,
            "label": confidence_info["label"],
            "icon": confidence_info["icon"],
            "color": confidence_info["color"],
            "description": confidence_info["description"],
            "score": round(confidence_score, 2)
        },
        "matched_law": doc.get("law_title", original_law_title),
        "matched_article": doc.get("article_number", original_article),
        "source_file": doc.get("source", ""),
        "was_mapped": metadata.get("was_mapped", False),
        "mapped_from": metadata.get("original_law_title") if metadata.get("was_mapped") else None,
        "multiple_matches": metadata.get("multiple_matches", False),
        "matching_laws": metadata.get("matching_laws", []),
        "strategy_used": metadata.get("strategy_used", "unknown"),
        "verification_hint": verification_hint,
        "match_count": metadata.get("match_count", 0)
    }

def find_law_documents(db, raw_law_title: str, raw_article_num: str) -> tuple[List[dict], Dict[str, Any]]:
    """
    Find law documents with confidence scoring.
    Supports dual integer/string database matching and trailing whitespace resilience.
    """
    # === 1. PREFIX & SUFFIX NORMALIZATION PIPELINE ===
    clean_title = raw_law_title.strip()
    # Strip leading periods, numbers, and spaces (e.g. ".3 LPK" -> "LPK", "3 KPK" -> "KPK")
    clean_title = re.sub(r'^[.\d\s]+', '', clean_title)
    # Strip common preposition prefixes
    clean_title = re.sub(r'^(?:i|e|të|sipas|në|nga|për|per)\s+', '', clean_title, flags=re.I)
    # Strip common possessive/definite suffixes (e.g. "LPK-së" -> "LPK", "LMD-së" -> "LMD")
    clean_title = re.sub(r'[-](?:së|it|at|ut|ën|ës|in)\b', '', clean_title, flags=re.I)
    clean_title = clean_title.strip()

    # === 2. COMPREHENSIVE MAPPING & ACRONYMS ===
    law_title_mappings = {
        # === ACCURATE ALBANIAN ACRONYMS ===
        'LPK': 'Ligji Nr. 03 L-006 Për Procedurën Kontestimore',
        'LMD': 'Ligji Nr. 04 L-077 Për Marrëdhëniet E Detyrimeve',
        'KPK': 'Kodi Nr. 06 L-074 Kodi Penal I Republikës Së Kosovës',
        'KPPK': 'Kodi Nr. 08 L-032 I Procedurës Penale',
        'LPA': 'Ligji Nr. 04 L-189 Për Procedurën Administrative',
        'LPP': 'Ligji Nr. 03 L-006 Për Procedurën Kontestimore',
        'KPC': 'Kodi I Procedurës Civile',

        # === CONSTITUTIONAL PRINCIPLES ===
        'KUSHTETUTA': 'Kushtetuta E Republikës Së Kosovës',
        'KUSHTETUTËN': 'Kushtetuta E Republikës Së Kosovës',
        'KUSHTETUTËS': 'Kushtetuta E Republikës Së Kosovës',
        '(BARAZIA PARA LIGJIT)': 'Kushtetuta E Republikës Së Kosovës',
        'BARAZIA PARA LIGJIT': 'Kushtetuta E Republikës Së Kosovës',
        '(BARAZIA)': 'Kushtetuta E Republikës Së Kosovës',
        'BARAZIA': 'Kushtetuta E Republikës Së Kosovës',
        '(LIRIA E SHPREHJES)': 'Kushtetuta E Republikës Së Kosovës',
        '(E DREJTA E PRONËS)': 'Kushtetuta E Republikës Së Kosovës',
        '(E DREJTA E PUNËS)': 'Kushtetuta E Republikës Së Kosovës',
        
        # === TOPICS ===
        '(GJOBAT)': 'Ligji Nr. 04 L-077 Për Marrëdhëniet E Detyrimeve',
        'GJOBAT': 'Ligji Nr. 04 L-077 Për Marrëdhëniet E Detyrimeve',
        '(GJOBA)': 'Ligji Nr. 04 L-077 Për Marrëdhëniet E Detyrimeve',
        'GJOBA': 'Ligji Nr. 04 L-077 Për Marrëdhëniet E Detyrimeve',
        '(DETYRIMET)': 'Ligji Nr. 04 L-077 Për Marrëdhëniet E Detyrimeve',
        'DETYRIMET': 'Ligji Nr. 04 L-077 Për Marrëdhëniet E Detyrimeve',
        '(KONTRATAT)': 'Ligji Nr. 04 L-077 Për Marrëdhëniet E Detyrimeve',
        '(DËMSHPËRBLIMI)': 'Ligji Nr. 04 L-077 Për Marrëdhëniet E Detyrimeve',
        '(KAMATA)': 'Ligji Nr. 04 L-077 Për Marrëdhëniet E Detyrimeve',
        '(DËMI)': 'Ligji Nr. 04 L-077 Për Marrëdhëniet E Detyrimeve',
        
        # === SECTION HEADINGS ===
        '(DISPOZITAT KALIMTARE)': 'Ligji Nr. 03 L-006 Për Procedurën Kontestimore',
        'DISPOZITAT KALIMTARE': 'Ligji Nr. 03 L-006 Për Procedurën Kontestimore',
        '(DISPOZITAT)': 'Ligji Nr. 03 L-006 Për Procedurën Kontestimore',
        'DISPOZITAT': 'Ligji Nr. 03 L-006 Për Procedurën Kontestimore',
        '(DISPOZITA)': 'Ligji Nr. 03 L-006 Për Procedurën Kontestimore',
        'DISPOZITA': 'Ligji Nr. 03 L-006 Për Procedurën Kontestimore',
        '(DISPOZITAT FINALE)': 'Ligji Nr. 03 L-006 Për Procedurën Kontestimore',
        'DISPOZITAT FINALE': 'Ligji Nr. 03 L-006 Për Procedurën Kontestimore',
        '(DISPOZITAT E PËRGJITHSHME)': 'Ligji Nr. 03 L-006 Për Procedurën Kontestimore',
        'DISPOZITAT E PËRGJITHSHME': 'Ligji Nr. 03 L-006 Për Procedurën Kontestimore',
        
        # === LEGAL CONCEPTS ===
        '(NULITETI I DISPOZITAVE)': 'Ligji Nr. 04 L-077 Për Marrëdhëniet E Detyrimeve',
        'NULITETI I DISPOZITAVE': 'Ligji Nr. 04 L-077 Për Marrëdhëniet E Detyrimeve',
        '(NULITETI)': 'Ligji Nr. 04 L-077 Për Marrëdhëniet E Detyrimeve',
        'NULITETI': 'Ligji Nr. 04 L-077 Për Marrëdhëniet E Detyrimeve',
        '(PADIA)': 'Ligji Nr. 03 L-006 Për Procedurën Kontestimore',
        '(PADITË)': 'Ligji Nr. 03 L-006 Për Procedurën Kontestimore',
        '(APELI)': 'Ligji Nr. 03 L-006 Për Procedurën Kontestimore',
        '(EKZEKUTIMI)': 'Ligji Nr. 04 L-139 Për Procedurën Përmbarimore',
        '(PËRMBARIMI)': 'Ligji Nr. 04 L-139 Për Procedurën Përmbarimore',
        '(PROCEDURA)': 'Ligji Nr. 03 L-006 Për Procedurën Kontestimore',
        '(PROVAT)': 'Ligji Nr. 03 L-006 Për Procedurën Kontestimore',
        '(DËSHMITARËT)': 'Ligji Nr. 03 L-006 Për Procedurën Kontestimore',
        '(EKSPERTIZA)': 'Ligji Nr. 03 L-006 Për Procedurën Kontestimore',
        
        # === SPECIFIC LAWS BY TOPIC ===
        '(PUNA)': 'Ligji Nr. 03 L-212 I Punës',
        '(PUNË)': 'Ligji Nr. 03 L-212 I Punës',
        '(PUNËSIMI)': 'Ligji Nr. 03 L-212 I Punës',
        '(KONTRATA E PUNËS)': 'Ligji Nr. 03 L-212 I Punës',
        '(SIGURIA NË PUNË)': 'Ligji Nr. 04 L-161 Për Sigurinë Dhe Shëndetin Në Punë',
        '(SHËNDETI NË PUNË)': 'Ligji Nr. 04 L-161 Për Sigurinë Dhe Shëndetin Në Punë',
        '(TATIMI)': 'Ligji Nr. 05 L-029 Për Tatimin Në Të Ardhurat E Korporatave',
        '(TATIMET)': 'Ligji Nr. 05 L-029 Për Tatimin Në Të Ardhurat E Korporatave',
        '(TATIMORE)': 'Ligji Nr. 08 L-257 Për Administrimin E Procedurave Tatimore',
        '(SHOQËRITË TREGTAPE)': 'Ligji Nr. 06 L-016 Për Shoqëritë Tregtare',
        '(SHOQËRIA TREGTAPE)': 'Ligji Nr. 06 L-016 Për Shoqëritë Tregtare',
        '(FAMILJA)': 'Ligji Nr. 2004 32 Ligji Për Familjen I Kosovës',
        '(FAMILJE)': 'Ligji Nr. 2004 32 Ligji Për Familjen I Kosovës',
        '(FËMIJA)': 'Ligji Nr. 06 L-084 Për Mbrojtjen E Fëmijës',
        '(FËMIJË)': 'Ligji Nr. 06 L-084 Për Mbrojtjen E Fëmijës',
        '(TË DHËNAT PERSONALE)': 'Ligji Nr. 06 L-082 Për Mbrojtjen E Të Dhënave Personale',
        '(PENAL)': 'Kodi Nr. 06 L-074 Kodi Penal I Republikës Së Kosovës',
        '(KRIMI)': 'Kodi Nr. 06 L-074 Kodi Penal I Republikës Së Kosovës',
        '(PROCEDURA PENALE)': 'Kodi Nr. 08 L-032 I Procedurës Penale',
        '(TË MITURIT)': 'Kodi Nr. 06 L-006 I Drejtësisë Për Të Mitur',
        '(TË MITUR)': 'Kodi Nr. 06 L-006 I Drejtësisë Për Të Mitur',
    }
    
    original_law_title = raw_law_title
    mapped = False
    
    # Case-insensitive acronym resolution
    lookup_title = clean_title.upper()
    if lookup_title in law_title_mappings:
        mapped_title = law_title_mappings[lookup_title]
        logger.info(f"Mapped law title from '{raw_law_title}' ({clean_title}) to: '{mapped_title}'")
        raw_law_title = mapped_title
        mapped = True
    else:
        raw_law_title = clean_title
    
    clean_art = str(raw_article_num).replace('Neni', '').replace('neni', '').replace('.', '').strip()
    
    # Build complete variants pool (Strings + Integers to bypass Atlas Type Mismatch)
    art_variants: List[Any] = [
        clean_art, 
        f"{clean_art}.", 
        f"Neni {clean_art}", 
        f"NENI {clean_art}",
        f"{clean_art} ",
        f" {clean_art}"
    ]
    if clean_art.isdigit():
        art_variants.append(int(clean_art))
    
    metadata = {
        "original_law_title": original_law_title,
        "mapped_law_title": raw_law_title if mapped else None,
        "was_mapped": mapped,
        "article_number": raw_article_num,
        "confidence": None,
        "strategy_used": None,
        "multiple_matches": False,
        "match_count": 0,
        "matching_laws": []
    }

    # === STRATEGY 1: Law code variations (HIGHEST CONFIDENCE) ===
    law_code_variations = _get_law_code_variations(raw_law_title)
    for law_code in law_code_variations:
        query = {
            "law_title": {"$regex": re.escape(law_code), "$options": "i"},
            "article_number": {"$in": art_variants}
        }
        cursor = db.legal_knowledge_base.find(query).sort("chunk_index", 1)
        docs = list(cursor)
        if docs:
            logger.info(f"Found documents with law code variation: '{law_code}' (HIGH CONFIDENCE)")
            metadata["strategy_used"] = f"law_code_variation: {law_code}"
            metadata["match_count"] = len(docs)
            conf = _calculate_confidence(docs[0], raw_law_title, raw_article_num, "LAW_CODE")
            metadata["confidence"] = conf
            return docs, metadata

    # === STRATEGY 2: Exact title match (HIGH CONFIDENCE) ===
    query = {
        "law_title": {"$regex": f"^{re.escape(raw_law_title.strip())}$", "$options": "i"},
        "article_number": {"$in": art_variants}
    }
    cursor = db.legal_knowledge_base.find(query).sort("chunk_index", 1)
    docs = list(cursor)
    if docs:
        logger.info(f"Found documents with exact title match (HIGH CONFIDENCE)")
        metadata["strategy_used"] = "exact_title_match"
        metadata["match_count"] = len(docs)
        conf = _calculate_confidence(docs[0], raw_law_title, raw_article_num, "EXACT_TITLE")
        metadata["confidence"] = conf
        return docs, metadata

    # === STRATEGY 3: Keyword fallback (MEDIUM CONFIDENCE) ===
    words = [w for w in raw_law_title.split() if len(w) >= 3 and w.lower() not in ['ligji', 'ligjit', 'kodi', 'kodin', 'për', 'per', 'dhe', 'nr']]
    if words:
        key_pattern = "|".join([re.escape(w) for w in words[:3]])
        query = {
            "law_title": {"$regex": key_pattern, "$options": "i"},
            "article_number": {"$in": art_variants}
        }
        cursor = db.legal_knowledge_base.find(query).sort("chunk_index", 1)
        docs = list(cursor)
        if docs:
            logger.info(f"Found documents with keyword match (MEDIUM CONFIDENCE)")
            metadata["strategy_used"] = f"keyword_fallback: {key_pattern}"
            metadata["match_count"] = len(docs)
            conf = _calculate_confidence(docs[0], raw_law_title, raw_article_num, "KEYWORD")
            metadata["confidence"] = conf
            return docs, metadata

    # === STRATEGY 4: Article + Law Title Keywords (MEDIUM CONFIDENCE) ===
    logger.info(f"Attempting article + law title keywords search for '{raw_article_num}'")
    original_words = [w.lower() for w in original_law_title.split() if len(w) >= 3 and w.lower() not in ['ligji', 'ligjit', 'kodi', 'kodin', 'për', 'per', 'dhe', 'nr']]
    
    if original_words:
        word_pattern = "|".join([re.escape(w) for w in original_words[:2]])
        query = {
            "article_number": {"$in": art_variants},
            "law_title": {"$regex": word_pattern, "$options": "i"}
        }
        cursor = db.legal_knowledge_base.find(query).sort("chunk_index", 1).limit(5)
        docs = list(cursor)
        if docs:
            logger.info(f"Found {len(docs)} documents by article + law keywords (MEDIUM CONFIDENCE)")
            metadata["strategy_used"] = f"article_plus_keywords: {word_pattern}"
            metadata["match_count"] = len(docs)
            conf = _calculate_confidence(docs[0], raw_law_title, raw_article_num, "ARTICLE_KEYWORD")
            metadata["confidence"] = conf
            return docs, metadata

    # === STRATEGY 5: Article-only search (LOW CONFIDENCE - WARNING) ===
    query = {"article_number": {"$in": art_variants}}
    cursor = db.legal_knowledge_base.find(query).sort("chunk_index", 1).limit(10)
    docs = list(cursor)
    
    # Whitespace-insensitive regex fallback for missing seeded documents
    if not docs and clean_art.isdigit():
        logger.info(f"Applying fallback whitespace-insensitive query for '{clean_art}'")
        fallback_query = {"article_number": {"$regex": f"^\\s*{clean_art}\\s*$"}}
        cursor = db.legal_knowledge_base.find(fallback_query).sort("chunk_index", 1).limit(10)
        docs = list(cursor)

    if docs:
        matching_laws = set()
        for doc in docs:
            matching_laws.add(doc.get("law_title", "Unknown"))
        
        if len(docs) > 1:
            logger.warning(f"⚠️ Found {len(docs)} documents by article number only (LOW CONFIDENCE)")
            logger.warning(f"⚠️ Multiple laws contain article {raw_article_num}: {list(matching_laws)}")
            metadata["multiple_matches"] = True
            metadata["matching_laws"] = list(matching_laws)
            
            # Try to find best match by checking if any law title contains the original topic
            for doc in docs:
                doc_title = str(doc.get("law_title", ""))
                for word in original_words:
                    if word.lower() in doc_title.lower():
                        logger.info(f"Best match: '{doc_title}' contains '{word}'")
                        metadata["strategy_used"] = f"article_only_best_match: {word}"
                        metadata["match_count"] = len(docs)
                        conf = _calculate_confidence(doc, raw_law_title, raw_article_num, "ARTICLE_ONLY_BEST")
                        metadata["confidence"] = conf
                        return [doc], metadata
            
            # If multiple matches and no clear winner, return the first one but log the risk
            logger.warning(f"⚠️ Returning first match (RISK: wrong law may be returned)")
            metadata["strategy_used"] = "article_only_first_match_risk"
            metadata["match_count"] = len(docs)
            conf = _calculate_confidence(docs[0], raw_law_title, raw_article_num, "ARTICLE_ONLY_LOW")
            metadata["confidence"] = conf
            return [docs[0]], metadata
        else:
            logger.info(f"Found 1 document by article number only (LOW CONFIDENCE)")
            metadata["strategy_used"] = "article_only_single_match"
            metadata["match_count"] = 1
            conf = _calculate_confidence(docs[0], raw_law_title, raw_article_num, "ARTICLE_ONLY")
            metadata["confidence"] = conf
            return docs, metadata

    # === STRATEGY 6: Partial article number match (LOWEST CONFIDENCE) ===
    logger.info(f"Attempting partial article match for '{raw_article_num}'")
    partial_query = {"article_number": {"$regex": f"^{raw_article_num}\\b", "$options": "i"}}
    cursor = db.legal_knowledge_base.find(partial_query).sort("chunk_index", 1).limit(10)
    docs = list(cursor)
    if docs:
        if len(docs) > 1:
            logger.warning(f"⚠️ Found {len(docs)} documents with partial article match (LOWEST CONFIDENCE)")
            metadata["multiple_matches"] = True
            matching_laws = set()
            for doc in docs:
                matching_laws.add(doc.get("law_title", "Unknown"))
            metadata["matching_laws"] = list(matching_laws)
        else:
            logger.info(f"Found 1 document with partial article match (LOWEST CONFIDENCE)")
        
        metadata["strategy_used"] = "partial_article_match"
        metadata["match_count"] = len(docs)
        conf = _calculate_confidence(docs[0], raw_law_title, raw_article_num, "PARTIAL_ARTICLE")
        metadata["confidence"] = conf
        return docs, metadata

    logger.warning(f"No documents found for law: '{original_law_title}', article: '{raw_article_num}'")
    metadata["strategy_used"] = "no_match"
    metadata["confidence"] = {"score": 0.0, "level": "NONE", "strategy": "no_match", "reason": ["No documents found"]}
    return [], metadata

def _calculate_confidence(doc: dict, raw_law_title: str, raw_article_num: str, strategy: str) -> Dict[str, Any]:
    """Calculate confidence score for a matched document with high normalization accuracy."""
    confidence = {
        "score": 0.0,
        "level": "UNKNOWN",
        "strategy": strategy,
        "reason": []
    }
    
    doc_title = str(doc.get("law_title", ""))
    doc_article = str(doc.get("article_number", ""))
    
    # Normalize titles (remove punctuation/spaces/slashes)
    def normalize_title(t: str) -> str:
        t_clean = re.sub(r'[^a-z0-9]', '', t.lower())
        return t_clean

    norm_raw_title = normalize_title(raw_law_title)
    norm_doc_title = normalize_title(doc_title)
    
    # Check match or cross-substring match
    if norm_raw_title == norm_doc_title or norm_raw_title in norm_doc_title or norm_doc_title in norm_raw_title:
        confidence["score"] += 0.5
        confidence["reason"].append("Law title matches (normalized)")
    else:
        # Check if words match
        raw_words = set([w for w in re.sub(r'[^a-z0-9\s]', ' ', raw_law_title.lower()).split() if len(w) >= 3])
        doc_words = set([w for w in re.sub(r'[^a-z0-9\s]', ' ', doc_title.lower()).split() if len(w) >= 3])
        intersect = raw_words & doc_words
        if intersect:
            word_score = min(0.3, len(intersect) * 0.1)
            confidence["score"] += word_score
            confidence["reason"].append(f"Partial keyword matches: {intersect}")

    # Check law code match (numbers like 04/L-077 or 03/L-006)
    raw_numbers = set(re.findall(r'\d+', raw_law_title))
    doc_numbers = set(re.findall(r'\d+', doc_title))
    common_numbers = raw_numbers & doc_numbers
    if common_numbers:
        confidence["score"] += 0.2
        confidence["reason"].append(f"Law code numbers match: {common_numbers}")
    
    # Extract only digits from article numbers
    clean_raw_art = re.sub(r'\D', '', raw_article_num)
    clean_doc_art = re.sub(r'\D', '', doc_article)
    
    if clean_raw_art and clean_doc_art and clean_raw_art == clean_doc_art:
        confidence["score"] += 0.3
        confidence["reason"].append("Article digits exact match")
    elif clean_raw_art in clean_doc_art or clean_doc_art in clean_raw_art:
        confidence["score"] += 0.15
        confidence["reason"].append("Article digits partial match")
    
    # Strategy-based boost
    if strategy in ["LAW_CODE", "EXACT_TITLE"]:
        confidence["score"] += 0.1
        confidence["reason"].append("Matched via exact title/code strategies")
    
    # Cap score at 1.0
    confidence["score"] = min(confidence["score"], 1.0)
    
    # Set confidence level
    if confidence["score"] >= 0.8:
        confidence["level"] = "HIGH"
    elif confidence["score"] >= 0.5:
        confidence["level"] = "MEDIUM"
    else:
        confidence["level"] = "LOW"
    
    return confidence

def find_pdf_by_number_pair(requested_name: str) -> Optional[str]:
    clean_requested = os.path.basename(requested_name).strip()

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

    digits = re.findall(r'\b\d+\b', clean_requested)

    for search_dir in search_dirs:
        if not os.path.exists(search_dir):
            continue

        for root, _, files in os.walk(search_dir):
            for f in files:
                if not f.lower().endswith('.pdf'):
                    continue

                if f.lower() == clean_requested.lower():
                    return os.path.join(root, f)

                if len(digits) >= 2:
                    primary_nums = [d for d in digits if len(d) >= 2 or d != '0']
                    if primary_nums and all(num in f for num in primary_nums):
                        return os.path.join(root, f)

                if 'kushtetuta' in clean_requested.lower() and 'kushtetuta' in f.lower():
                    return os.path.join(root, f)

    return None

RIGID_AUDITOR_PROMPT = """
ROLI: Ti je 'Krye-Auditori Forenzik' i certifikuar për juridiksionin e Kosovës.
DETYRA: Përgjigju pyetjeve të përdoruesit BAZUAR VETËM NË KONTEKSTIN E DHËNË.

1. **MOS SHPIK ASNJË LIGJ, NEN, APO DATË.**
2. **PËR ÇDO DEKLARATË LIGJORE, CITO BURIMIN E SAKTË.** Formati: "[Burimi: {emri_i_ligjit}, Neni X]"
3. **NUMRAT DHE DATAT DUHET TË EKZISTOJNË NË KONTEKST.**
4. **NËSE NUK JE I SIGURTË, THUAJ "NUK DI".**
5. **DELEGIMI I MATEMATIKËS:** Llogaritja kërkon përpunim nga motori tatimor.

STILI: Shqip standard, i qartë, me pika dhe lista për lehtësi.
"""

@router.get("/pdf/{filename}")
async def get_law_pdf(filename: str):
    clean_name = os.path.basename(filename)

    try:
        s3 = storage_service.get_s3_client()
        bucket = storage_service.B2_BUCKET_NAME
        digits = re.findall(r'\b\d+\b', clean_name)

        b2_response = s3.list_objects_v2(Bucket=bucket, Prefix="laws/")
        b2_items = b2_response.get('Contents', [])

        for obj in b2_items:
            key = obj.get('Key', '')
            b2_filename = os.path.basename(key)

            is_exact = b2_filename.lower() == clean_name.lower()
            primary_nums = [d for d in digits if len(d) >= 2 or d != '0']
            is_number_match = len(primary_nums) >= 2 and all(num in b2_filename for num in primary_nums)

            if is_exact or is_number_match:
                presigned_url = storage_service.generate_presigned_url(key)
                if presigned_url:
                    return RedirectResponse(url=presigned_url)
    except Exception as e:
        logger.warning(f"B2 cloud PDF search skipped: {e}")

    found_file = find_pdf_by_number_pair(clean_name)
    if found_file:
        return FileResponse(found_file, media_type="application/pdf", filename=os.path.basename(found_file))

    raise HTTPException(
        status_code=404, 
        detail=f"Dokumenti PDF '{clean_name}' nuk u gjet në server."
    )

@router.post("/sync-to-b2")
async def sync_laws_to_b2(current_user = Depends(get_current_user)):
    try:
        s3 = storage_service.get_s3_client()
        bucket = storage_service.B2_BUCKET_NAME

        existing_b2_files = set()
        try:
            b2_res = s3.list_objects_v2(Bucket=bucket, Prefix="laws/")
            for obj in b2_res.get('Contents', []):
                k = obj.get('Key', '')
                f_name = os.path.basename(k)
                if f_name:
                    existing_b2_files.add(f_name)
                    existing_b2_files.add(k)
        except Exception as err:
            logger.warning(f"Could not list existing B2 files: {err}")

        current_file = os.path.abspath(__file__)
        endpoints_dir = os.path.dirname(current_file)
        api_dir = os.path.dirname(endpoints_dir)
        app_dir = os.path.dirname(api_dir)
        backend_dir = os.path.dirname(app_dir)
        project_root = os.path.dirname(backend_dir)

        search_dirs = [
            os.path.join(project_root, "data", "laws"),
            os.path.join(backend_dir, "data", "laws"),
            "data/laws"
        ]

        uploaded = []
        skipped = []

        for s_dir in search_dirs:
            if not os.path.exists(s_dir):
                continue
            for root, _, files in os.walk(s_dir):
                rel_path = os.path.relpath(root, s_dir)
                subfolder = '' if rel_path == '.' else rel_path.replace('\\', '/')

                for f in files:
                    if f.lower().endswith('.pdf'):
                        b2_key = f"laws/{subfolder}/{f}".replace('//', '/') if subfolder else f"laws/{f}"

                        if f in existing_b2_files or b2_key in existing_b2_files:
                            skipped.append(f)
                            continue

                        local_path = os.path.join(root, f)
                        try:
                            s3.upload_file(
                                local_path, 
                                bucket, 
                                b2_key, 
                                ExtraArgs={'ContentType': 'application/pdf'}
                            )
                            uploaded.append(f)
                            existing_b2_files.add(f)
                            existing_b2_files.add(b2_key)
                        except Exception as e:
                            logger.error(f"[B2 Cloud Sync Error] {f}: {e}")

        return {
            "status": "SUCCESS", 
            "message": f"Sinkronizimi u krye. U ngarkuan {len(uploaded)} skedarë të rinj, u anashkaluan {len(skipped)} ekzistues.",
            "uploaded_files": uploaded,
            "skipped_files": skipped
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dështoi sinkronizimi në B2: {str(e)}")

@router.post("/explain")
async def explain_law_article(request: LawExplainRequest, current_user = Depends(get_current_user)):
    system_prompt = (
        "ROLI: Ti je partneri kryesor (Senior Legal Partner) në zyrën më prestigjioze ligjore në Kosovë.\n\n"
        "DUHET TË STRUKTUROSH PËRGJIGJEN SAKTËSISHT NË DY SEKSIONE TË NDARA ME MARKERIN [NDARJA]:\n\n"
        "NIVELI 1: OPINIONI PROFESIONAL (Për Juristët)\n"
        "Analizë e thellë doktrinare, precedentet dhe interpretimi i nenit.\n\n"
        "[NDARJA]\n\n"
        "NIVELI 2: KËSHILLIM PËR QYTETARIN\n"
        "Shpjegim jashtëzakonisht i thjeshtë me fjalë të përditshme se çfarë do të thotë ky nen për jetën e tij."
    )
    try:
        generator = llm_service.stream_text_async(sys_p=system_prompt, user_p=request.prompt, temp=0.3)
        return StreamingResponse(generator, media_type="text/plain")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Synthesis failed: {str(e)}")

@router.post("/audit-chat")
async def audit_chat(request: AuditChatRequest, current_user = Depends(get_current_user)):
    try:
        from app.core.db import get_db_instance
        db = get_db_instance()
        
        user_query = request.effective_query
        documents = []

        # 1. Prioritize law title and article number lookup for 100% accuracy
        if request.law_title and request.article_number:
            documents, metadata = find_law_documents(db, request.law_title, request.article_number)
            logger.info(f"Audit chat metadata: {metadata}")

        # 2. Fallback to article_id (chunk_id)
        if not documents and request.article_id:
            doc = db.legal_knowledge_base.find_one({"chunk_id": request.article_id})
            if doc:
                documents = [doc]
                metadata = {"strategy_used": "chunk_id", "confidence": {"level": "HIGH", "score": 1.0}}

        # 3. Ultimate Fallback: search by article number
        if not documents and request.article_number:
            clean_art = str(request.article_number).replace('Neni', '').replace('.', '').strip()
            cursor = db.legal_knowledge_base.find({"article_number": clean_art}).limit(5)
            documents = list(cursor)
            metadata = {"strategy_used": "ultimate_fallback", "confidence": {"level": "LOW", "score": 0.3}}
        
        if not documents:
            raise HTTPException(status_code=404, detail="Article not found in database.")
        
        full_article_text = "\n\n".join([doc.get("text", "") for doc in documents])
        law_title = documents[0].get("law_title", request.law_title or "Ligji")
        art_num = documents[0].get("article_number", request.article_number or "")
        
        context = f"=== KONTEKSTI I DOKUMENTEVE ===\nTitulli i Ligjit: {law_title}\nNumri i Nenit: {art_num}\nPërmbajtja e Nenit:\n{full_article_text}\n"
        full_user_prompt = f"{context}\n\nPyetja e përdoruesit në lidhje me këtë nen: {user_query}"
        
        generator = llm_service.stream_text_async(sys_p=RIGID_AUDITOR_PROMPT, user_p=full_user_prompt, temp=0.0)
        return StreamingResponse(generator, media_type="text/plain")
        
    except HTTPException: raise
    except Exception as e: 
        logger.error(f"Audit chat error: {e}")
        raise HTTPException(status_code=500, detail=f"Audit chat failed: {str(e)}")

@router.get("/search")
async def search_laws(q: str = Query(...), limit: int = Query(50, ge=1, le=200), current_user = Depends(get_current_user)):
    try:
        results = vector_store_service.query_global_knowledge_base(q, n_results=limit)
        return results
    except Exception as e: raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/titles")
async def get_law_titles(current_user = Depends(get_current_user)):
    try:
        from app.core.db import get_db_instance
        db = get_db_instance()
        titles = db.legal_knowledge_base.distinct("law_title")
        return sorted([t for t in titles if t])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching titles: {str(e)}")

@router.get("/article")
async def get_law_article(
    law_title: str = Query(...), 
    article_number: str = Query(...), 
    current_user = Depends(get_current_user)
):
    try:
        from app.core.db import get_db_instance
        db = get_db_instance()
        
        documents, metadata = find_law_documents(db, law_title, article_number)
        
        if not documents: 
            raise HTTPException(
                status_code=404, 
                detail=f"Neni nuk u gjet për ligjin '{law_title}', Neni {article_number}"
            )

        # Log the source law for transparency
        source_law = documents[0].get("law_title", law_title)
        source_article = documents[0].get("article_number", article_number)
        confidence_level = metadata.get("confidence", {}).get("level", "UNKNOWN")
        
        logger.info(f"Returning article from: '{source_law}', Article: '{source_article}' (Confidence: {confidence_level})")
        
        # If confidence is LOW, log a warning
        if confidence_level == "LOW" or confidence_level == "LOWEST":
            logger.warning(f"⚠️ LOW CONFIDENCE match for '{law_title}' Article '{article_number}' -> '{source_law}' Article '{source_article}'")
            if metadata.get("multiple_matches"):
                logger.warning(f"⚠️ Multiple laws contain this article: {metadata.get('matching_laws', [])}")

        # Generate user-friendly source_info
        source_info = _generate_source_info(
            documents[0], 
            metadata, 
            law_title, 
            article_number
        )

        return {
            "law_title": documents[0].get("law_title", law_title),
            "article_number": documents[0].get("article_number", article_number),
            "source": documents[0].get("source", ""),
            "text": "\n\n".join([doc.get("text", "") for doc in documents]),
            "source_info": source_info
        }
    except HTTPException: raise
    except Exception as e: 
        logger.error(f"Article endpoint error: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/by-title")
async def get_law_articles(law_title: str = Query(...), current_user = Depends(get_current_user)):
    try:
        from app.core.db import get_db_instance
        db = get_db_instance()
        
        query = {"law_title": law_title}
        law_num_match = re.search(r'\b(\d{2,4}[\/\-][L\d\-]+(?:\d+)?)\b', law_title, re.I)
        if law_num_match:
            query = {"law_title": {"$regex": re.escape(law_num_match.group(1)), "$options": "i"}}
        
        cursor = db.legal_knowledge_base.find(query, {"law_title": 1, "article_number": 1, "source": 1})
        docs = list(cursor)
        
        if not docs: 
            cursor = db.legal_knowledge_base.find({"law_title": {"$regex": f"^{re.escape(law_title)}$", "$options": "i"}}, {"law_title": 1, "article_number": 1, "source": 1})
            docs = list(cursor)

        if not docs:
            raise HTTPException(status_code=404, detail="Ligji nuk u gjet")
        
        canonical_title = docs[0].get("law_title", law_title)
        articles: Set[str] = {str(d.get("article_number")) for d in docs if d.get("article_number") is not None}
        sorted_articles = sorted(list(articles), key=_natural_sort_key)
        
        return {
            "law_title": canonical_title,
            "source": str(docs[0].get("source", "")),
            "article_count": len(sorted_articles),
            "articles": sorted_articles
        }
    except HTTPException: raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@router.get("/{chunk_id}")
async def get_law_chunk(chunk_id: str, current_user = Depends(get_current_user)):
    try:
        from app.core.db import get_db_instance
        db = get_db_instance()
        doc = db.legal_knowledge_base.find_one({"chunk_id": chunk_id})
        
        if not doc: 
            raise HTTPException(status_code=404, detail="Law chunk not found")

        return {
            "law_title": str(doc.get("law_title", "Ligji i panjohur")),
            "article_number": str(doc.get("article_number", "")),
            "source": str(doc.get("source", "")),
            "text": doc.get("text", "")
        }
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")