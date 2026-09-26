# check_suspects.py
from app.services.document_review.fact_extractor import (
    extract_suspects,
    build_fact_profile,
)

text = """
GRUPI I: USHTRIMI I NDIKIMIT

1. NAZLIE BALA — Zyrtare e Lartë në Kabinetin e Ministrisë së Drejtësisë
• Kualifikimi Ligjor Penal:
o Neni 424, par. 1 i KPRK-së: Ushtrimi i ndikimit;

GRUPI II: ZYRTARËT E SISTEMIT GJYQËSOR DHE PROKURORIAL

1. BUJAR DOBËRDOLANI — Gjyqtar në Gjykatën Themelore në Prishtinë, Departamenti i Përgjithshëm
• Kualifikimi Ligjor Penal:

2. SABIT SADIKAJ — Gjyqtar në Gjykatën Themelore në Prishtinë, Divizioni Penal
• Kualifikimi Ligjor Penal:

3. KOLEGJI I GJYKATËS SË APELIT: LUMNI SALLAUKA, ARDIAN AJVAZI, NORA BLLACA DULA
• Kualifikimi Ligjor Penal:

4. FIKRIJE SYLEJMANI — Prokurore në Prokurorinë Themelore në Prishtinë
• Kualifikimi Ligjor Penal:

5. HETUESI POLICOR I RASTIT — Zyrtar pranë Stacionit Policor "Jugu", Prishtinë
• Kualifikimi Ligjor Penal:

GRUPI III: PERSONELI MJEKËSOR DHE KLINIK I QKUK-së

1. DR. SAMIRE BRAINA — Mjeke Psikiatre në QKUK / Kryesuese e Ekipit të Ekspertëve
• Kualifikimi Ligjor Penal:

2. DR. TRINGË KRASNIQI — Mjeke Psikiatre në QKUK / Anëtare e Ekipit të Ekspertëve
• Kualifikimi Ligjor Penal:

3. M.SC. BESNIK KADRIU — Psikolog Klinik në QKUK / Anëtar i Ekipit të Ekspertëve
• Kualifikimi Ligjor Penal:

4. DR. MUHAMET KARAMETA — Mjek Psikiatër / Ekspert Gjyqësor
• Kualifikimi Ligjor Penal:
"""


print("=" * 60)
print("TEST extract_suspects")
print("=" * 60)
suspects = extract_suspects(text)
print(f"Total suspects: {len(suspects)}")
for s in suspects:
    name = s["name"]
    pos = s["position_hint"][:50]
    grp = s.get("group", "?")
    print(f"  [{grp}] {s['index']}. {name} — {pos}")

print()

print("=" * 60)
print("TEST build_fact_profile (me own_case_numbers bosh)")
print("=" * 60)
fp = build_fact_profile(text, source_document="test.docx", own_case_numbers=set())
print(f"  Suspects: {fp['stats']['total_suspects']}")
print(f"  Parties:  {fp['stats']['total_parties']}")
print(f"  Internal contradictions: {fp['stats']['internal_contradictions']}")
print(f"  Reported contradictions: {fp['stats']['reported_contradictions']}")