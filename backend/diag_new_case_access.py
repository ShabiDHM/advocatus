# FILE: backend/diag_new_case_access.py
# DIAGNOSTIKUES — analizon case-in e ri + guest-in + rezultatin e query-t të aksesit.
import os
from bson import ObjectId
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()
client = MongoClient(os.environ["DATABASE_URI"])
db = client[os.environ.get("MONGO_DB_NAME", "advocatus_db")]

print("\n=== ALL USERS ===")
print("=" * 80)
for u in db.users.find({}):
    print(f"\n  _id                 = {u['_id']}")
    print(f"  email               = {u.get('email')}")
    print(f"  role                = {u.get('role')}")
    print(f"  org_access_level    = {u.get('org_access_level')!r}")
    print(f"  assigned_case_ids   = {u.get('assigned_case_ids')!r}")
    print(f"  assigned_user_ids   = {u.get('assigned_user_ids')!r}")
    print(f"  organization_id     = {u.get('organization_id')!r}")
    print(f"  org_id (legacy)     = {u.get('org_id')!r}")

print("\n\n=== ALL CASES ===")
print("=" * 80)
for c in db.cases.find({}):
    print(f"\n  _id                 = {c['_id']}")
    print(f"  title               = {c.get('title')}")
    print(f"  owner_id            = {c.get('owner_id')} (type={type(c.get('owner_id')).__name__})")
    print(f"  user_id             = {c.get('user_id')}")
    print(f"  org_id              = {c.get('org_id')} (type={type(c.get('org_id')).__name__})")
    print(f"  organization_id     = {c.get('organization_id')} (type={type(c.get('organization_id')).__name__})")
    print(f"  assigned_user_ids   = {c.get('assigned_user_ids')!r}")

print("\n\n=== SIMULIM — _build_case_access_query për çdo user ===")
print("=" * 80)

# Importo logjikën reale nga projekti
try:
    from app.models.user import UserInDB
    from app.services.case_service import _build_case_access_query

    for u in db.users.find({}):
        try:
            user_obj = UserInDB.model_validate(u)
            query = _build_case_access_query(user_obj)
            matched = list(db.cases.find(query, {"_id": 1, "title": 1, "org_id": 1}))
            print(f"\n  {u.get('email')} (role={u.get('role')}, level={u.get('org_access_level')!r})")
            print(f"    Query      = {query}")
            print(f"    Cases match= {len(matched)}")
            for m in matched:
                print(f"      → {m['_id']} | {m.get('title')} | org_id={m.get('org_id')}")
        except Exception as e:
            print(f"\n  {u.get('email')} → ERROR: {e}")
except Exception as e:
    print(f"\n  ⚠️  Nuk mund të ngarkohet _build_case_access_query: {e}")
    print("  (Sigurohu që ekzekuton nga folderi backend/ me .env të ngarkuar)")

client.close()