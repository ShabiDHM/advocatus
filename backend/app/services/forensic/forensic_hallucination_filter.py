# FILE: backend/app/services/forensic/forensic_hallucination_filter.py
# PHOENIX PROTOCOL - 100% AUTHENTIC FORENSIC CITATION AUDITOR V2.0
# 100% COMPLETE CODE • REAL MONGODB 'legal_knowledge_base' VERIFICATION • DEEPSEEK CLEANER • ZERO BYPASS

import re
import logging
from typing import Dict, Any, List, Tuple, Set
from pymongo.database import Database

from .forensic_llm_service import call_forensic_llm

logger = logging.getLogger(__name__)

# Regex preciz për aktgjykimet supreme (p.sh. "Rev.nr. 123/2021", "Pml.nr.45/2020", "REV 98/2024")
PRECEDENT_FULL_REGEX = re.compile(
    r'\b((?:Rev|PML|PKR|PA1|AC|CA|A|ANR|KMLP|P|C|Cn)\.?\s*(?:nr|Nr|NR)?\.?\s*\d+/\d{2,4})\b',
    re.IGNORECASE
)

# Regex për nenet ligjore (p.sh. "Neni 265", "nenit 123", "neni 12 paragrafi 1")
ARTICLE_REGEX = re.compile(
    r'\b(?:Neni|neni|Nenin|nenin|Nenit|nenit)\s+(\d+)(?:\s+(?:paragrafi|par\.)\s*(\d+))?',
    re.IGNORECASE
)

# Baza Qendrore e së Vërtetës në MongoDB Atlas
PRIMARY_KNOWLEDGE_COLLECTION = "legal_knowledge_base"


def extract_precedents(text: str) -> List[str]:
    """Nxjerr të gjithë numrat e plotë të lëndëve nga teksti."""
    if not text:
        return []
    matches = PRECEDENT_FULL_REGEX.findall(text)
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
        full_mention = match.group(0)
        if full_mention not in found:
            found.append(full_mention)
    return found


def verify_precedent_in_db(db: Database, precedent_str: str) -> bool:
    """
    Kontrollon në mënyrë të hekurt në MongoDB (legal_knowledge_base)
    nëse ky numër aktgjykimi suprem ekziston realisht në arkivë.
    """
    if db is None:
        return False

    number_part_match = re.search(r'\d+/\d{2,4}', precedent_str)
    number_pattern = number_part_match.group(0) if number_part_match else precedent_str

    caselaw_query = {
        "$and": [
            {
                "$or": [
                    {"category": "caselaw"},
                    {"is_case_law": True},
                    {"source": {"$regex": "case_law|supreme|PML|REV|PA1", "$options": "i"}},
                    {"law_title": {"$regex": "Gjykata\\s+Supreme|PML|REV", "$options": "i"}}
                ]
            },
            {
                "$or": [
                    {"case_number": {"$regex": re.escape(number_pattern), "$options": "i"}},
                    {"title": {"$regex": re.escape(number_pattern), "$options": "i"}},
                    {"source": {"$regex": re.escape(number_pattern), "$options": "i"}},
                    {"text": {"$regex": re.escape(number_pattern), "$options": "i"}}
                ]
            }
        ]
    }

    try:
        count = db[PRIMARY_KNOWLEDGE_COLLECTION].count_documents(caselaw_query, limit=1)
        return count > 0
    except Exception as e:
        logger.warning(f"Gabim gjatë verifikimit të precedentit {precedent_str}: {e}")
        return False


