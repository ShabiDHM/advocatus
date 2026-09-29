# FILE: backend/scripts/test_acronyms.py
# PHOENIX PROTOCOL - ACRONYMS TEST V1.0
#
# Teston zgjidhjen e akronimeve (KPRK, KPPRK, LPK, etj.)
# që janë shkaku i gabimeve 404 për /laws/article.

import os
import sys

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from app.core.db import get_db_instance
from app.api.endpoints.laws_pkg.laws_dictionary import (
    _normalize_hallucinated_title,
    _expand_acronym,
    _load_acronyms,
    clear_canonical_title_cache,
)


def main():
    print("═" * 75)
    print("ACRONYMS TEST")
    print("═" * 75)

    # 1. Ngarko akronimet
    acronyms = _load_acronyms()
    print(f"\n[1] Acronyms loaded: {len(acronyms)}")
    for k in sorted(acronyms.keys())[:10]:
        print(f"    {k} → {acronyms[k][:60]}...")

    # 2. Test expansion pa DB
    print(f"\n[2] Expansion test (pa DB):")
    test_acronyms = ["KPRK", "KPPRK", "KPPK", "LPK", "LMD", "LSHT", "LPP",
                     "KPS", "PSRK", "KDM", "KUSHTETUTA", "LIGJI I PUNËS"]
    for acr in test_acronyms:
        expanded = _expand_acronym(acr)
        marker = "✓" if expanded else "✗"
        if expanded:
            print(f"    {marker} '{acr}' → '{expanded[:60]}...'")
        else:
            print(f"    {marker} '{acr}' → (nuk u zgjidh)")

    # 3. Test me DB real
    print(f"\n[3] Normalization me DB:")
    db = get_db_instance()
    clear_canonical_title_cache()

    test_titles = [
        "KPRK", "KPPRK", "KPPK", "LPK", "LMD", "LSHT", "LPP",
        "KPS", "PSRK", "KDM", "KUSHTETUTA", "LIGJI I PUNËS",
        "Ligji për Prokurorinë Speciale",
        "KODI NR. 06 L 074 KODI PENAL I REPUBLIKËS SË KOSOVËS",
    ]

    for t in test_titles:
        result = _normalize_hallucinated_title(t, "", db=db)
        marker = "✓" if result and result != t else "✗"
        print(f"    {marker} '{t}'")
        print(f"       → '{result[:70]}...'")

    # 4. Test /article flow manual
    print(f"\n[4] Simulim /article flow:")
    coll = db["legal_knowledge_base"]

    for user_input, article_num in [
        ("KPRK", "383"),
        ("KPPRK", "79"),
        ("LPK", "360"),
        ("LMD", "382"),
    ]:
        mapped = _normalize_hallucinated_title(user_input, article_num, db=db)

        # Simulo query-n
        art_variants = [article_num, f"{article_num}."]
        if article_num.isdigit():
            art_variants.append(int(article_num))

        doc = coll.find_one({
            "article_number": {"$in": art_variants},
            "is_article": True,
            "law_title": {"$regex": re.escape(mapped), "$options": "i"},
        })

        if doc:
            title = (doc.get("law_title") or "")[:60]
            print(f"    ✓ '{user_input}' Neni {article_num} → {title}")
        else:
            print(f"    ✗ '{user_input}' Neni {article_num} → NUK U GJET")

    print()
    print("═" * 75)
    print("✅ Test përfundoi")
    print("═" * 75)


if __name__ == "__main__":
    import re
    main()