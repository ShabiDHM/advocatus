# FILE: backend/app/services/document_review/mongo_verifier/orchestrator.py
# PHOENIX PROTOCOL - MONGO VERIFIER / ORCHESTRATOR V1.1
#
# V1.1: Shtuar stat `articles_external` për traktate ndërkombëtare
#       (KEDNJ, OKB, Hagë) — ndajmë nga `articles_not_found`.
#       Kjo lejon frontend-in të dallojë:
#         - articles_external → burim i njohur (KEDNJ/OKB/Hagë)
#         - articles_not_found → nuk ekziston në DB
#
# V1.0: Ekstraktuar nga mongo_verifier.py V2.11 (pa ndryshim logjike).

import logging
from typing import Any, Dict

from .articles import verify_articles
from .laws import verify_law_numbers
from .case_numbers import verify_case_numbers

logger = logging.getLogger(__name__)


def verify_all(db, citation_profile: Dict[str, Any]) -> Dict[str, Any]:
    if not citation_profile:
        return {
            "articles": [], "laws_by_number": [],
            "case_numbers": [], "stats": {},
        }

    articles = verify_articles(db, citation_profile.get("articles", []))
    laws_by_number = verify_law_numbers(db, citation_profile.get("laws_by_number", []))
    case_numbers = verify_case_numbers(db, citation_profile.get("case_numbers", []))

    # V1.1: Numërime të reja për traktate eksterne
    articles_external = sum(
        1 for a in articles
        if a.get("is_external") is True
    )
    articles_not_found = sum(
        1 for a in articles
        if not a["exists"] and not a.get("is_external")
    )

    stats = {
        "articles_total": len(articles),
        "articles_verified": sum(1 for a in articles if a["exists"]),
        "articles_not_found": articles_not_found,
        # V1.1
        "articles_external": articles_external,
        "articles_external_kednj": sum(
            1 for a in articles
            if a.get("external_source_id") == "KEDNJ"
        ),
        "articles_external_okb": sum(
            1 for a in articles
            if a.get("external_source_id") == "OKB_FEMIJES"
        ),
        "articles_external_haga": sum(
            1 for a in articles
            if a.get("external_source_id") == "HAGA_FEMIJET"
        ),
        "articles_in_successor_laws": sum(
            1 for a in articles
            if a.get("match_reason", "").startswith("found_in_successor_law")
        ),
        "articles_via_alias": sum(
            1 for a in articles
            if "abbrev_alias" in a.get("match_reason", "")
            or "abbrev_match_alias" in a.get("match_reason", "")
        ),
        "articles_via_compound_abbrev": sum(
            1 for a in articles
            if a.get("match_reason", "").startswith("compound_abbrev_")
        ),
        "articles_via_international_treaty": articles_external,  # backward compat
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
        f"📚 [MONGO_VERIFIER V1.1] Complete: "
        f"articles {stats['articles_verified']}/{stats['articles_total']} "
        f"({stats['articles_external']} external treaties, "
        f"+{stats['articles_in_successor_laws']} in successor laws, "
        f"{stats['articles_via_alias']} via alias, "
        f"{stats['articles_via_compound_abbrev']} via compound abbrev), "
        f"not_found={stats['articles_not_found']}, "
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