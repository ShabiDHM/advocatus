# FILE: backend/app/services/document_review/mongo_verifier.py
# PHOENIX PROTOCOL - MONGO VERIFIER V1.9
# V1.9: FIX KRITIK — WORD BOUNDARY në abbrev_match dhe full_name_match.
#       "PENAL" nuk matchon më "PENALE" (bug: KODI PENAL → KPK gabimisht).
# V1.8: full_name_match me word boundary (i cunguar — vetëm hapi 5).
# V1.7: TOC FILTER + sort sekondar text_len DESC.
# V1.6: FULL_NAME_MATCH + prag dinamik overlap.
# V1.5: text_excerpt 500 → 3000 chars.
# V1.4: KNOWN_ABBREV_KEYWORDS për akronime zyrtare kosovare.
# V1.3: FIX "LMD" ⊂ "LMDHF" + short-circuit + limit 20.
# V1.2: "Ligji"/"Kodi" NUK filtrohen më në gjenerim akronimesh.
# V1.1: Prioritet match + gjenerim dinamik akronimesh.
# V1.0: Ekstraktim deterministik.

import re
import logging
from typing import Dict, Any, List, Set, Optional, Tuple

from .constants import (
    LEGAL_KB_COLLECTION,
    CASE_LAW_COLLECTION,
    ALBANIAN_STOPWORDS,
)
from .helpers import normalize_albanian, normalize_law_number, normalize_case_number

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# V1.2: MINI STOPWORDS për gjenerimin e akronimeve
# NUK filtron "ligji", "kodi", "kushtetuta" — ato janë pjesë e akronimit.
# ═══════════════════════════════════════════════════════════════════════════

ABBREV_SKIP_WORDS = {
    # Parafjalë dhe lidhëza
    "për", "per", "dhe", "ose", "me", "në", "ne", "nga",
    "të", "te", "e", "i", "së", "se", "si", "ka",
    # Fjalë numerike dhe kontekstuale
    "nr", "numri", "numrit", "numër", "numer",
    "republikës", "republike", "republikë",
    "kosovës", "kosove", "kosovë",
    "këtij", "ketij", "kësaj", "kesaj",
    # Fjalë gjyqësore pa vlerë akronimike
    "gjykata", "gjykatës", "gjykate", "gjykatë",
    "vendimi", "vendimit", "vendim",
    "aktgjykim", "aktgjykimi",
    "aktvendim", "aktvendimi",
    "lënda", "lenda", "lëndës", "lendes",
    "rasti", "rastit", "rast",
    "pala", "palë", "pales", "palës", "palët", "palet",
    "apelit", "apeli", "themelore", "supreme",
}


# ═══════════════════════════════════════════════════════════════════════════
# V1.4: KNOWN_ABBREV_KEYWORDS — akronime zyrtare kosovare
# Për secilin akronim, lista e fjalëve kyçe (të pjesshme, lowercase) që DUHEN
# hasur në law_title. Kontrolli bëhet me substring në titullin e normalizuar.
# ═══════════════════════════════════════════════════════════════════════════

KNOWN_ABBREV_KEYWORDS: Dict[str, List[str]] = {
    # Ligji për Mbrojtjen nga Dhuna në Familje
    "LMDHF": ["ligji", "mbrojtj", "dhuna", "familje"],
    # Ligji për Marrëdhëniet e Detyrimeve
    "LMD":   ["ligji", "marrëdhëniet", "detyrimeve"],
    # Ligji për Procedurën Kontestimore
    "LPK":   ["ligji", "procedurën", "kontestimore"],
    # Kodi Penal i Republikës së Kosovës
    "KPRK":  ["kodi", "penal"],
    # Kodi i Procedurës Penale
    "KPK":   ["kodi", "procedurës", "penale"],
    "KPPRK": ["kodi", "procedurës", "penale"],
    # Ligji për Familjen
    "LFK":   ["ligji", "familjen"],
    # Ligji për Shoqëritë Tregtare
    "LSHT":  ["ligji", "shoqëritë", "tregtare"],
    # Kushtetuta e Republikës së Kosovës
    "KRK":   ["kushtetuta"],
}


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS — NORMALIZIM
# ═══════════════════════════════════════════════════════════════════════════

