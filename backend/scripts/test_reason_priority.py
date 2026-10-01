# backend/scripts/test_reason_priority.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.document_review.mongo_verifier.title_matching import _reason_priority

cases = [
    ("compound_abbrev_exact",   99),
    ("compound_abbrev_lcs",     98),  # V1.1
    ("compound_abbrev_partial", 97),  # V1.1
    ("abbrev_generated_exact",  90),
    ("abbrev_generated_prefix", 85),
    ("abbrev_generated_partial", 80),
    ("number_match:06/L-074",   100),
    ("keyword_match:['kodi']",  50),
]

fails = 0
for reason, expected in cases:
    actual = _reason_priority(reason)
    ok = (actual == expected)
    fails += 0 if ok else 1
    print(f"{'OK  ' if ok else 'FAIL'} {reason:35} -> {actual} (pritet {expected})")

# Kontroll konsistence: exact > lcs > partial
assert _reason_priority("compound_abbrev_exact") > \
       _reason_priority("compound_abbrev_lcs") > \
       _reason_priority("compound_abbrev_partial"), \
    "Hierarkia exact > lcs > partial është e prishur!"
print("\nHierarkia compound_abbrev_*: OK")

print(f"\n{'=' * 50}\nTOTAL FAILS: {fails}\n{'=' * 50}")
sys.exit(1 if fails else 0)