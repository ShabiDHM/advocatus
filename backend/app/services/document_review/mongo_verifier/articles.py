# FILE: backend/app/services/document_review/mongo_verifier/articles.py
# PHOENIX PROTOCOL - MONGO VERIFIER / ARTICLES V1.2
#
# V1.2: ROBUSTNESS + PERF —
#   - HEQUR `count_documents(query, limit=1)` — ishte query e dytë e
#     panevojshme para `find().limit(20)`. Kjo kursen 1 roundtrip për çdo
#     nen të verifikuar (20 nene × N dokumente → 20×N roundtrips ndaj
#     Mongo Atlas). `find()` tashmë kthen listë bosh nëse nuk ka.
#   - `.get()` për çelësat e detyrueshëm:
#       * `article["number"]` → skip nëse None.
#       * `r["exists"]` → `r.get("exists")` në stats.
#     Parandalon KeyError kur dict vjen i mangët nga citation_profile.
#
# V1.1: BURIMET EKSTERNE nga JSON (jo hardcoded).
#   - Hequr `_check_if_international_treaty` (ishte hardcoded për KEDNJ + OKB)
#   - Shtuar përdorim i `find_external_source` nga `external_registry.py`
#   - Shtuar fusha `is_external`, `external_source_id`, `external_category`
#     në rezultatin e verifikimit për t'u dalluar nga "unverified" në frontend
#   - Shtuar Konventa e Hagës (nëpërmjet JSON, jo kod)
#   - `verify_articles` tani raporton `external_matches` veçmas
#
# V1.0 (V2.12 modular): Ekstraktuar nga mongo_verifier.py V2.11.

import logging

from typing import Any, Dict, List, Optional, Set, Tuple


from .config import LEGAL_KB_COLLECTION
from .external_registry import find_external_source
from .title_matching import _title_matches_citation, _reason_priority
from .successor_laws import _get_successor_law, _try_successor_law
from .text_utils import _looks_like_toc, _serialize_doc

logger = logging.getLogger(__name__)


def _check_exists_in_other_laws(db, article_number: str) -> List[Dict[str, Any]]:
    try:
        collection = db[LEGAL_KB_COLLECTION]
        article_variants = [article_number, f"{article_number}."]
        try:
            article_variants.append(int(article_number))
        except (ValueError, TypeError):
            pass
        query = {"is_article": True, "article_number": {"$in": article_variants}}
        candidates = list(collection.find(query, {
            "law_title": 1, "source": 1, "text": 1, "page": 1,
        }).limit(50))
        non_toc = [c for c in candidates if not _looks_like_toc(c.get("text", ""))]
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


