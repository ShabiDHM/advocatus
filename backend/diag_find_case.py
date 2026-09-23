# FILE: backend/diag_find_case.py
# DIAGNOSTIKUES V3 — gjej ku ndodhet case_id 6ab32fdb1a5668dd074d9359
# dhe çfarë dokumentesh ekzistojnë në DB.

import os
from bson import ObjectId
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()
client = MongoClient(os.environ["DATABASE_URI"])
db = client[os.environ.get("MONGO_DB_NAME", "advocatus_db")]

TARGET_ID = "6ab32fdb1a5668dd074d9359"

print(f"\n📦 DB: {db.name}")
print(f"🎯 Target ID: {TARGET_ID}\n")

# 1) Listo të gjitha koleksionet
collections = db.list_collection_names()
print(f"📚 Koleksionet ({len(collections)}):")
for c in sorted(collections):
    count = db[c].estimated_document_count()
    print(f"  • {c:40s} ({count} docs)")

# 2) Kërko TARGET_ID në ÇDO koleksion
print(f"\n🔎 Duke kërkuar '{TARGET_ID}' në të gjitha koleksionet...\n")

target_oid = ObjectId(TARGET_ID)

for c in collections:
    coll = db[c]
    # Kërko si _id
    if coll.find_one({"_id": target_oid}):
        print(f"  ✅ FOUND as _id në: {c}")

    # Kërko si case_id (string ose ObjectId)
    hit_str = coll.find_one({"case_id": TARGET_ID})
    hit_oid = coll.find_one({"case_id": target_oid})
    if hit_str or hit_oid:
        count = coll.count_documents({"$or": [{"case_id": TARGET_ID}, {"case_id": target_oid}]})
        print(f"  ✅ FOUND as case_id në: {c} ({count} docs)")

    # Kërko si document_id
    if coll.find_one({"document_id": TARGET_ID}):
        print(f"  ✅ FOUND as document_id në: {c}")

# 3) Sa dokumente ka GJITHSEJ dhe kush është owner
print(f"\n📄 Koleksioni 'documents' — total: {db.documents.count_documents({})}")
print("   ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
for d in db.documents.find({}).limit(20):
    print(f"  _id       = {d['_id']}")
    print(f"  file_name = {d.get('file_name')}")
    print(f"  case_id   = {d.get('case_id')} (type={type(d.get('case_id')).__name__})")
    print(f"  owner_id  = {d.get('owner_id')}")
    print(f"  status    = {d.get('status')!r}")
    print("  ---")

# 4) Sa cases ka gjithsej
print(f"\n📁 Koleksioni 'cases' — total: {db.cases.count_documents({})}")
print("   ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
for c in db.cases.find({}).limit(20):
    print(f"  _id       = {c['_id']}")
    print(f"  title     = {c.get('title')}")
    print(f"  owner_id  = {c.get('owner_id')}")
    print(f"  org_id    = {c.get('org_id')}")
    print(f"  case_number = {c.get('case_number')}")
    print("  ---")

client.close()