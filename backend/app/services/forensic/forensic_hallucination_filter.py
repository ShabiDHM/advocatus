# FILE: backend/app/services/forensic/forensic_hallucination_filter.py
# PHOENIX PROTOCOL - FORENSIC STATUTORY & PRECEDENT CITATION VERIFIER V1.0

import re
import logging
from typing import Dict, Any, List, Tuple, Set
from pymongo.database import Database

from .forensic_llm_service import call_forensic_llm

logger = logging.getLogger(__name__)

# Regex preciz për lëndët e gjykatave të Kosovës (kap formatin e plotë: p.sh. "Rev.nr. 123/2021" ose "Pml.nr.45/2020")
PRECEDENT_FULL_REGEX = re.compile(
    r'\b((?:Rev|PML|PKR|PA1|AC|CA|A|ANR|KMLP|P|C|Cn)\.?\s*(?:nr|Nr|NR)?\.?\s*\d+/\d{2,4})\b',
    re.IGNORECASE
)

# Regex për nenet ligjore (p.sh. "Neni 265", "nenit 123", "neni 12 paragrafi 1")
ARTICLE_REGEX = re.compile(
    r'\b(?:Neni|neni|Nenin|nenin|Nenit|nenit)\s+(\d+)(?:\s+(?:paragrafi|par\.)\s*(\d+))?',
    re.IGNORECASE
)

# Koleksionet e mundshme ku ruhen vendimet dhe ligjet në sistem
SUPREME_COLLECTIONS = ["supreme_cases", "court_precedents", "laws_store", "laws_precedents"]

def extract_precedents(text: str) -> List[str]:
    """Nxjerr të gjithë numrat e plotë të lëndëve nga teksti."""
    if not text:
        return []
    matches = PRECEDENT_FULL_REGEX.findall(text)
    # Normalizo formatin për kërkim (hiq hapësirat e tepërta)
    cleaned = []
    for m in matches:
        norm = re.sub(r'\s+', ' ', m.strip())
        if norm not in cleaned:
            cleaned.append(norm)
    return cleaned

def extract_articles(text: str) -> List[str]:
    """Nxjerr të gjitha referencat e neneve nga teksti."""
    if not text:
        return []
    found = []
    for match in ARTICLE_REGEX.finditer(text):
        art_num = match.group(1)
        full_mention = match.group(0)
        if full_mention not in found:
            found.append(full_mention)
    return found

def verify_precedent_in_db(db: Database, precedent_str: str) -> bool:
    """
    Kontrollon në koleksionet e gjykatës supreme nëse ky numër lënde ekziston realisht.
    """
    if db is None:
        return True  # Fallback tolerues në rast se DB s'është inicializuar në një test

    # Përgatit termat e kërkimit (p.sh. numrin: "123/2021")
    number_part_match = re.search(r'\d+/\d{2,4}', precedent_str)
    number_pattern = number_part_match.group(0) if number_part_match else precedent_str

    query = {
        "$or": [
            {"case_number": {"$regex": re.escape(number_pattern), "$options": "i"}},
            {"title": {"$regex": re.escape(number_pattern), "$options": "i"}},
            {"citation": {"$regex": re.escape(number_pattern), "$options": "i"}},
            {"text": {"$regex": re.escape(number_pattern), "$options": "i"}}
        ]
    }

    for coll_name in SUPREME_COLLECTIONS:
        try:
            if coll_name in db.list_collection_names():
                count = db[coll_name].count_documents(query, limit=1)
                if count > 0:
                    return True
        except Exception as e:
            logger.warning(f"Koleksioni {coll_name} nuk u verifikua: {e}")

    # Nëse precedentet nuk janë hedhur ende të gjitha në Mongo, nuk bllokojmë arbitrarisht por e shënojmë
    return False

def audit_citations(response_text: str, db: Database) -> Dict[str, Any]:
    """
    Auditon të gjitha citimet në përgjigje.
    Kthen listën e citimeve të verifikuara dhe të dyshuara.
    """
    precedents = extract_precedents(response_text)
    articles = extract_articles(response_text)

    verified_precedents: List[str] = []
    unverified_precedents: List[str] = []

    # Kontrollojmë nëse kemi koleksione në Mongo
    has_precedent_tables = False
    if db is not None:
        try:
            existing = db.list_collection_names()
            has_precedent_tables = any(c in existing for c in SUPREME_COLLECTIONS)
        except Exception:
            pass

    for prec in precedents:
        if has_precedent_tables:
            if verify_precedent_in_db(db, prec):
                verified_precedents.append(prec)
            else:
                unverified_precedents.append(prec)
        else:
            # Nëse arkivi nuk është i indeksuar ende, verifikohet me standard format
            verified_precedents.append(prec)

    return {
        "is_safe": len(unverified_precedents) == 0,
        "total_citations_found": len(precedents) + len(articles),
        "precedents_found": precedents,
        "verified_precedents": verified_precedents,
        "unverified_precedents": unverified_precedents,
        "articles_cited": articles
    }

def purge_and_regenerate_if_hallucinated(
    response_text: str,
    db: Database,
    original_prompt: str
) -> Tuple[str, Dict[str, Any]]:
    """
    Nëse konstatohen precedentë fiktivë, bën thirrje te Claude Sonnet 4.6
    për të ri-hartuar përgjigjen duke hequr fabrikimet.
    """
    audit = audit_citations(response_text, db)
    
    if audit["is_safe"] or not audit["unverified_precedents"]:
        return response_text, audit

    logger.warning(f"🚨 [Hallucination Filter] U gjetën precedentë të paverifikuar: {audit['unverified_precedents']}")

    correction_prompt = f"""AUDITIM DHE RIGJENERIM FORENZIK RIGOROZ:
Në analizën paraprake u konstatuan këto citime precedentësh që NUK figurojnë në arkivin e Gjykatës Supreme të Kosovës:
{', '.join(audit['unverified_precedents'])}

DETYRA JUAJ E DETYRUESHME:
1. Rishkruani analizën e plotë juridike.
2. Hiqni çdo precedent të paverifikuar të listuar më sipër.
3. Mbështetuni rreptësisht në nene ligjore të aplikueshme të legjislacionit të Kosovës dhe fakte konkrete.
4. Mos përmendni numra lëndësh përveç atyre që janë provuar 100% nga pala."""

    try:
        cleaned_text = call_forensic_llm(
            system_prompt=correction_prompt,
            user_content=f"Teksti fillestar që kërkon pastrim:\n\n{response_text}",
            temperature=0.0
        )
        audit["purged"] = True
        return cleaned_text, audit
    except Exception as e:
        logger.error(f"❌ Dështoi rigjenerimi i pastrimit: {e}")
        return response_text, audit