def _extract_law_number_from_text(text: str) -> Optional[str]:
    """Nxjerr numrin e ligjit nga një tekst."""
    if not text:
        return None
    m = re.search(
        r'(\d{2})\s*[\/\-_\s]?\s*L\s*[\/\-_\s]?\s*(\d{2,4})',
        text, re.IGNORECASE,
    )
    if m:
        return f"{m.group(1)}/L-{m.group(2)}"
    return None


def _extract_keywords(text: str, min_length: int = 4) -> Set[str]:
    """Nxjerr fjalë kyçe nga një emër ligji (pa stopwords)."""
    if not text:
        return set()
    normalized = normalize_albanian(text)
    words = re.findall(rf'\b[a-z]{{{min_length},}}\b', normalized)
    return set(w for w in words if w not in ALBANIAN_STOPWORDS)


# ═══════════════════════════════════════════════════════════════════════════
# V1.7: TOC DETECTION — injoron tabelat e përmbajtjes
# ═══════════════════════════════════════════════════════════════════════════

def _looks_like_toc(text: str) -> bool:
    """
    V1.7: Kontrollo nëse teksti i chunk-ut është nga tabela e përmbajtjes.
    Kriteret (dinamik, pa hardkodim ligji):
      - Përmban 1+ rreshta me 5+ pika radhazi (........)
      - Teksti total < 250 chars DHE ka pika të shumta
      - Mbi 40% e rreshtave përfundojnë me numër
    """
    if not text:
        return False

    stripped = text.strip()
    if len(stripped) < 20:
        return False

    # Kriteri 1: shumë pika radhazi (TOC klasik)
    dotted_matches = re.findall(r'\.{5,}', stripped)
    if len(dotted_matches) >= 1 and len(stripped) < 400:
        return True

    # Kriteri 2: 2+ rreshta me ".....N" (numri i faqes)
    toc_lines = re.findall(r'\.{3,}\s*\d+\s*$', stripped, re.MULTILINE)
    if len(toc_lines) >= 2:
        return True

    # Kriteri 3: Mbi 40% e rreshtave mbarojnë me "....numri"
    lines = [l for l in stripped.split("\n") if l.strip()]
    if len(lines) >= 3:
        dotted_ending = sum(1 for l in lines if re.search(r'\.{3,}\s*\d+\s*$', l))
        if dotted_ending / len(lines) > 0.4:
            return True

    return False


# ═══════════════════════════════════════════════════════════════════════════
# V1.2: DYNAMIC ABBREVIATION GENERATION
# ═══════════════════════════════════════════════════════════════════════════

def _generate_abbreviation_from_title(title: str) -> str:
    """
    V1.2: Gjeneron akronim nga titulli i ligjit.
    "Ligji"/"Kodi"/"Kushtetuta" NUK filtrohen — ato japin shkronjën e parë.

    Shembuj:
      "LIGJI NR. 03 L 006 PËR PROCEDURËN KONTESTIMORE" → "LPK"
      "KODI NR. 06 L 074 KODI PENAL" → "KKP" (Kodi + Kodi + Penal)
      "LIGJI PËR MBROJTJEN NGA DHUNA NË FAMILJE" → "LMDHF" ose "LPMDNF"
    """
    if not title:
        return ""

    # Hiq "Ligji Nr. XX/L-YYY" / "Kodi Nr. XX/L-YYY" prefixin numerik
    title_clean = re.sub(
        r'\b(?:Nr\.?|nr\.?)\s*\d+\s*[\/\-_\s]?\s*L\s*[\/\-_\s]?\s*\d+',
        '', title, flags=re.IGNORECASE,
    )

    # Normalizo
    normalized = normalize_albanian(title_clean)

    # Nda në fjalë
    words = re.findall(r'\b[a-zëç]+\b', normalized)

    # Filtro vetëm MINI_SKIP_WORDS (jo ALBANIAN_STOPWORDS!)
    significant = [
        w for w in words
        if w not in ABBREV_SKIP_WORDS and len(w) >= 1
    ]

    if len(significant) < 2:
        return ""

    # Merr shkronjën e parë të fjalëve të para (max 6)
    abbrev = "".join(w[0].upper() for w in significant[:6])
    return abbrev


