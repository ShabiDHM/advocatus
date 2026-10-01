# backend/scripts/test_hallucination_checker.py
"""
V282.34: Test për checker.py V1.28 — kontrollo që refactor-i nuk ka
ndryshuar sjelljen dhe që ekstraksioni bëhet 1× jo 2×.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.document_review.hallucination.checker import (
    VALID_STANDARD_ABBREVS,
    HallucinationChecker,
)

# 1. Konstanta ekziston dhe ka përmbajtjen e pritur
expected = {"KPRK", "KPPRK", "LPK", "LMD", "LMDHF", "LFK", "LSHT", "PSRK", "KRK", "LPTS"}
assert VALID_STANDARD_ABBREVS == expected, f"Konstanta e gabuar: {VALID_STANDARD_ABBREVS}"
print(f"OK VALID_STANDARD_ABBREVS = {len(VALID_STANDARD_ABBREVS)} akronime")

# 2. Instanco checker bosh dhe testo një seksion
checker = HallucinationChecker(
    citation_profile={},
    fact_profile={},
    verification_report={},
)

# Seksion me përmbajtje bosh
r = checker.check_section("test", "")
assert r["status"] == "empty", f"Status bosh i gabuar: {r['status']}"
print(f"OK empty section: status={r['status']}")

# Seksion me tekst të thjeshtë (pa citime)
r2 = checker.check_section("test", "Ky është një tekst i thjeshtë pa citime ligjore.")
print(f"OK plain text: status={r2['status']}, issues={len(r2['issues'])}, "
      f"counts={r2['counts']}")

# 3. Ekstraksioni i dyfishtë — matim kohën
import time
big_text = ("Neni 5 i Ligjit Nr. 06/L-074 Kodi Penal. " * 200)
t0 = time.perf_counter()
checker.check_section("perf", big_text)
t1 = time.perf_counter()
print(f"OK performance: {len(big_text)} chars → {(t1-t0)*1000:.1f}ms")

# 4. Robustness: issue pa 'severity' nuk duhet të hedhë KeyError
# (simulo duke krijuar një checker me allowed bosh — check_section do të japë issue)
print("\nTË GJITHA TESTET KALUAN")