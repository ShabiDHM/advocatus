# FILE: backend/scripts/test_forensic.py
# Test për forensic_extractor + forensic_engine (pa varësi PDF).
# Zero ekstra PDF — fokus në logjikën e ekstraktimit + detektorëve.

import os
import sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(_THIS_DIR)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

import logging
from app.services.document_review.forensic_extractor import extract_forensic_data
from app.services.document_review.forensic_engine import (
    run_forensic_detectors,
    load_forensic_config,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


# ═══════════════════════════════════════════════════════════════════════════
# TEST 1 — Ekstraktori me tekst sintetik
# ═══════════════════════════════════════════════════════════════════════════

SAMPLE_TEXT = """Numri i dokumentit: 05340452
C.nr.385/2024, datë 16.02.2024
AKTVENDIM
I. MIRATOHET kërkesa për urdhërmbrojtje.
Kohëzgjatja: 6 muaj.
Distance 100 metra.
P.nr.869/18, datë 26.05.2021
"""

print("=" * 72)
print("TEST 1 — Ekstraktori me tekst sintetik")
print("=" * 72)

d = extract_forensic_data(SAMPLE_TEXT, "synthetic.pdf")
print(f"doc_numbers:    {d.document_numbers}")
print(f"case_numbers:   {d.case_numbers}")
print(f"own_case:       {d.own_case_number}")
print(f"dates:          {sorted(d.dates_iso)}")
print(f"doc_types:      {d.doc_type_hints}")
print(f"numeric_claims: {[(c.value, c.unit) for c in d.numeric_claims]}")
print(f"sections:       {[(s.marker, s.heading[:40]) for s in d.sections]}")
print(f"full_text:      {len(d.full_text)} chars")
print(f"to_dict keys:   {sorted(d.to_dict().keys())}")

assert "full_text" not in d.to_dict(), "to_dict() NUK duhet të ketë full_text"
assert "05340452" in d.document_numbers
assert "C.nr.385/2024" in d.case_numbers
assert "P.nr.869/2018" in d.case_numbers
assert "2024-02-16" in d.dates_iso
assert "2021-05-26" in d.dates_iso
assert "decision" in d.doc_type_hints
assert any(c.unit == "muaj" and c.value == 6.0 for c in d.numeric_claims)
assert any(c.unit == "metra" and c.value == 100.0 for c in d.numeric_claims)

print("✓ TEST 1 KALOI")


# ═══════════════════════════════════════════════════════════════════════════
# TEST 2 — Config lexohet
# ═══════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 72)
print("TEST 2 — Config lexohet")
print("=" * 72)

cfg = load_forensic_config()
print(f"version:        {cfg.get('version')}")
print(f"rules:          {len(cfg.get('rules', []))}")
print(f"profiles:       {list(cfg.get('profiles', {}).keys())}")

assert cfg.get("version"), "config duhet të ketë version"
assert len(cfg.get("rules", [])) > 0, "config duhet të ketë rules"
assert "judicial_decision" in cfg.get("profiles", {})

print("✓ TEST 2 KALOI")


# ═══════════════════════════════════════════════════════════════════════════
# TEST 3 — Detektori: duplicate_document_number (critical)
# ═══════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 72)
print("TEST 3 — duplicate_document_number (5 seanca me të njëjtin numër)")
print("=" * 72)

# Simulojmë 5 dokumente me të njëjtin numër dokumenti
same_doc_num = "05340452"
docs = []
for i in range(5):
    text = (
        f"Numri i dokumentit: {same_doc_num}\n"
        f"PROCESVERBAL\n"
        f"Datë: {10 + i}.01.2024\n"
        f"C.nr.385/2024\n"
    )
    docs.append(extract_forensic_data(text, f"seanca_{i+1}.pdf"))

flags = run_forensic_detectors(docs, profile="judicial_decision")
print(f"Total flamuj: {len(flags)}")
for f in flags:
    print(f"  [{f.severity.upper()}] {f.rule_id}: {f.message[:100]}")

critical_flags = [f for f in flags if f.severity == "critical"]
assert any(f.rule_id == "duplicate_document_number" for f in critical_flags), \
    "Duhet të kapi numrin e përsëritur të dokumentit"

print("✓ TEST 3 KALOI")


# ═══════════════════════════════════════════════════════════════════════════
# TEST 4 — Detektori: expired_conviction_used (denim i skaduar)
# ═══════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 72)
print("TEST 4 — expired_conviction_used (P.nr.869/18 në 2024)")
print("=" * 72)

text_vendim = """
Numri i dokumentit: 05340452
AKTVENDIM
C.nr.385/2024, datë 16.02.2024
Bazuar në Aktgjykimin P.nr.869/18, datë 26.05.2021
"""
doc = extract_forensic_data(text_vendim, "vendim.pdf")
print(f"case_numbers: {doc.case_numbers}")
print(f"latest_date:  {doc.latest_date}")

flags = run_forensic_detectors([doc], profile="judicial_decision")
print(f"Total flamuj: {len(flags)}")
for f in flags:
    print(f"  [{f.severity.upper()}] {f.rule_id}: {f.message[:100]}")

assert any(f.rule_id == "expired_conviction_used" for f in flags), \
    "Duhet të kapi denimin e skaduar"

print("✓ TEST 4 KALOI")


# ═══════════════════════════════════════════════════════════════════════════
# TEST 5 — Detektori: duplicate_session_dates
# ═══════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 72)
print("TEST 5 — duplicate_session_dates (3 seanca me të njëjtën datë)")
print("=" * 72)

same_date = "19.01.2024"
docs = []
for i in range(3):
    text = (
        f"PROCESVERBAL\n"
        f"Datë: {same_date}\n"
        f"Numri i dokumentit: 0534045{i}\n"
        f"C.nr.385/2024\n"
    )
    docs.append(extract_forensic_data(text, f"seanca_{i+1}.pdf"))

flags = run_forensic_detectors(docs, profile="judicial_decision")
for f in flags:
    print(f"  [{f.severity.upper()}] {f.rule_id}: {f.message[:100]}")

# Kontrollo
has_session_flag = any(f.rule_id == "duplicate_session_dates" for f in flags)
print(f"Ka duplicate_session_dates flag: {has_session_flag}")

print("✓ TEST 5 PËRFUNDOI")


# ═══════════════════════════════════════════════════════════════════════════
# TEST 6 — Detektori: psychiatric_basis_insufficient
# ═══════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 72)
print("TEST 6 — psychiatric_basis_insufficient (raport pa ekzaminim)")
print("=" * 72)

text_psikiatrik = """
MENDIMI I EKSPERTEVE TE PSIKIATRISE
Bazuar në anamnezën e marrë nga deklarata verbale
dhe raportin social të QPS, konstatohet se...
"""
doc = extract_forensic_data(text_psikiatrik, "raport_psikiatrik.pdf")
print(f"doc_types: {doc.doc_type_hints}")

flags = run_forensic_detectors([doc], profile="judicial_decision")
for f in flags:
    print(f"  [{f.severity.upper()}] {f.rule_id}: {f.message[:100]}")

has_flag = any(f.rule_id == "psychiatric_basis_insufficient" for f in flags)
print(f"Ka psychiatric_basis flag: {has_flag}")

print("✓ TEST 6 PËRFUNDOI")


print("\n" + "=" * 72)
print("TË GJITHA TESTET PËRFUNDUAN")
print("=" * 72)