# ═══════════════════════════════════════════════════════════════════════════
# V1.4: KNOWN ABBREV MATCH
# ═══════════════════════════════════════════════════════════════════════════

def _known_abbrev_matches(cit_upper: str, db_title: str) -> bool:
    """
    V1.4: Kontrollo akronimin kundrejt mapping-ut zyrtar.
    Kthen True nëse TË GJITHA fjalët kyçe shfaqen si substring në titull.
    """
    keywords = KNOWN_ABBREV_KEYWORDS.get(cit_upper)
    if not keywords:
        return False

    title_norm = normalize_albanian(db_title)
    return all(kw in title_norm for kw in keywords)


# ═══════════════════════════════════════════════════════════════════════════
# PRIORITY + MATCHING
# ═══════════════════════════════════════════════════════════════════════════

def _reason_priority(reason: str) -> int:
    """Prioritet i arsyes së match-it."""
    if reason.startswith("number_match"):
        return 100
    if reason.startswith("full_name_match"):
        return 96
    if reason.startswith("abbrev_known"):
        return 95
    if reason.startswith("abbrev_generated_exact"):
        return 90
    if reason.startswith("abbrev_generated_prefix"):
        return 85
    if reason.startswith("abbrev_generated_partial"):
        return 80
    if reason.startswith("abbrev_match"):
        return 70
    if reason.startswith("keyword_match"):
        return 50
    return 0


def _title_matches_citation(db_title: str, citation_law_hint: str) -> Tuple[bool, str]:
    """Kontrollo nëse law_title përputhet me law_hint."""
    if not db_title or not citation_law_hint:
        return False, "empty"

    # 1. Numër ligji
    db_num = _extract_law_number_from_text(db_title)
    cit_num = _extract_law_number_from_text(citation_law_hint)
    if db_num and cit_num and db_num == cit_num:
        return True, f"number_match:{db_num}"

    cit_upper = citation_law_hint.upper().strip()
    is_abbrev_hint = bool(re.match(r'^[A-ZËÇ]{2,6}$', cit_upper))

    # 2. V1.4: Mapping akronimesh zyrtare
    if is_abbrev_hint and _known_abbrev_matches(cit_upper, db_title):
        return True, f"abbrev_known:{cit_upper}"

    # 3. Gjenerim dinamik akronimi
    if is_abbrev_hint:
        generated = _generate_abbreviation_from_title(db_title)
        if generated:
            if cit_upper == generated:
                return True, f"abbrev_generated_exact:{cit_upper}"
            if len(cit_upper) >= 3 and len(generated) >= 3:
                if abs(len(cit_upper) - len(generated)) <= 1 and generated.startswith(cit_upper):
                    return True, f"abbrev_generated_prefix:{cit_upper}~{generated}"

    # ═══════════════════════════════════════════════════════════════════════
    # 4. V1.9: Akronim direkt në titull — ME WORD BOUNDARY
    #    "PENAL" nuk matchon më "PENALE" (bug fix kritik)
    # ═══════════════════════════════════════════════════════════════════════
    if is_abbrev_hint:
        db_upper = db_title.upper()
        pattern = r'\b' + re.escape(cit_upper) + r'\b'
        if re.search(pattern, db_upper):
            return True, f"abbrev_match:{cit_upper}"

    # ═══════════════════════════════════════════════════════════════════════
    # 5. V1.9: FULL_NAME_MATCH — emër i plotë ligji (me word boundary)
    # ═══════════════════════════════════════════════════════════════════════
    if not is_abbrev_hint and len(cit_upper) >= 5:
        db_upper = db_title.upper()
        pattern = r'\b' + re.escape(cit_upper) + r'\b'
        if re.search(pattern, db_upper):
            return True, f"full_name_match:{cit_upper}"

    # ═══════════════════════════════════════════════════════════════════════
    # 6. Fjalë kyçe — prag DINAMIK
    # ═══════════════════════════════════════════════════════════════════════
    db_kw = _extract_keywords(db_title)
    cit_kw = _extract_keywords(citation_law_hint)
    overlap = db_kw & cit_kw
    min_overlap = 1 if len(cit_kw) <= 1 else 2
    if len(overlap) >= min_overlap:
        return True, f"keyword_match:{sorted(overlap)[:3]}"

    return False, "no_match"


