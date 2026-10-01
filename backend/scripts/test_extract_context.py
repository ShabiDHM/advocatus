# FILE: backend/scripts/test_extract_context.py
"""
V282.34: Test për has_real_citation_context V1.26.
Verifikon që dead code removal nuk ka ndryshuar sjelljen.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.document_review.hallucination.extract import has_real_citation_context

cases = [
    # (text, value, expected, window)
    ("Neni 5 i Ligjit Nr. 06/L-074.", "5", True, 200),
    ("Sugjerohet Neni 5 për shtim.", "5", False, 200),
    ("Ky tekst nuk përmban numrin.", "5", False, 200),
    ("", "5", False, 200),
    ("Neni 5.", "", False, 200),

    # Dukuritë larg njëra-tjetrës (>2×window) → e para del "real"
    (
        "Neni 5 i Ligjit Nr. 06/L-074. " + ("X" * 500) + " Sugjerohet Neni 5 për shtim.",
        "5", True, 200,
    ),

    # Vetëm sugjerim → False
    (
        "Sugjerohet Neni 5 për shtim. " + ("Y" * 500) + " Më tej tekst.",
        "5", False, 200,
    ),
]

fails = 0
for text, value, expected, window in cases:
    r = has_real_citation_context(text, value, window=window)
    ok = (r == expected)
    fails += 0 if ok else 1
    display = text[:50] if len(text) <= 50 else f"{text[:25]}...{text[-25:]}"
    print(f"{'OK  ' if ok else 'FAIL'} {display!r:55} value={value!r} w={window} -> {r} (pritet {expected})")

print(f"\n{'=' * 60}\nTOTAL FAILS: {fails}\n{'=' * 60}")
sys.exit(1 if fails else 0)