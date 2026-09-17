# FILE: backend/test_role_conflict.py
# Teston zgjidhjen e konfliktit JUDGE vs PROSECUTOR.

from app.services.albanian_ner_service import ALBANIAN_NER_SERVICE

text = """
Prokuroresha Fikrije Sylejmani ka ngritur aktakuzën PP.II.nr. 122/24F
në Prokurorinë Themelore në Prishtinë.

Gjyqtari Bujar Dobërdolani vendosi në lëndën C.nr. 385/2024.

Gjyqtarët Lumni Sallauka, Ardian Ajvazi dhe Nora Bllaca Dula
konfirmuan aktvendimin CA.nr. 3120/2024.
"""

result = ALBANIAN_NER_SERVICE.extract_legal_entities(
    text=text,
    document_id="test_role_conflict",
    document_type="Kallëzim Penal",  # hint
)

print("=" * 70)
print("REZULTATI:")
print("=" * 70)
print(f"Total entities: {result['stats']['total_entities']}")
print(f"Role conflicts resolved: {result['stats']['role_conflicts_resolved']}")
print()

for label in ["PROSECUTOR", "JUDGE", "LAWYER", "COURT"]:
    entities = result["entities_by_type"].get(label, [])
    if entities:
        print(f"\n[{label}] ({len(entities)}):")
        for e in entities:
            print(f"   - {e['text']} (conf={e['confidence']})")
            if "role_conflict_resolved" in e:
                print(f"     ⚠️  CONFLICT RESOLVED: was {e['role_conflict_resolved']}")
                print(f"        votes: {e['role_conflict_votes']}")