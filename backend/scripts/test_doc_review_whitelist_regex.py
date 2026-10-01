# backend/scripts/test_doc_review_whitelist_regex.py
"""V282.34: Verifikon që whitelist regex pranon 08/L-185 DHE 2004/32."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.rag.document_review_post_processor import (
    _LAW_NUMBER_WHITELIST_RE,
    _ARTICLE_OUTPUT_RE,
)

fails = 0

# ─── T1: whitelist regex pranon të dyja format ───
print("\n=== T1: _LAW_NUMBER_WHITELIST_RE ===")
cases = [
    ("08/L-185", True),
    ("03/L-006", True),
    ("04/L-077", True),
    ("2004/32", True),
    ("1999/1", True),
    ("invalid", False),
    ("foo/bar", False),
    ("", False),
]
for text, expected in cases:
    got = bool(_LAW_NUMBER_WHITELIST_RE.match(text))
    ok = (got == expected)
    fails += 0 if ok else 1
    print(f"{'OK  ' if ok else 'FAIL'} {text!r:15} → {got} (pritet {expected})")

# ─── T2: artikujt pranojnë Nenet/Nene ───
print("\n=== T2: _ARTICLE_OUTPUT_RE ===")
for variant in ["Neni", "Nenit", "Nenin", "Nenët", "Nenet", "Nene"]:
    text = f"{variant} 5"
    m = _ARTICLE_OUTPUT_RE.search(text)
    ok = m and m.group(1) == "5"
    fails += 0 if ok else 1
    print(f"{'OK  ' if ok else 'FAIL'} {text!r:15} → {m.group(1) if m else None}")

print(f"\n{'=' * 60}\nTOTAL FAILS: {fails}\n{'=' * 60}")
sys.exit(1 if fails else 0)