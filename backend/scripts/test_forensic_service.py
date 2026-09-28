# FILE: backend/scripts/test_forensic_service.py
# Test për forensic_service — lexon DB, xhiron engine, formon block.

import os
import sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(_THIS_DIR)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

import logging
from app.services.document_review.forensic_service import (
    resolve_profile,
    run_forensic_analysis,
    ForensicAnalysisResult,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


# ═══════════════════════════════════════════════════════════════════════════
# TEST 1 — resolve_profile
# ═══════════════════════════════════════════════════════════════════════════

print("=" * 72)
print("TEST 1 — resolve_profile (zero hardcoding)")
print("=" * 72)

cases = [
    ("Vendim Gjyqësor", "judicial_decision"),
    ("Kallëzim Penal", "criminal_complaint"),
    ("Kontratë", "civil_contract"),
    ("Padi Civile", "civil_contract"),
    ("Diçka E Panjohur", "generic"),
    (None, "generic"),
    ("", "generic"),
]

for doc_type, expected in cases:
    actual = resolve_profile(doc_type)
    status = "✓" if actual == expected else "✗"
    print(f"  {status} '{doc_type}' → '{actual}' (pritet '{expected}')")
    assert actual == expected, f"FAIL: {doc_type} → {actual}, pritet {expected}"

print("✓ TEST 1 KALOI")


# ═══════════════════════════════════════════════════════════════════════════
# TEST 2 — run_forensic_analysis me DB (live)
# ═══════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 72)
print("TEST 2 — run_forensic_analysis (DB live)")
print("=" * 72)

try:
    from app.core.db import get_db
    db = get_db()

    # Përdor case_id nga rasti i njohur (ose merr nje ekzistues)
    TEST_CASE_ID = os.getenv("TEST_CASE_ID", "")

    if not TEST_CASE_ID:
        # Kërko një rast me dokumente
        case = db.cases.find_one({}, {"_id": 1})
        if case:
            TEST_CASE_ID = str(case["_id"])

    if not TEST_CASE_ID:
        print("⚠️ TEST 2 SKIPPED — s'ka case në DB.")
    else:
        print(f"Case ID: {TEST_CASE_ID}")

        result = run_forensic_analysis(
            db, TEST_CASE_ID, document_type="Vendim Gjyqësor",
        )

        print(f"\nhas_findings:      {result.has_findings}")
        print(f"profile_used:      {result.profile_used}")
        print(f"documents_scanned: {result.documents_scanned}")
        print(f"flags_total:       {len(result.flags)}")
        print(f"stats:             {result.stats}")

        if result.flags:
            print(f"\nFlamujt (top 5):")
            for f in result.flags[:5]:
                print(f"  [{f.severity.upper()}] {f.rule_id}: {f.message[:100]}")

        if result.block:
            print(f"\nBlock i formuar: {len(result.block)} chars")
            print(f"  Preview: {result.block[:200]}...")

        print("✓ TEST 2 KALOI")

except ImportError as e:
    print(f"⚠️ TEST 2 SKIPPED — {e}")
except Exception as e:
    print(f"❌ TEST 2 dështoi: {e}")
    raise


print("\n" + "=" * 72)
print("TË GJITHA TESTET PËRFUNDUAN")
print("=" * 72)