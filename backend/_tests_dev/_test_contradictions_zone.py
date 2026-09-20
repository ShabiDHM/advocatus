# FILE: backend/_tests_dev/_test_contradictions_zone.py
"""
Teston zone-aware contradictions (V3.0).
Skenari: false positive i raportuar ne mandat.
"""
from app.services.document_review.fact_extractor import build_fact_profile

DOC = """
REPUBLIKA E KOSOVES
GJYKATA THEMELORE NE PRISHTINE
Nr. 123/2024
Date: 15.03.2024

FAKTET:
Me 10.01.2024, i pandehuri, pas 1 muaj e gjysem grindje te vazhdueshme me
bashkeshorten, ka shkaktuar lendime te renda.

ARSYETIMI:
Nga provat e administruara, gjykata konstaton se vepra penale eshte provuar.
PËR KËTO ARSYE

VENDOSI:
I. I pandehuri denohet me 6 muaj burg.

PROPOZIMI I PROKURORISE:
Propozon denimin me 12 muaj burg.
"""

profile = build_fact_profile(DOC)
print("=" * 60)
print(f"Contradictions: {profile['stats']['total_contradictions']}")
print("=" * 60)
for c in profile["contradictions"]:
    print(f"  type={c['type']} zone={c.get('zone', '-')} "
          f"unit={c['unit']} values={c['values']}")
print("=" * 60)

# PRITET:
# - Contradictions: 0
# - "1 muaj" -> zone=facts
# - "6 muaj" -> zone=dispositive
# - "12 muaj" -> zone=proposal
# Nuk ka dy vlera te ndryshme brenda te njejtes zone.