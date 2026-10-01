# FILE: backend/scripts/test_abbreviations_refactor.py
"""
V282.34: Test refactor për abbreviations.py V1.1 (DRY refactor).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.document_review.mongo_verifier.abbreviations import (
    _generate_abbreviation_from_title,
    _generate_full_abbreviation_from_title,
)

# Rastet reale (vlerat e pritura kalkuluar manualisht nga logjika)
cases = [
    # "Ligji Nr. 06/L-074 Kodi Penal i Republikës së Kosovës"
    # → heq numrin → ligji kodi penal i republikes se kosoves
    # → filtro skip (i, se) → ligji kodi penal republikes kosoves = 5 fjalë
    # → "LKPRK"
    ("Ligji Nr. 06/L-074 Kodi Penal i Republikës së Kosovës",
     "LKPRK", "LKPRK"),

    # "Ligji për Marrëdhëniet e Detyrimeve"
    # → ligji per marredheniet e detyrimeve
    # → filtro skip (e) → ligji per marredheniet detyrimeve
    # → "LPMD"  — por "për"/"per" nuk është në ABBREV_SKIP_WORDS!
    # Kontroll: ABBREV_SKIP_WORDS nuk përmban "për"/"per"? Lista:
    #   për, per, dhe, ose, ... — PO, përmban.
    # → ligji marredheniet detyrimeve = 3 fjalë → "LMD"
    ("Ligji për Marrëdhëniet e Detyrimeve",
     "LMD", "LMD"),

    # "Ligji për Familjen i Kosovës"
    # → ligji per familjen i kosoves
    # → filtro skip (për, per, i) → ligji familjen kosoves = 3 fjalë
    # → "LFK"
    ("Ligji për Familjen i Kosovës",
     "LFK", "LFK"),

    # Kufiri 6-fjalësh: 7 fjalë domethënëse → short pritet [:6]
    ("Ligji për Mbrojtjen e Fëmijëve nga Dhuna në Familje dhe Shkolla",
     None, None),  # kontrolle dinamike më poshtë
]

fails = 0
for title, exp_short, exp_full in cases:
    if exp_short is None:
        # Rast dinamik: verifiko vetëm që short <= 6 chars dhe full >= short
        short = _generate_abbreviation_from_title(title)
        full = _generate_full_abbreviation_from_title(title)
        ok = (len(short) <= 6) and (len(full) >= len(short)) and (full.startswith(short))
        fails += 0 if ok else 1
        print(f"{'OK  ' if ok else 'FAIL'} dynamic: {title[:45]:47} -> short={short!r} full={full!r}")
        continue

    short = _generate_abbreviation_from_title(title)
    full = _generate_full_abbreviation_from_title(title)
    ok_short = (short == exp_short)
    ok_full = (full == exp_full)
    fails += 0 if ok_short else 1
    fails += 0 if ok_full else 1
    print(f"{'OK  ' if ok_short else 'FAIL'} short: {title[:45]:47} -> {short!r} (pritet {exp_short!r})")
    print(f"{'OK  ' if ok_full else 'FAIL'} full : {title[:45]:47} -> {full!r} (pritet {exp_full!r})")

# Equivalence: default == max_words=6
for title, _, _ in cases:
    a = _generate_abbreviation_from_title(title)
    b = _generate_abbreviation_from_title(title, max_words=6)
    assert a == b, f"Default != explicit-6 për {title!r}: {a!r} vs {b!r}"
print("\nEquivalence (default == max_words=6): OK")

# Equivalence: max_words=0 == full
for title, _, _ in cases:
    a = _generate_abbreviation_from_title(title, max_words=0)
    b = _generate_full_abbreviation_from_title(title)
    assert a == b, f"max_words=0 != full për {title!r}: {a!r} vs {b!r}"
print("Equivalence (max_words=0 == full): OK")

print(f"\n{'=' * 50}\nTOTAL FAILS: {fails}\n{'=' * 50}")
sys.exit(1 if fails else 0)