# FILE: backend/fix_case_org.py
# FIX ONE-OFF — vendos org_id/organization_id për case-at që kanë owner me org.
import os
from bson import ObjectId
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()
client = MongoClient(os.environ["DATABASE_URI"])
db = client[os.environ.get("MONGO_DB_NAME", "advocatus_db")]

print("\n=== FIX — case me org_id=None, owner ka org ===\n")

fixed_count = 0

for case in db.cases.find({"$or": [{"org_id": None}, {"organization_id": None}]}):
    owner_id = case.get("owner_id") or case.get("user_id")
    if not owner_id:
        continue

    owner = db.users.find_one({"_id": owner_id})
    if not owner:
        print(f"  ⚠️  Case {case['_id']}: owner {owner_id} nuk u gjet")
        continue

    # Lexo org_id ose organization_id nga owner
    owner_org = owner.get("organization_id") or owner.get("org_id")
    if not owner_org:
        print(f"  ⚠️  Case {case['_id']}: owner ka pa org")
        continue

    # Konverto në ObjectId
    if isinstance(owner_org, str) and ObjectId.is_valid(owner_org):
        owner_org = ObjectId(owner_org)

    result = db.cases.update_one(
        {"_id": case["_id"]},
        {"$set": {
            "org_id": owner_org,
            "organization_id": owner_org,
        }}
    )
    if result.modified_count:
        print(f"  ✅ Case {case['_id']} ({case.get('title')}) → org_id={owner_org}")
        fixed_count += 1

print(f"\n✅ Total fixed: {fixed_count}\n")
client.close()