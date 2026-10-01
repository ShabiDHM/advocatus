# FILE: backend/scripts/test_chat_post_processor.py
"""
V282.34: Verifikon regex diaeresis në chat_post_processor V2.5.
Kontrollon që "Nenet"/"Nene" (pa ë) tani match-ohen si "Neni"/"Nenët".
"""
import sys
from pathlib import Path

# Shto backend/ në sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.rag.chat_post_processor import (
    _ARTICLE_OUTPUT_RE,
    _extract_articles_normalized,
    _find_missing_articles,
)

fails = 0

# ─── T1: regex match-on Nenet/Nene ───
print("\n=== T1: _ARTICLE_OUTPUT_RE ===")
for variant in ["Neni", "Nenit", "Nenin", "Nenët", "Nenet", "Nene"]:
    text = f"{variant} 5"
    m = _ARTICLE_OUTPUT_RE.search(text)
    ok = m and m.group(1) == "5"
    fails += 0 if ok else 1
    print(f"{'OK  ' if ok else 'FAIL'} {text!r:15} → {m.group(1) if m else None}")

# ─── T2: _extract_articles_normalized kap Nenet ───
print("\n=== T2: extract normalizuar ===")
for text, expected in [
    ("Neni 5 dhe Neni 6", {"5", "6"}),
    ("Nenet 5, 6 dhe 7", {"5"}),              # vetëm 5 (regex match-on 'Nenet 5')
    ("Nenet 5 dhe Nene 12", {"5", "12"}),
    ("Sipas Nenit 145 dhe Nenet 200", {"145", "200"}),
]:
    got = set(_extract_articles_normalized(text))
    ok = got == expected
    fails += 0 if ok else 1
    print(f"{'OK  ' if ok else 'FAIL'} {text!r:35} → {got} (pritet {expected})")

# ─── T3: _find_missing_articles kap hallucinations "Nenet" ───
print("\n=== T3: find_missing me Nenet ===")
whitelist = {"articles": ["5", "6"]}
out = "Sipas Nenet 5 dhe Nene 99 kjo është e saktë."
missing = _find_missing_articles(out, whitelist)
ok = "99" in missing and "5" not in missing and "6" not in missing
fails += 0 if ok else 1
print(f"{'OK  ' if ok else 'FAIL'} missing → {missing} (duhet të përmbajë '99')")

print(f"\n{'=' * 60}\nTOTAL FAILS: {fails}\n{'=' * 60}")
sys.exit(1 if fails else 0)