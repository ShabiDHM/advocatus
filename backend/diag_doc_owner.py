# FILE: backend/diag_doc_owner.py
# DIAGNOSTIKUES V2 — lexon DATABASE_URI / MONGO_DB_NAME nga .env
# Kontrollon owner_id / case_id / status te dokumentet për një case.

import os
from bson import ObjectId
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

uri = os.environ["DATABASE_URI"]
db_name = os.environ.get("MONGO_DB_NAME", "advocatus_db")

client = MongoClient(uri)
db = client[db_name]

CASE_ID = "6ab32fdb1a5668dd074d9359"  # nga URL-ja e screenshot-it

print(f"\n🔍 CASE_ID: {CASE_ID}")
print(f"📦 DB     : {db_name}")
case_oid = ObjectId(CASE_ID) if ObjectId.is_valid(CASE_ID) else CASE_ID

# 1) Dokumentet e case-it (PA filter owner)
docs = list(db.documents.find({
    "$or": [{"case_id": CASE_ID}, {"case_id": case_oid}]
}))
print(f"\n📄 Dokumentet e case-it (PA filter owner): {len(docs)}")
for d in docs:
    print(f"  _id        = {d['_id']}")
    print(f"  file_name  = {d.get('file_name')}")
    print(f"  case_id    = {d.get('case_id')} (type={type(d.get('case_id')).__name__})")
    print(f"  owner_id   = {d.get('owner_id')} (type={type(d.get('owner_id')).__name__})")
    print(f"  status     = {d.get('status')!r}")
    has_text = bool(d.get('content') or d.get('extracted_text') or d.get('text'))
    print(f"  has_text   = {has_text}")
    print("  ---")

# 2) Case owner
case = db.cases.find_one({"_id": case_oid})
if case:
    print(f"\n📁 Case owner_id = {case.get('owner_id')} (type={type(case.get('owner_id')).__name__})")
    print(f"   Case org_id   = {case.get('org_id')}")
    print(f"   Case user_id  = {case.get('user_id')}")
else:
    print(f"\n⚠️  Case {CASE_ID} NUK u gjet në koleksionin 'cases'")

# 3) Users
print(f"\n👥 Users në DB:")
for u in db.users.find({}, {"_id": 1, "email": 1, "org_id": 1}):
    print(f"  {u['_id']} | {u.get('email')} | org={u.get('org_id')}")

client.close()