# ═══════════════════════════════════════════════════════════════════════════
# VERIFY SINGLE ARTICLE
# ═══════════════════════════════════════════════════════════════════════════

def _verify_single_article(
    db,
    article_number: str,
    paragraph: Optional[str],
    law_hint: str,
) -> Dict[str, Any]:
    """Verifikon një nen të vetëm kundrejt DB."""
    result = {
        "article_number": article_number,
        "paragraph": paragraph,
        "law_hint": law_hint,
        "exists": False,
        "matched_doc": None,
        "match_reason": "",
        "candidates_checked": 0,
        "toc_filtered": 0,
    }

    if db is None:
        result["match_reason"] = "no_db"
        return result

    try:
        collection = db[LEGAL_KB_COLLECTION]

        article_variants = [article_number, f"{article_number}."]
        try:
            article_variants.append(int(article_number))
        except (ValueError, TypeError):
            pass

        query = {
            "is_article": True,
            "article_number": {"$in": article_variants},
        }

        # V1.3: Short-circuit
        if collection.count_documents(query, limit=1) == 0:
            result["match_reason"] = "article_not_in_db"
            return result

        # V1.3: limit 100 → 20 (perf: 5x më pak docs)
        candidates = list(collection.find(query, {
            "law_title": 1, "article_number": 1, "source": 1,
            "text": 1, "chunk_index": 1, "page": 1,
        }).limit(20))

        result["candidates_checked"] = len(candidates)

        if not candidates:
            result["match_reason"] = "article_not_in_db"
            return result

        # ═══════════════════════════════════════════════════════════════════
        # V1.7: TOC FILTER — prefero kandidatë që NUK janë TOC
        # ═══════════════════════════════════════════════════════════════════
        non_toc = [c for c in candidates if not _looks_like_toc(c.get("text", ""))]
        toc_count = len(candidates) - len(non_toc)
        result["toc_filtered"] = toc_count

        if non_toc:
            candidates = non_toc
            if toc_count > 0:
                logger.info(
                    f"🧹 [TOC Filter V1.7] Hoqën {toc_count} kandidatë TOC për Neni {article_number}, "
                    f"mbetën {len(non_toc)} real"
                )
        elif toc_count > 0:
            logger.warning(
                f"⚠️ [TOC Filter V1.7] Të gjithë kandidatët për Neni {article_number} "
                f"janë TOC ({toc_count}) — përdorim fallback"
            )

        if not law_hint:
            law_titles = set(c.get("law_title", "") for c in candidates)
            if len(law_titles) == 1:
                doc = max(candidates, key=lambda c: len(c.get("text", "")))
                result["exists"] = True
                result["matched_doc"] = _serialize_doc(doc)
                result["match_reason"] = "single_law_in_db"
            else:
                result["match_reason"] = f"multiple_laws_no_hint:{len(law_titles)}"
            return result

        # Mbledh TË GJITHA match-et
        matches: List[Tuple[int, Dict[str, Any], str]] = []

        for candidate in candidates:
            db_title = candidate.get("law_title", "") or ""
            is_match, reason = _title_matches_citation(db_title, law_hint)
            if is_match:
                priority = _reason_priority(reason)
                matches.append((priority, candidate, reason))

        if matches:
            # V1.7: Sort — priority DESC, pastaj text length DESC
            matches.sort(key=lambda x: (-x[0], -len(x[1].get("text", ""))))
            _, best_doc, best_reason = matches[0]
            result["exists"] = True
            result["matched_doc"] = _serialize_doc(best_doc)
            result["match_reason"] = best_reason
        else:
            result["match_reason"] = "law_hint_no_match"

        return result

    except Exception as e:
        logger.warning(f"⚠️ [_verify_single_article] Error: {e}")
        result["match_reason"] = f"error:{type(e).__name__}"
        return result


