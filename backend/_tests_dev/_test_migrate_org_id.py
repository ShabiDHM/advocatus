# FILE: backend/_test_migrate_org_id.py
# Migrim: vendos org_id = owner._id për case-t e ORGANIZATION userave pa org_id
# Shenim: DISA case mund te jene personale (jo te duhet te kene org_id).
# Kontrollo listen e para se te vazhdosh.

import os
from dotenv import load_dotenv
from pymongo import MongoClient
from bson import ObjectId

load_dotenv()
db = MongoClient(os.getenv("DATABASE_URI"))[os.getenv("MONGO_DB_NAME", "advocatus_db")]

print("=" * 70)
print("MIGRIM: org_id per case-t e ORGANIZATION userave")
print("=" * 70)

# 1. Gjej te gjithe ORGANIZATION userat
org_users = list(db.users.find({"account_type": "ORGANIZATION"}))
org_map = {u["_id"]: u for u in org_users}
print(f"\nORGANIZATION users: {len(org_users)}")

# 2. Gjej case-t me org_id=None dhe owner_id ne org_users
candidates = list(db.cases.find({
    "org_id": None,
    "owner_id": {"$in": list(org_map.keys())}
}))

print(f"\nCase-t kandidate per migrim (org_id=None, owner ORGANIZATION): {len(candidates)}")
for c in candidates:
    owner = org_map.get(c["owner_id"])
    print(f"  {c['_id']} | {c.get('title', '?')} | owner={owner.get('email', '?')}")

# 3. Konfirmo
if not candidates:
    print("\nAsnje case per migrim. Dalje.")
    exit(0)

confirm = input("\nVazhdojme me migrimin? (shkruaj 'PO'): ").strip()
if confirm != "PO":
    print("Anuluar.")
    exit(0)

# 4. Migro
updated = 0
for c in candidates:
    result = db.cases.update_one(
        {"_id": c["_id"]},
        {"$set": {
            "org_id": c["owner_id"],
            "updated_at": c.get("created_at") or c.get("updated_at")
        }}
    )
    if result.modified_count:
        updated += 1
        print(f"  OK: {c['_id']} -> org_id = {c['owner_id']}")

print(f"\nMigruar: {updated}/{len(candidates)}")