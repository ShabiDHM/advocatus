# FILE: backend/app/services/document_review/mongo_verifier.py
# PHOENIX PROTOCOL - MONGO VERIFIER V2.0 (MULTI-LAW VERIFICATION)
# V2.0: VERIFIKIM MULTI-LIGJ — nëse neni nuk gjendet me law_hint:
#       1. Provo ligjin pasardhës (LAW_SUCCESSOR_MAP)
#       2. Raporto "found_in_successor_law" me sugjerim zëvendësimi
#       3. Raporto "not_found_but_exists_in" me listë ligjesh alternative
# V1.9: FIX KRITIK — WORD BOUNDARY në abbrev_match dhe full_name_match.
# V1.8: full_name_match me word boundary.
# V1.7: TOC FILTER + sort sekondar text_len DESC.
# V1.6: FULL_NAME_MATCH + prag dinamik overlap.
# V1.5: text_excerpt 3000 chars.
# V1.4: KNOWN_ABBREV_KEYWORDS.
# V1.3: FIX "LMD" ⊂ "LMDHF" + short-circuit + limit 20.
# V1.2: "Ligji"/"Kodi" NUK filtrohen.
# V1.1: Prioritet match.
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
# ═══════════════════════════════════════════════════════════════════════════

ABBREV_SKIP_WORDS = {
    "për", "per", "dhe", "ose", "me", "në", "ne", "nga",
    "të", "te", "e", "i", "së", "se", "si", "ka",
    "nr", "numri", "numrit", "numër", "numer",
    "republikës", "republike", "republikë",
    "kosovës", "kosove", "kosovë",
    "këtij", "ketij", "kësaj", "kesaj",
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
# ═══════════════════════════════════════════════════════════════════════════

KNOWN_ABBREV_KEYWORDS: Dict[str, List[str]] = {
    "LMDHF": ["ligji", "mbrojtj", "dhuna", "familje"],
    "LMD":   ["ligji", "marrëdhëniet", "detyrimeve"],
    "LPK":   ["ligji", "procedurën", "kontestimore"],
    "KPRK":  ["kodi", "penal"],
    "KPK":   ["kodi", "procedurës", "penale"],
    "KPPRK": ["kodi", "procedurës", "penale"],
    "LFK":   ["ligji", "familjen"],
    "LSHT":  ["ligji", "shoqëritë", "tregtare"],
    "KRK":   ["kushtetuta"],
}


# ═══════════════════════════════════════════════════════════════════════════
# V2.0: LAW SUCCESSOR MAP — ligje të vjetra → ligje të reja
# Format: {law_number_old: {"successor": law_number_new, "name": "...", "note": "..."}}
# ═══════════════════════════════════════════════════════════════════════════

LAW_SUCCESSOR_MAP: Dict[str, Dict[str, str]] = {
    # Ligji për Mbrojtjen nga Dhuna në Familje — zëvendësuar me 08/L-185 (2023)
    "03/L-182": {
        "successor": "08/L-185",
        "name": "Ligji për Parandalimin dhe Mbrojtjen nga Dhuna në Familje, Dhuna Ndaj Grave dhe Dhuna në Bazë Gjinore",
        "note": "LMDHF u zëvendësua në vitin 2023 me versionin e ri 08/L-185",
    },
    # Ligji për Familjen — version i konsoliduar
    "2004/32": {
        "successor": "2004/32",
        "name": "Ligji për Familjen i Kosovës",
        "note": "Ligji Nr. 2004/32 — version i konsoliduar",
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS — NORMALIZIM
# ═══════════════════════════════════════════════════════════════════════════

def _extract_law_number_from_text(text: str) -> Optional[str]:
    """Nxjerr numrin e ligjit nga një tekst (XX/L-YYY ose YYYY/NN)."""
    if not text:
        return None
    # Format XX/L-YYY
    m = re.search(
        r'(\d{2})\s*[\/\-_\s]?\s*L\s*[\/\-_\s]?\s*(\d{2,4})',
        text, re.IGNORECASE,
    )
    if m:
        return f"{m.group(1)}/L-{m.group(2)}"
    # Format YYYY/NN (si 2004/32)
    m = re.search(r'\b(\d{4})\s*[\/\-]\s*(\d{1,3})\b', text)
    if m:
        return f"{m.group(1)}/{m.group(2)}"
    return None


def _extract_keywords(text: str, min_length: int = 4) -> Set[str]:
    """Nxjerr fjalë kyçe nga një emër ligji (pa stopwords)."""
    if not text:
        return set()
    normalized = normalize_albanian(text)
    words = re.findall(rf'\b[a-z]{{{min_length},}}\b', normalized)
    return set(w for w in words if w not in ALBANIAN_STOPWORDS)


# ═══════════════════════════════════════════════════════════════════════════
# V1.7: TOC DETECTION
# ═══════════════════════════════════════════════════════════════════════════

def _looks_like_toc(text: str) -> bool:
    """Kontrollo nëse teksti është tabelë përmbajtjeje."""
    if not text:
        return False

    stripped = text.strip()
    if len(stripped) < 20:
        return False

    dotted_matches = re.findall(r'\.{5,}', stripped)
    if len(dotted_matches) >= 1 and len(stripped) < 400:
        return True

    toc_lines = re.findall(r'\.{3,}\s*\d+\s*$', stripped, re.MULTILINE)
    if len(toc_lines) >= 2:
        return True

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
    """Gjeneron akronim nga titulli i ligjit."""
    if not title:
        return ""

    title_clean = re.sub(
        r'\b(?:Nr\.?|nr\.?)\s*\d+\s*[\/\-_\s]?\s*L\s*[\/\-_\s]?\s*\d+',
        '', title, flags=re.IGNORECASE,
    )

    normalized = normalize_albanian(title_clean)
    words = re.findall(r'\b[a-zëç]+\b', normalized)

    significant = [
        w for w in words
        if w not in ABBREV_SKIP_WORDS and len(w) >= 1
    ]

    if len(significant) < 2:
        return ""

    return "".join(w[0].upper() for w in significant[:6])


def _known_abbrev_matches(cit_upper: str, db_title: str) -> bool:
    """Kontrollo akronimin kundrejt mapping-ut zyrtar."""
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

    # 2. Mapping akronimesh zyrtare
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

    # 4. Akronim direkt në titull (word boundary)
    if is_abbrev_hint:
        db_upper = db_title.upper()
        pattern = r'\b' + re.escape(cit_upper) + r'\b'
        if re.search(pattern, db_upper):
            return True, f"abbrev_match:{cit_upper}"

    # 5. FULL_NAME_MATCH (word boundary)
    if not is_abbrev_hint and len(cit_upper) >= 5:
        db_upper = db_title.upper()
        pattern = r'\b' + re.escape(cit_upper) + r'\b'
        if re.search(pattern, db_upper):
            return True, f"full_name_match:{cit_upper}"

    # 6. Fjalë kyçe — prag DINAMIK
    db_kw = _extract_keywords(db_title)
    cit_kw = _extract_keywords(citation_law_hint)
    overlap = db_kw & cit_kw
    min_overlap = 1 if len(cit_kw) <= 1 else 2
    if len(overlap) >= min_overlap:
        return True, f"keyword_match:{sorted(overlap)[:3]}"

    return False, "no_match"


# ═══════════════════════════════════════════════════════════════════════════
# V2.0: SUCCESSOR LAW LOOKUP
# ═══════════════════════════════════════════════════════════════════════════

def _get_successor_law(law_hint: str) -> Optional[Dict[str, str]]:
    """V2.0: Kthen info për ligjin pasardhës nëse ekziston."""
    if not law_hint:
        return None

    law_num = _extract_law_number_from_text(law_hint)
    if not law_num:
        return None

    successor_info = LAW_SUCCESSOR_MAP.get(law_num)
    return successor_info


def _try_successor_law(
    db,
    article_number: str,
    paragraph: Optional[str],
    original_hint: str,
    successor_info: Dict[str, str],
) -> Optional[Dict[str, Any]]:
    """
    V2.0: Provo ligjin pasardhës. Kthen result të plotë me sugjerim
    nëse neni ekziston në ligjin e ri.
    """
    successor_num = successor_info.get("successor", "")
    if not successor_num:
        return None

    try:
        collection = db[LEGAL_KB_COLLECTION]

        article_variants = [article_number, f"{article_number}."]
        try:
            article_variants.append(int(article_number))
        except (ValueError, TypeError):
            pass

        # Kërko në ligjin pasardhës duke përdorur numrin e ligjit
        query = {
            "is_article": True,
            "article_number": {"$in": article_variants},
            "law_title": {"$regex": re.escape(successor_num).replace("/", r"\s*[\/\-_\s]?\s*"), "$options": "i"},
        }

        candidates = list(collection.find(query, {
            "law_title": 1, "article_number": 1, "source": 1,
            "text": 1, "chunk_index": 1, "page": 1,
        }).limit(10))

        # Nëse regex nuk matchon (format tjetër), provo me keyword
        if not candidates:
            successor_keywords = ["parandalimin", "mbrojtjen", "dhuna", "familje"]
            alt_query = {
                "is_article": True,
                "article_number": {"$in": article_variants},
            }
            alt_candidates = list(collection.find(alt_query, {
                "law_title": 1, "article_number": 1, "source": 1,
                "text": 1, "chunk_index": 1, "page": 1,
            }).limit(20))
            for c in alt_candidates:
                title_norm = normalize_albanian(c.get("law_title", ""))
                if all(kw in title_norm for kw in successor_keywords):
                    candidates.append(c)
                    if len(candidates) >= 10:
                        break

        if not candidates:
            return None

        # Zgjedh tekstin më të gjatë (jo TOC)
        non_toc = [c for c in candidates if not _looks_like_toc(c.get("text", ""))]
        pool = non_toc if non_toc else candidates
        best_doc = max(pool, key=lambda c: len(c.get("text", "")))

        result = {
            "article_number": article_number,
            "paragraph": paragraph,
            "law_hint": original_hint,
            "exists": True,
            "matched_doc": _serialize_doc(best_doc),
            "match_reason": f"found_in_successor_law:{original_hint}→{successor_num}",
            "candidates_checked": len(candidates),
            "toc_filtered": len(candidates) - len(non_toc),
            "suggested_replacement": {
                "old_law": original_hint,
                "new_law": successor_num,
                "new_law_name": successor_info.get("name", ""),
                "note": successor_info.get("note", ""),
            },
        }
        return result

    except Exception as e:
        logger.warning(f"⚠️ [_try_successor_law] Error: {e}")
        return None


def _check_exists_in_other_laws(
    db,
    article_number: str,
) -> List[Dict[str, Any]]:
    """
    V2.0: Kontrollo nëse neni ekziston në ligje të tjera (për raportim).
    Kthen listë me (law_title, source, page) — pa konfirmim.
    """
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

        candidates = list(collection.find(query, {
            "law_title": 1, "source": 1, "text": 1, "page": 1,
        }).limit(50))

        # Filtro TOC
        non_toc = [c for c in candidates if not _looks_like_toc(c.get("text", ""))]

        # Grup sipas law_title
        seen_titles: Set[str] = set()
        results: List[Dict[str, Any]] = []
        for c in non_toc:
            title = c.get("law_title", "").strip()
            if not title or title in seen_titles:
                continue
            seen_titles.add(title)
            results.append({
                "law_title": title,
                "source": c.get("source", ""),
                "page": c.get("page"),
            })

        return results

    except Exception as e:
        logger.warning(f"⚠️ [_check_exists_in_other_laws] Error: {e}")
        return []


# ═══════════════════════════════════════════════════════════════════════════
# VERIFY SINGLE ARTICLE — V2.0
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

        # Short-circuit
        if collection.count_documents(query, limit=1) == 0:
            result["match_reason"] = "article_not_in_db"
            # V2.0: Edhe nëse nuk gjendet fare, kontribuon asgjë
            return result

        candidates = list(collection.find(query, {
            "law_title": 1, "article_number": 1, "source": 1,
            "text": 1, "chunk_index": 1, "page": 1,
        }).limit(20))

        result["candidates_checked"] = len(candidates)

        if not candidates:
            result["match_reason"] = "article_not_in_db"
            return result

        # TOC FILTER
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
                # V2.0: Raporto ligjet alternative
                result["alternative_laws"] = sorted(law_titles)
            return result

        # Standard matching
        matches: List[Tuple[int, Dict[str, Any], str]] = []

        for candidate in candidates:
            db_title = candidate.get("law_title", "") or ""
            is_match, reason = _title_matches_citation(db_title, law_hint)
            if is_match:
                priority = _reason_priority(reason)
                matches.append((priority, candidate, reason))

        if matches:
            matches.sort(key=lambda x: (-x[0], -len(x[1].get("text", ""))))
            _, best_doc, best_reason = matches[0]
            result["exists"] = True
            result["matched_doc"] = _serialize_doc(best_doc)
            result["match_reason"] = best_reason
            return result

        # ═══════════════════════════════════════════════════════════════
        # V2.0: NUK U GJET — Provo strategji alternative
        # ═══════════════════════════════════════════════════════════════
        logger.info(
            f"🔎 [MULTI-LAW V2.0] Neni {article_number} me hint='{law_hint}' "
            f"nuk u gjet direkt — provo strategji alternative..."
        )

        # Strategjia 1: Ligji pasardhës
        successor_info = _get_successor_law(law_hint)
        if successor_info:
            logger.info(
                f"➡️ [MULTI-LAW V2.0] Hint '{law_hint}' → successor "
                f"'{successor_info.get('successor')}'"
            )
            successor_result = _try_successor_law(
                db, article_number, paragraph, law_hint, successor_info
            )
            if successor_result and successor_result.get("exists"):
                logger.info(
                    f"✅ [MULTI-LAW V2.0] U gjet në ligjin pasardhës: "
                    f"{successor_result['match_reason']}"
                )
                return successor_result

        # Strategjia 2: Raporto ku tjetër ekziston
        other_laws = _check_exists_in_other_laws(db, article_number)
        if other_laws:
            logger.info(
                f"⚠️ [MULTI-LAW V2.0] Neni {article_number} ekziston në "
                f"{len(other_laws)} ligje të tjera, por jo me hint '{law_hint}'"
            )
            result["match_reason"] = "law_hint_no_match_but_exists_elsewhere"
            result["exists"] = False
            result["alternative_laws"] = other_laws
            return result

        # Nuk u gjet fare
        result["match_reason"] = "law_hint_no_match"
        return result

    except Exception as e:
        logger.warning(f"⚠️ [_verify_single_article] Error: {e}")
        result["match_reason"] = f"error:{type(e).__name__}"
        return result


# ═══════════════════════════════════════════════════════════════════════════
# SERIALIZE DOC
# ═══════════════════════════════════════════════════════════════════════════

MAX_TEXT_EXCERPT_CHARS = 3000


def _serialize_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Serializon dokumentin MongoDB."""
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
    # V2.0: Numëro edhe ata që u gjetën në ligje pasardhëse
    successor_matches = sum(
        1 for r in results
        if r.get("match_reason", "").startswith("found_in_successor_law")
    )
    alternative_found = sum(
        1 for r in results
        if r.get("match_reason") == "law_hint_no_match_but_exists_elsewhere"
    )

    logger.info(
        f"📚 [MONGO_VERIFIER V2.0] Articles: {len(results)} total, "
        f"{verified} verified (including {successor_matches} in successor laws), "
        f"{alternative_found} exist elsewhere (wrong hint), "
        f"{len(results) - verified - alternative_found} not found"
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
                # V2.0: Format YYYY/NN
                m2 = re.match(r'(\d{4})/(\d+)', law_number)
                if m2:
                    part1, part2 = m2.group(1), m2.group(2)
                    title_patterns = [
                        rf"\b{part1}\s*[\/\-_\s]?\s*{part2}\b",
                    ]
                else:
                    result["match_reason"] = "invalid_number_format"
                    results.append(result)
                    continue
            else:
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
                # V2.0: Kontrollo successor
                successor_info = _get_successor_law(law_number)
                if successor_info and successor_info.get("successor") != law_number:
                    result["match_reason"] = f"law_replaced_by:{successor_info['successor']}"
                    result["suggested_replacement"] = {
                        "old_law": law_number,
                        "new_law": successor_info["successor"],
                        "new_law_name": successor_info.get("name", ""),
                        "note": successor_info.get("note", ""),
                    }
                else:
                    result["match_reason"] = "law_not_in_db"

        except Exception as e:
            logger.warning(f"⚠️ [verify_law_numbers] Error for {law_number}: {e}")
            result["match_reason"] = f"error:{type(e).__name__}"

        results.append(result)

    verified = sum(1 for r in results if r["exists"])
    replaced = sum(
        1 for r in results
        if r.get("match_reason", "").startswith("law_replaced_by")
    )

    logger.info(
        f"📚 [MONGO_VERIFIER V2.0] Laws by number: {len(results)} total, "
        f"{verified} verified, {replaced} replaced"
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
# VERIFY ALL — V2.0
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
        # V2.0
        "articles_in_successor_laws": sum(
            1 for a in articles
            if a.get("match_reason", "").startswith("found_in_successor_law")
        ),
        "articles_exist_elsewhere": sum(
            1 for a in articles
            if a.get("match_reason") == "law_hint_no_match_but_exists_elsewhere"
        ),
        "laws_total": len(laws_by_number),
        "laws_verified": sum(1 for l in laws_by_number if l["exists"]),
        "laws_replaced": sum(
            1 for l in laws_by_number
            if l.get("match_reason", "").startswith("law_replaced_by")
        ),
        "case_numbers_total": len(case_numbers),
        "case_numbers_cited": sum(1 for c in case_numbers if not c["is_likely_own"]),
        "precedents_verified": sum(1 for c in case_numbers if c["is_precedent"]),
    }

    logger.info(
        f"📚 [MONGO_VERIFIER V2.0] Complete: "
        f"articles {stats['articles_verified']}/{stats['articles_total']} "
        f"(+{stats['articles_in_successor_laws']} in successor laws), "
        f"laws {stats['laws_verified']}/{stats['laws_total']} "
        f"({stats['laws_replaced']} replaced), "
        f"precedents {stats['precedents_verified']}/{stats['case_numbers_cited']}"
    )

    return {
        "articles": articles,
        "laws_by_number": laws_by_number,
        "case_numbers": case_numbers,
        "stats": stats,
    }