# backend/scripts/test_hallucination_filter_regex.py
"""V282.34: Verifikon që regex ordering nuk ka ndryshuar sjellje."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.pillars.hallucination_filter import (
    KOSOVO_CASE_NUMBER_REGEX,
    HallucinationFilter,
)

cases = [
    # (input, duhet match)
    ("PML.nr.185/2025", True),
    ("PML 185/2025", True),
    ("PML nr 185/2025", True),
    ("Rev.nr.45/2023", True),
    ("REV.45/2023", True),
    ("PKR.nr.12/2024", True),
    ("KMLP.nr.7/2023", True),
    ("ANR.nr.3/2024", True),
    ("AC.nr.100/2024", True),
    ("CA.nr.50/2024", True),
    ("Cn.nr.5/2024", True),
    ("C.nr.5/2024", True),
    ("A.nr.5/2024", True),
    ("P.nr.5/2024", True),

    # Jo-matches (duhet False)
    ("Kodi Penal", False),
    ("Neni 5", False),
    ("2024", False),
    ("PML", False),  # pa numër
]

fails = 0
for text, expected in cases:
    actual = bool(KOSOVO_CASE_NUMBER_REGEX.search(text))
    ok = (actual == expected)
    fails += 0 if ok else 1
    print(f"{'OK  ' if ok else 'FAIL'} {text!r:25} → {actual} (pritet {expected})")

# Kontroll specifik për bug-un e mundshëm Cn/C
m = KOSOVO_CASE_NUMBER_REGEX.search("Cn.nr.5/2024")
assert m and m.group(0) == "Cn.nr.5/2024", f"Cn match i gabuar: {m.group(0) if m else None}"
print(f"\nOK 'Cn.nr.5/2024' match i plotë (jo vetëm 'C')")

# Test normalize_precedent equivalence
norm_cases = [
    ("PML nr 123/2024", "PML 123/2024"),
    ("PML.nr.123/2024", "PML 123/2024"),
    ("PML 123 / 2024", "PML 123/2024"),
    ("Rev. 45/2023", "REV 45/2023"),
]
for inp, expected in norm_cases:
    out = HallucinationFilter.normalize_precedent(inp)
    assert out == expected, f"normalize: {inp!r} → {out!r}, pritej {expected!r}"
print("OK normalize_precedent V10.1 ruajtur")

print(f"\n{'=' * 60}\nTOTAL FAILS: {fails}\n{'=' * 60}")
sys.exit(1 if fails else 0)