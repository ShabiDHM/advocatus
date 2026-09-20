# FILE: backend/_tests_dev/_test_chat_post.py
"""Verifikon chat_post_processor V2.2: Neni 1.2 nuk eshte me false-positive."""
from app.services.rag.chat_post_processor import (
    build_correction_section,
    _find_missing_articles,
)

# Whitelist sic do te krijohej nga AlbanianRAGService
whitelist = {
    "laws_number": ["03/L-182"],
    "articles": ["1", "5", "42"],   # post-V1.5, te normalizuara
    "articles_display": ["Neni 1", "Neni 5", "Neni 42"],
    "laws_by_file": {"vendimi.pdf": ["03/L-182"]},
    "source_filter": "judicial_only",
}

# TEST 1: output i paster me "Neni 1.2" (i cili duhet te normalizohet ne "1")
clean = "Sipas Nenit 1.2 te Ligjit Nr. 03/L-182 dhe Nenit 42 te ligjit, vendimi..."
missing = _find_missing_articles(clean, whitelist)
print("TEST 1 — Neni 1.2 normalizuar")
print(f"  missing: {missing}")
assert missing == [], f"Pritet [], mori {missing}"

# TEST 2: output me nen te rreme
dirty = "Sipas Nenit 99 dhe Nenit 1.2 te Ligjit Nr. 03/L-182..."
missing = _find_missing_articles(dirty, whitelist)
print("TEST 2 — Neni 99 i rreme")
print(f"  missing: {missing}")
assert missing == ["99"], f"Pritet ['99'], mori {missing}"

# TEST 3: correction section i plote
sec = build_correction_section(dirty, whitelist)
print("TEST 3 — Correction section")
print(f"  length: {len(sec)}")
assert "Neni 99" in sec
assert "Neni 1" not in sec.split("❌")[1].split("✅")[0] if "❌" in sec else True

print("[OK] Te gjitha testet kaluan.")