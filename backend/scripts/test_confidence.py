# FILE: backend/scripts/test_confidence.py
# PHOENIX PROTOCOL - CONFIDENCE TEST V1.0
#
# Teston që confidence për /laws/article reflekton realisht input-in.
# Verifikon fix-in V208.5 (45% për akronime).

import os
import sys

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from app.core.db import get_db_instance
from app.api.endpoints.laws_pkg.laws_dictionary import (
    _normalize_hallucinated_title,
    clear_canonical_title_cache,
)
from app.api.endpoints.laws_pkg.laws_query_router import _infer_match_type


def main():
    print("═" * 75)
    print("CONFIDENCE TEST — V208.5")
    print("═" * 75)

    db = get_db_instance()
    clear_canonical_title_cache()

    # (input, expected_min_score)
    # min_score reflekton: exact→0.95+, code→0.85+, substring→0.70+, word→0.55+
    tests = [
        # (input, neni, prit_level, prit_score_min)
        ("KPRK", "383", "HIGH/MEDIUM", 0.70),
        ("KPPRK", "79", "HIGH/MEDIUM", 0.70),
        ("LPK", "360", "HIGH/MEDIUM", 0.70),
        ("LMD", "382", "HIGH/MEDIUM", 0.70),
        ("KODI PENAL", "383", "HIGH/MEDIUM", 0.70),
        ("KODI NR. 06 L 074 KODI PENAL I REPUBLIKËS SË KOSOVËS (KONSOLIDUAR)", "383", "HIGH", 0.90),
        ("LIGJI NR. 03 L 006 PËR PROCEDURËN KONTESTIMORE", "360", "HIGH", 0.90),
    ]

    print("\n" + "─" * 75)
    print("TEST I INPUT-EVE")
    print("─" * 75)

    for user_input, art_num, expected_level, min_score in tests:
        # 1. Norm
        mapped = _normalize_hallucinated_title(user_input, art_num, db=db)

        # 2. Gjej canonical (simulo /article)
        projection = {"law_title": 1}
        art_variants = [art_num, f"{art_num}."]
        if art_num.isdigit():
            art_variants.append(int(art_num))

        doc = db.legal_knowledge_base.find_one(
            {
                "article_number": {"$in": art_variants},
                "is_article": True,
                "law_title": {"$regex": f"^{_escape_regex(mapped)}$", "$options": "i"},
            },
            projection,
        )
        if not doc:
            doc = db.legal_knowledge_base.find_one(
                {
                    "article_number": {"$in": art_variants},
                    "is_article": True,
                    "law_title": {"$regex": _escape_regex(mapped), "$options": "i"},
                },
                projection,
            )

        if not doc:
            print(f"  ✗ '{user_input}' Neni {art_num}")
            print(f"      NUK U GJET dokumenti (mapped: '{mapped[:50]}')")
            continue

        canonical = doc.get("law_title", "")

        # 3. Infer match_type me fix-in V208.5
        match_type = _infer_match_type(canonical, mapped)

        # 4. Llogarit score
        base_score = {
            "exact": 0.95,
            "code": 0.85,
            "substring": 0.70,
            "word": 0.55,
            "unknown": 0.40,
        }.get(match_type, 0.30)
        base_score += 0.05  # article_matches

        level = "HIGH" if base_score >= 0.85 else (
            "MEDIUM" if base_score >= 0.55 else (
                "LOW" if base_score > 0 else "NONE"
            )
        )

        passed = base_score >= min_score
        marker = "✓" if passed else "✗"

        print(f"  {marker} '{user_input}' Neni {art_num}")
        print(f"      mapped:    {mapped[:60]}")
        print(f"      canonical: {canonical[:60]}")
        print(f"      match:     {match_type}")
        print(f"      score:     {base_score:.2f} ({level})  [prit >= {min_score}]")
        print()

    print("═" * 75)
    print("✅ Test përfundoi")
    print("═" * 75)


def _escape_regex(s: str) -> str:
    import re
    return re.escape(s)


if __name__ == "__main__":
    main()