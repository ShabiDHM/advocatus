# FILE: backend/probe_docs.py
# Zbulon ku ruhen dokumentet në MongoDB.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.db import get_db
from bson import ObjectId

db = get_db()
case_id = "6ab42c76b6e7f311be56c2ae"
c_oid = ObjectId(case_id)

print("=" * 70)
print("PROBE — ku ruhen dokumentet?")
print("=" * 70)

# 1. Emrat e koleksioneve
print("\n📁 Koleksionet në DB:")
for name in sorted(db.list_collection_names()):
    print(f"   - {name}")

# 2. Kontrollo çdo koleksion për fusha 'case_id' ose 'case'
print("\n🔎 Koleksionet me referencë ndaj case:")
for name in db.list_collection_names():
    if name == "system.indexes":
        continue
    col = db[name]
    try:
        # Provo ObjectId
        n1 = col.count_documents({"case_id": c_oid})
        # Provo string
        n2 = col.count_documents({"case_id": case_id})
        # Provo 'case'
        n3 = col.count_documents({"case": c_oid})
        # Provo 'caseId'
        n4 = col.count_documents({"caseId": c_oid})
        # Provo 'parent_id'
        n5 = col.count_documents({"parent_id": case_id})
        total = n1 + n2 + n3 + n4 + n5
        if total > 0:
            print(f"   ✓ {name}: case_id(OID)={n1}, case_id(str)={n2}, "
                  f"case(OID)={n3}, caseId(OID)={n4}, parent_id(str)={n5}")
    except Exception as e:
        print(f"   ⚠️ {name}: {e}")

# 3. Sample nga koleksionet kryesore
print("\n📄 Shembull nga 'documents' (5):")
for d in db["documents"].find({}).limit(5):
    keys = list(d.keys())
    print(f"   keys={keys[:8]}")
    print(f"   case_id={d.get('case_id')} type={type(d.get('case_id')).__name__}")
    print(f"   file_name={d.get('file_name') or d.get('filename')}")
    print()

print("\n📄 Shembull nga 'case_documents' (5):")
if "case_documents" in db.list_collection_names():
    for d in db["case_documents"].find({}).limit(5):
        print(f"   {list(d.keys())[:8]}")
else:
    print("   (nuk ekziston)")

print("\n📋 Struktura e case-it target:")
case = db.cases.find_one({"_id": c_oid})
if case:
    print(f"   keys={list(case.keys())}")
    print(f"   documents in case: {len(case.get('documents') or [])}")