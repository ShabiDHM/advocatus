# backend/scripts/test_whitelist_regex.py
"""V282.34: Verifikon që regex-i i artikujve kap Nenet/Nene/Nenët."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.rag.context_builder import (
    _ARTICLE_RE, _ARTICLE_ABBREV_RE, _ARTICLE_LAWNUM_RE,
)

cases_re = [
    ("Neni 5", "5"),
    ("Nenit 5", "5"),
    ("Nenin 5", "5"),
    ("Nenët 5", "5"),   # me diaeresis
    ("Nenet 5", "5"),   # pa diaeresis ← BUG-i i vjetër
    ("Nene 5", "5"),    # plural i pacaktuar
]

fails = 0
for text, expected in cases_re:
    m = _ARTICLE_RE.search(text)
    got = m.group(1) if m else None
    ok = (got == expected)
    fails += 0 if ok else 1
    print(f"{'OK  ' if ok else 'FAIL'} _ARTICLE_RE: {text!r:15} → {got!r} (pritet {expected!r})")

# _ARTICLE_ABBREV_RE: "Nenit 5 i KPRK"
for variant in ["Nenit", "Nenet", "Nenët"]:
    t = f"{variant} 5 i KPRK"
    m = _ARTICLE_ABBREV_RE.search(t)
    ok = m and m.group(1) == "5" and m.group(2).upper() == "KPRK"
    fails += 0 if ok else 1
    print(f"{'OK  ' if ok else 'FAIL'} _ARTICLE_ABBREV_RE: {t!r}")

# _ARTICLE_LAWNUM_RE: "Nenet 5 i Ligjit Nr. 06/L-074"
for variant in ["Nenet", "Nenët", "Nene"]:
    t = f"{variant} 5 i Ligjit Nr. 06/L-074"
    m = _ARTICLE_LAWNUM_RE.search(t)
    ok = m and m.group(1) == "5"
    fails += 0 if ok else 1
    print(f"{'OK  ' if ok else 'FAIL'} _ARTICLE_LAWNUM_RE: {t!r}")

print(f"\n{'=' * 60}\nTOTAL FAILS: {fails}\n{'=' * 60}")
sys.exit(1 if fails else 0)