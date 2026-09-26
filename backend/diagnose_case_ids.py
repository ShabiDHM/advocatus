# FILE: backend/diagnose_case_ids.py
# Verifikon si ruhen case_id në sub-collections.
# Ekzekuto: python diagnose_case_ids.py
# Fshi pas përdorimit.

from app.core.db import get_db_instance

db = get_db_instance()

COLLECTIONS = [
    "case_extractions",
    "case_synthesis",
    "case_chat_history",
    "case_cross_references",
]

CASE_ID_STR = "6ab5de695e5d9944239c1042"

print("=" * 78)
print(f"DIAGNOSTIKIM case_id në sub-collections (case={CASE_ID_STR})")
print("=" * 78)

for coll_name in COLLECTIONS:
    coll = db[coll_name]
    total = coll.count_documents({})
    print(f"\n### {coll_name} — gjithsej {total} dokument(e) në collection")

    if total == 0:
        print("    [BOSH]")
        continue

    # Kontrollo 3 sample
    samples = list(coll.find({}).limit(3))
    for i, doc in enumerate(samples, 1):
        cid = doc.get("case_id")
        cid_type = type(cid).__name__
        match_str = "MATCH ✓" if str(cid) == CASE_ID_STR else "NO MATCH"
        print(f"    [{i}] case_id={cid!r} (type={cid_type}) → {match_str}")

    # Kontrollo me variants
    print(f"\n    Kërko me str: case_id='{CASE_ID_STR}' → {coll.count_documents({'case_id': CASE_ID_STR})}")
    from bson import ObjectId
    if ObjectId.is_valid(CASE_ID_STR):
        print(f"    Kërko me ObjectId → {coll.count_documents({'case_id': ObjectId(CASE_ID_STR)})}")

print("\n" + "=" * 78)
print("PËRFUNDOI. Kopjo output-in.")
print("=" * 78)