# scripts/test_verify_case_numbers.py
# T1 false-positive + T2 real + T3 morphology variants
# Run: cd backend && python scripts/test_verify_case_numbers.py

import os
import sys

# V1.1: Sigurohu që 'app' paketa është e importueshme kur ekzekutohet
# direkt nga scripts/ (pa -m).
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(_THIS_DIR)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

import logging
from app.core.db import get_db
from app.services.document_review.mongo_verifier import verify_case_numbers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

db = get_db()

TESTS = {
    "T1_FALSE_POSITIVE (duhet: 0 precedentë)": [
        {"case_number": "ZZZ.Nr.9999/9999", "is_likely_own": False},
        {"case_number": "FAKE.Nr.1/2025", "is_likely_own": False},
    ],
    "T2_REAL (duhet: 7 precedentë)": [
        {"case_number": "PML.Nr.185/2025", "is_likely_own": False},
        {"case_number": "PML.Nr.122/2025", "is_likely_own": False},
        {"case_number": "PML.Nr.352/2025", "is_likely_own": False},
        {"case_number": "PML.Nr.752/2024", "is_likely_own": False},
        {"case_number": "PML.Nr.272/2025", "is_likely_own": False},
        {"case_number": "Rev.Nr.252/2025", "is_likely_own": False},
        {"case_number": "Rev.Nr.570/2021", "is_likely_own": False},
    ],
    "T3_MORPHOLOGY (duhet: të gjithë found)": [
        {"case_number": "PML.185/2025", "is_likely_own": False},       # pa Nr.
        {"case_number": "PML Nr 185 2025", "is_likely_own": False},    # hapësira
        {"case_number": "PML.Nr.185/25", "is_likely_own": False},      # vit 2-shifror
    ],
}

for label, cases in TESTS.items():
    print(f"\n{'=' * 72}\n{label}\n{'=' * 72}")
    results = verify_case_numbers(db, cases)
    for r in results:
        mark = "✅" if r["is_precedent"] else "❌"
        print(
            f"  {mark} {r['case_number']:25s} → "
            f"precedent={r['is_precedent']:<5}  reason={r['match_reason']}"
        )