# FILE: backend/scripts/test_precedent_regex.py
"""
V282.34: Teste për _detect_specific_precedent_query.
T1 = false positives (duhet False)
T2 = real precedent (duhet True)
T3 = morfologji/format (duhet True)
"""
import sys
from pathlib import Path

# scripts/ është brenda backend/ → parent.parent = backend/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.albanian_rag_service import _detect_specific_precedent_query

# T1: false positives (duhet False)
fp_cases = [
    "Kush janë të dyshuarit?",
    "Trego precedentët supremë për dhunë në familje",
    "Çfarë thotë CALL 123/456?",          # CA brenda CALL
    "Sa është vlera e AC?",                # AC e vetme pa numër
    "PILLOW 5/2024 test",                  # P brenda fjalës
    "Analizo këtë dokument.",              # asnjë precedent
]

# T2: real precedent (duhet True)
real_cases = [
    "Çfarë thotë Gjykata Supreme në vendimin PML.Nr.185/2025?",
    "Trego Rev.nr.42/2023",
    "P.nr.100/2022 precedent",
    "C.nr.50/2021",
    "PP.II.nr.10/2024",
]

# T3: morfologji/format (duhet True)
morph_cases = [
    "PML Nr. 185/2025",       # hapësirë vend dot
    "PML.Nr185/2025",         # pa pikë pas nr
    "AC.7/2024",              # dy-shkronjësh valid
]

fails = 0

print("\n=== T1: FALSE POSITIVES (duhet False) ===")
for c in fp_cases:
    r = _detect_specific_precedent_query(c)
    ok = (r is False)
    fails += 0 if ok else 1
    print(f"{'OK  ' if ok else 'FAIL'} -> {str(r):5} | {c!r}")

print("\n=== T2: REAL PRECEDENT (duhet True) ===")
for c in real_cases:
    r = _detect_specific_precedent_query(c)
    ok = (r is True)
    fails += 0 if ok else 1
    print(f"{'OK  ' if ok else 'FAIL'} -> {str(r):5} | {c!r}")

print("\n=== T3: MORPHOLOGY (duhet True) ===")
for c in morph_cases:
    r = _detect_specific_precedent_query(c)
    ok = (r is True)
    fails += 0 if ok else 1
    print(f"{'OK  ' if ok else 'MISS'} -> {str(r):5} | {c!r}")

print(f"\n{'=' * 60}\nTOTAL FAILS: {fails}\n{'=' * 60}")
sys.exit(1 if fails else 0)