# ═══════════════════════════════════════════════════════════════════════════
# SERIALIZE DOC — V1.5: text_excerpt 3000 chars
# ═══════════════════════════════════════════════════════════════════════════

MAX_TEXT_EXCERPT_CHARS = 3000


def _serialize_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Serializon dokumentin MongoDB. V1.5: text_excerpt 3000 chars."""
    if not doc:
        return {}
    full_text = doc.get("text") or ""
    return {
        "law_title": doc.get("law_title", ""),
        "article_number": str(doc.get("article_number", "")),
        "source": doc.get("source", ""),
        "text_excerpt": full_text[:MAX_TEXT_EXCERPT_CHARS],
        "text_truncated": len(full_text) > MAX_TEXT_EXCERPT_CHARS,
        "text_full_length": len(full_text),
        "page": doc.get("page"),
    }


# ═══════════════════════════════════════════════════════════════════════════
# VERIFY ARTICLES
# ═══════════════════════════════════════════════════════════════════════════

def verify_articles(db, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Verifikon të gjitha nenet."""
    if not articles:
        return []

    results = []
    for article in articles:
        verification = _verify_single_article(
            db, article["number"], article.get("paragraph"),
            article.get("law_hint", ""),
        )
        verification["citation_context"] = article.get("context", "")
        verification["citation_sentence"] = article.get("sentence", "")
        results.append(verification)

    verified = sum(1 for r in results if r["exists"])
    logger.info(
        f"📚 [MONGO_VERIFIER] Articles: {len(results)} total, "
        f"{verified} verified, {len(results) - verified} not found"
    )
    return results


# ═══════════════════════════════════════════════════════════════════════════
# VERIFY LAW NUMBERS
# ═══════════════════════════════════════════════════════════════════════════

