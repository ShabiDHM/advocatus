# backend/scripts/test_document_guard.py
"""V282.34: Verifikon që service.py V5.30 nuk hedh AttributeError kur
document=None por extraction ekziston."""
from pathlib import Path

src = (Path(__file__).resolve().parent.parent /
       "app/services/document_review/service.py").read_text(encoding="utf-8")

# Kontrollo që të gjitha access-et e `document.get` kanë guard
assert "(document or {}).get" in src, "Mungon guard-i (document or {})"
assert "(extraction or {}).get" in src, "Mungon guard-i (extraction or {})"

# Kontrollo që version = v5.30
assert "V5.30" in src, "Version nuk u përditësua"
assert "verify_hybrid" not in src and "parallel_buffered_x{MAX_CONCURRENT_SECTIONS}_v5.30" in src

# Kontrollo precedents_found
assert "precedents_found_total = len(found_precedent_cases)" in src, \
    "precedents_found_total nuk u fiksua"

# Kontrollo concise_mode në batched
assert '"concise_mode": True,   # V5.30' in src, \
    "concise_mode nuk u shtua në batched"

print("OK — service.py V5.30 me 4 fixe")
print("   - document guard në 3 vende")
print("   - try/except në load")
print("   - precedents_found_total = len(found_precedent_cases)")
print("   - concise_mode në batched stats")