def _verify_single_article(
    db,
    article_number: str,
    paragraph: Optional[str],
    law_hint: str,
) -> Dict[str, Any]:
    result = {
        "article_number": article_number,
        "paragraph": paragraph,
        "law_hint": law_hint,
        "exists": False,
        "is_external": False,
        "matched_doc": None,
        "match_reason": "",
        "candidates_checked": 0,
        "toc_filtered": 0,
    }

    # ═══════════════════════════════════════════════════════════════════════
    # V1.1: Burimet eksterne nga JSON registry
    # ═══════════════════════════════════════════════════════════════════════
    external = find_external_source(law_hint)
    if external:
        result["exists"] = True
        result["is_external"] = True
        result["match_reason"] = "international_treaty_constitutional"
        result["matched_doc"] = {
            "law_title": external["canonical_name"],
            "article_number": article_number,
            "source": external["constitutional_basis"],
            "text_excerpt": external["note"],
            "text_truncated": False,
            "text_full_length": len(external["note"]),
            "page": None,
        }
        result["external_source_id"] = external["id"]
        result["external_category"] = external["category"]
        result["external_short_name"] = external.get("short_name", "")
        return result

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

        # V1.2: Hequr `count_documents(query, limit=1)` — query e panevojshme.
        # `find().limit(20)` më poshtë do të kthejë [] nëse nuk ka.
        candidates = list(collection.find(query, {
            "law_title": 1, "article_number": 1, "source": 1,
            "text": 1, "chunk_index": 1, "page": 1,
        }).limit(20))
        result["candidates_checked"] = len(candidates)

        if not candidates:
            result["match_reason"] = "article_not_in_db"
            return result

        non_toc = [c for c in candidates if not _looks_like_toc(c.get("text", ""))]
        toc_count = len(candidates) - len(non_toc)
        result["toc_filtered"] = toc_count
        if non_toc:
            candidates = non_toc
            if toc_count > 0:
                logger.info(
                    f"🧹 [TOC Filter] Hoqën {toc_count} kandidatë TOC për "
                    f"Neni {article_number}, mbetën {len(non_toc)} real"
                )
        elif toc_count > 0:
            logger.warning(
                f"⚠️ [TOC Filter] Të gjithë kandidatët për Neni {article_number} "
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
                result["alternative_laws"] = sorted(law_titles)
            return result

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

        logger.info(
            f"🔎 [MULTI-LAW] Neni {article_number} me hint='{law_hint}' "
            f"nuk u gjet direkt — provo strategji alternative..."
        )

        successor_info = _get_successor_law(law_hint)
        if successor_info:
            successor_result = _try_successor_law(
                db, article_number, paragraph, law_hint, successor_info
            )
            if successor_result and successor_result.get("exists"):
                return successor_result

        other_laws = _check_exists_in_other_laws(db, article_number)
        if other_laws:
            result["match_reason"] = "law_hint_no_match_but_exists_elsewhere"
            result["exists"] = False
            result["alternative_laws"] = other_laws
            return result

        result["match_reason"] = "law_hint_no_match"
        return result

    except Exception as e:
        logger.warning(f"⚠️ [_verify_single_article] Error: {e}")
        result["match_reason"] = f"error:{type(e).__name__}"
        return result


def verify_articles(db, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not articles:
        return []
    results = []
    for article in articles:
        # V1.2: .get() — skip nëse mungon numri
        art_num = (article.get("number") or "").strip()
        if not art_num:
            logger.warning("⚠️ [verify_articles] Entry pa 'number' — skip")
            continue
        verification = _verify_single_article(
            db, art_num, article.get("paragraph"),
            article.get("law_hint", ""),
        )
        verification["context"] = article.get("context", "")
        verification["sentence"] = article.get("sentence", "")
        results.append(verification)

    # V1.2: .get() për robustness
    verified = sum(1 for r in results if r.get("exists"))
    successor_matches = sum(
        1 for r in results
        if r.get("match_reason", "").startswith("found_in_successor_law")
    )
    alias_matches = sum(
        1 for r in results
        if "abbrev_alias" in r.get("match_reason", "")
        or "abbrev_match_alias" in r.get("match_reason", "")
    )
    # V1.1: External (KEDNJ, OKB, Hagë) — ndajmë nga unverified
    external_matches = sum(
        1 for r in results
        if r.get("is_external") is True
    )
    external_count = external_matches
    alternative_found = sum(
        1 for r in results
        if r.get("match_reason") == "law_hint_no_match_but_exists_elsewhere"
    )
    compound_matches = sum(
        1 for r in results
        if r.get("match_reason", "").startswith("compound_abbrev_")
    )

    # Not-found = nuk ekziston në DB, nuk është traktat
    not_found = sum(
        1 for r in results
        if not r.get("exists")
        and not r.get("is_external")
        and r.get("match_reason") != "law_hint_no_match_but_exists_elsewhere"
    )

    logger.info(
        f"📚 [MONGO_VERIFIER V1.2] Articles: {len(results)} total, "
        f"{verified} verified "
        f"({external_count} external treaties, "
        f"{successor_matches} in successor laws, "
        f"{alias_matches} via alias, {compound_matches} via compound abbrev), "
        f"{alternative_found} exist elsewhere (wrong hint), "
        f"{not_found} not found"
    )
    return results