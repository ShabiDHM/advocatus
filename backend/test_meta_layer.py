# test_meta_layer.py
# Test për meta-layer validation në hallucination_checker V1.16.1

from app.services.document_review.hallucination_checker import (
    HallucinationChecker,
    _normalize_law_name,
)


# ═══════════════════════════════════════════════════════════════════════════
# TEST 1 — Normalizim i emrave të ligjeve (trajtat rasore)
# ═══════════════════════════════════════════════════════════════════════════

print("=" * 60)
print("Test 1 — Normalizim i emrave:")
print("=" * 60)

test_names = [
    "Ligjit për Familjen",
    "Ligji për Familjen",
    "Ligjin për Familjen",
    "Kodin Penal",
    "Kodi Penal",
    "Kodit Penal",
    "Ligjin për Marrëdhëniet e Detyrimeve",
    "Ligji për Marrëdhëniet e Detyrimeve",
]

for name in test_names:
    normalized = _normalize_law_name(name)
    print(f"  '{name}' → '{normalized}'")

print()


# ═══════════════════════════════════════════════════════════════════════════
# TEST 2 — Meta-layer checks
# ═══════════════════════════════════════════════════════════════════════════

print("=" * 60)
print("Test 2 — Meta-layer checks:")
print("=" * 60)

fake_citation = {
    'laws_by_number': [],
    'articles': [],
    'case_numbers': [],
    'abbreviations': ['KPRK', 'KPPRK'],
}
fake_fact = {'dates': []}
fake_ver = {'laws_by_number': [], 'articles': [], 'case_numbers': []}

c = HallucinationChecker(fake_citation, fake_fact, fake_ver)

text = (
    'Sipas Nenit 15 të Ligjit për Familjen (Nr. 04/L-077), '
    'zëvendëso KPRK me KPK.'
)

report = c.check_section('test', text)

print(f"Input: {text}")
print()
print(f"Issues: {len(report['issues'])}")
print()

for i in report['issues']:
    print(f"  [{i['severity']}] {i['type']}: {i['value']}")
    print(f"     {i['message']}")
    print()