def verify_law_numbers(
    db, laws_by_number: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Verifikon numrat e ligjeve."""
    if not laws_by_number:
        return []

    if db is None:
        return [
            {**law, "exists": False, "matched_doc": None, "match_reason": "no_db"}
            for law in laws_by_number
        ]

    results = []
    collection = db[LEGAL_KB_COLLECTION]

    for law in laws_by_number:
        law_number = law["number"]
        result = {
            "number": law_number,
            "name": law.get("name", ""),
            "exists": False,
            "matched_doc": None,
            "match_reason": "",
        }

        try:
            m = re.match(r'(\d{2})/L-(\d+)', law_number)
            if not m:
                result["match_reason"] = "invalid_number_format"
                results.append(result)
                continue

            part1, part2 = m.group(1), m.group(2)

            title_patterns = [
                rf"\b{part1}\s*[\/\-_\s]?\s*L\s*[\/\-_\s]?\s*{part2}\b",
                rf"\b{part1}\s+L\s+{part2}\b",
            ]

            for pattern in title_patterns:
                doc = collection.find_one(
                    {"law_title": {"$regex": pattern, "$options": "i"}},
                    {"law_title": 1, "source": 1, "text": 1},
                )
                if doc:
                    result["exists"] = True
                    result["matched_doc"] = {
                        "law_title": doc.get("law_title", ""),
                        "source": doc.get("source", ""),
                    }
                    result["match_reason"] = "number_in_title"
                    break

            if not result["exists"]:
                result["match_reason"] = "law_not_in_db"

        except Exception as e:
            logger.warning(f"⚠️ [verify_law_numbers] Error for {law_number}: {e}")
            result["match_reason"] = f"error:{type(e).__name__}"

        results.append(result)

    verified = sum(1 for r in results if r["exists"])
    logger.info(
        f"📚 [MONGO_VERIFIER] Laws by number: {len(results)} total, "
        f"{verified} verified"
    )
    return results


# ═══════════════════════════════════════════════════════════════════════════
# VERIFY CASE NUMBERS
# ═══════════════════════════════════════════════════════════════════════════

def verify_case_numbers(
    db, case_numbers: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Verifikon numrat e lëndëve."""
    if not case_numbers:
        return []

    results = []

    case_law_available = False
    if db is not None:
        try:
            case_law_available = CASE_LAW_COLLECTION in db.list_collection_names()
        except Exception:
            pass

    for case in case_numbers:
        case_number = case["case_number"]
        result = {
            "case_number": case_number,
            "prefix": case.get("prefix", ""),
            "is_likely_own": case.get("is_likely_own", False),
            "context": case.get("context", ""),
            "is_precedent": False,
            "matched_doc": None,
            "match_reason": "",
        }

        if case.get("is_likely_own"):
            result["match_reason"] = "own_case_number"
            results.append(result)
            continue

        if db is None:
            result["match_reason"] = "no_db"
            results.append(result)
            continue

        if not case_law_available:
            result["match_reason"] = "case_law_collection_not_available"
            results.append(result)
            continue

        try:
            collection = db[CASE_LAW_COLLECTION]
            clean_number = case_number.replace(" ", "").upper()
            variants = [
                clean_number,
                clean_number.replace(".", ""),
                clean_number.replace(".nr.", "/"),
            ]

            doc = None
            for variant in variants:
                doc = collection.find_one(
                    {"case_number": {"$regex": re.escape(variant), "$options": "i"}},
                    {"case_number": 1, "text": 1, "source": 1},
                )
                if doc:
                    break

            if doc:
                result["is_precedent"] = True
                result["matched_doc"] = {
                    "case_number": doc.get("case_number", ""),
                    "source": doc.get("source", ""),
                }
                result["match_reason"] = "found_in_case_law"
            else:
                result["match_reason"] = "not_in_case_law"

        except Exception as e:
            logger.warning(f"⚠️ [verify_case_numbers] Error for {case_number}: {e}")
            result["match_reason"] = f"error:{type(e).__name__}"

        results.append(result)

    precedents = sum(1 for r in results if r["is_precedent"])
    cited = sum(1 for r in results if not r["is_likely_own"])
    logger.info(
        f"📚 [MONGO_VERIFIER] Case numbers: {len(results)} total, "
        f"{cited} cited, {precedents} real precedents"
    )
    return results


# ═══════════════════════════════════════════════════════════════════════════
# VERIFY ALL
# ═══════════════════════════════════════════════════════════════════════════

def verify_all(
    db, citation_profile: Dict[str, Any],
) -> Dict[str, Any]:
    """Verifikon të gjitha citimet."""
    if not citation_profile:
        return {
            "articles": [], "laws_by_number": [],
            "case_numbers": [], "stats": {},
        }

    articles = verify_articles(db, citation_profile.get("articles", []))
    laws_by_number = verify_law_numbers(db, citation_profile.get("laws_by_number", []))
    case_numbers = verify_case_numbers(db, citation_profile.get("case_numbers", []))

    stats = {
        "articles_total": len(articles),
        "articles_verified": sum(1 for a in articles if a["exists"]),
        "articles_not_found": sum(1 for a in articles if not a["exists"]),
        "laws_total": len(laws_by_number),
        "laws_verified": sum(1 for l in laws_by_number if l["exists"]),
        "case_numbers_total": len(case_numbers),
        "case_numbers_cited": sum(1 for c in case_numbers if not c["is_likely_own"]),
        "precedents_verified": sum(1 for c in case_numbers if c["is_precedent"]),
    }

    logger.info(
        f"📚 [MONGO_VERIFIER] Complete: "
        f"articles {stats['articles_verified']}/{stats['articles_total']}, "
        f"laws {stats['laws_verified']}/{stats['laws_total']}, "
        f"precedents {stats['precedents_verified']}/{stats['case_numbers_cited']}"
    )

    return {
        "articles": articles,
        "laws_by_number": laws_by_number,
        "case_numbers": case_numbers,
        "stats": stats,
    }