def verify_article_in_db(db: Database, article_str: str) -> bool:
    """
    Verifikon nëse numri i nenit ekziston në fondin e ligjeve të Kosovës.
    """
    if db is None:
        return False

    art_num_match = re.search(r'\d+', article_str)
    if not art_num_match:
        return False
    art_num = art_num_match.group(0)

    art_query = {
        "article_number": {"$in": [art_num, int(art_num) if art_num.isdigit() else art_num, f"Neni {art_num}"]},
        "is_article": True,
        "$nor": [
            {"category": "caselaw"},
            {"is_case_law": True}
        ]
    }

    try:
        count = db[PRIMARY_KNOWLEDGE_COLLECTION].count_documents(art_query, limit=1)
        return count > 0
    except Exception as e:
        logger.warning(f"Gabim gjatë verifikimit të nenit {article_str}: {e}")
        return False


def audit_citations(response_text: str, db: Database) -> Dict[str, Any]:
    """
    Auditon me saktësi absolute të gjitha citimet ligjore dhe precedentët
    drejtpërdrejt mbi bazën 'legal_knowledge_base'.
    """
    precedents = extract_precedents(response_text)
    articles = extract_articles(response_text)

    verified_precedents: List[str] = []
    unverified_precedents: List[str] = []

    for prec in precedents:
        if verify_precedent_in_db(db, prec):
            verified_precedents.append(prec)
        else:
            unverified_precedents.append(prec)

    verified_articles: List[str] = []
    unverified_articles: List[str] = []

    for art in articles:
        if verify_article_in_db(db, art):
            verified_articles.append(art)
        else:
            unverified_articles.append(art)

    is_safe = (len(unverified_precedents) == 0) and (len(unverified_articles) == 0)

    return {
        "is_safe": is_safe,
        "total_citations_found": len(precedents) + len(articles),
        "precedents_found": precedents,
        "verified_precedents": verified_precedents,
        "unverified_precedents": unverified_precedents,
        "articles_cited": articles,
        "verified_articles": verified_articles,
        "unverified_articles": unverified_articles
    }


def purge_and_regenerate_if_hallucinated(
    response_text: str,
    db: Database,
    original_prompt: str
) -> Tuple[str, Dict[str, Any]]:
    """
    Nëse konstatohen nene apo precedentë që nuk ekzistojnë në MongoDB,
    thërret DeepSeek (call_forensic_llm) për ta rishkruar tekstin
    duke asgjësuar çdo fabrikim apo halucinacion.
    """
    audit = audit_citations(response_text, db)
    
    if audit["is_safe"]:
        return response_text, audit

    flagged_issues = []
    if audit["unverified_precedents"]:
        flagged_issues.append(f"Precedentë që nuk figurojnë në arkivin Suprem: {', '.join(audit['unverified_precedents'])}")
    if audit["unverified_articles"]:
        flagged_issues.append(f"Nene që nuk u gjetën në ligjet e Kosovës: {', '.join(audit['unverified_articles'])}")

    logger.warning(f"🚨 [Hallucination Filter] Konstatim fabrikimesh: {flagged_issues}")

    correction_prompt = f"""AUDITIM DHE RIGJENERIM RIGOROZ FORENZIK (KOSOVË):
Gjatë verifikimit të thellë me bazën e të dhënave të Kosovës u konstatuan këto shkelje doktrinare:
{chr(10).join(flagged_issues)}

DETYRA JUAJ E DETYRUESHME:
1. Rishkruani analizën juridike me saktësi absolute.
2. Fshini plotësisht çdo nen ose precedent të paverifikuar të listuar më sipër.
3. Mbështetuni ekskluzivisht në normat pozitive në fuqi dhe faktet e provuara nga lënda.
4. MOS shpikni asnjëherë numra lëndësh gjyqësore."""

    try:
        cleaned_text = call_forensic_llm(
            system_prompt=correction_prompt,
            user_content=f"Kërkesa fillestare e përdoruesit:\n{original_prompt}\n\nTeksti fillestar që kërkon spastrim:\n\n{response_text}",
            temperature=0.0
        )
        audit["purged"] = True
        return cleaned_text, audit
    except Exception as e:
        logger.error(f"❌ Dështoi rigjenerimi i pastrimit me DeepSeek: {e}")
        return response_text, audit