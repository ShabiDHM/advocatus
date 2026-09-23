# FILE: backend/diag_guest_access.py
# DIAGNOSTIKUES V2 — pa emoji (cp1252 safe).
import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()
client = MongoClient(os.environ["DATABASE_URI"])
db = client[os.environ.get("MONGO_DB_NAME", "advocatus_db")]

print("\n=== USERS — access model ===")
print("=" * 80)
for u in db.users.find({}, {"email": 1, "org_access_level": 1, "assigned_case_ids": 1, "organization_id": 1, "org_id": 1}):
    print(f"\n  _id              = {u['_id']}")
    print(f"  email            = {u.get('email')}")
    print(f"  org_access_level = {u.get('org_access_level')!r}")
    print(f"  assigned_case_ids= {u.get('assigned_case_ids')!r}")
    print(f"  organization_id  = {u.get('organization_id')!r}")
    print(f"  org_id (legacy)  = {u.get('org_id')!r}")

print("\n" + "=" * 80)
print("\n=== CASES — owner/org/assigned ===")
print("=" * 80)
for c in db.cases.find({}, {"title": 1, "owner_id": 1, "org_id": 1, "organization_id": 1, "assigned_user_ids": 1}):
    print(f"\n  _id              = {c['_id']}")
    print(f"  title            = {c.get('title')}")
    print(f"  owner_id         = {c.get('owner_id')}")
    print(f"  org_id           = {c.get('org_id')}")
    print(f"  organization_id  = {c.get('organization_id')}")
    print(f"  assigned_user_ids= {c.get('assigned_user_ids')!r}")

client.close()