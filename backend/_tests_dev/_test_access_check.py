# FILE: backend/_test_access_check.py
# Verifikon qe Shabi Test (FULL) tani sheh Doberdolani
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from bson import ObjectId

load_dotenv()
db = MongoClient(os.getenv("DATABASE_URI"))[os.getenv("MONGO_DB_NAME", "advocatus_db")]

# Importon logjiken e njesise
import sys
sys.path.insert(0, ".")
from app.models.user import UserInDB
from app.services.case_service import _build_case_access_query

shabi_doc = db.users.find_one({"_id": ObjectId("6a8e129c02d1fd46ca5ab3a4")})
shabi = UserInDB.model_validate(shabi_doc)

print("=" * 70)
print("VERIFIKIM AKSESI - Shabi Test (FULL)")
print("=" * 70)
print(f"User: {shabi.email}")
print(f"org_id: {shabi.org_id}")
print(f"org_access_level: {shabi.org_access_level}")

# Nderto query
query = _build_case_access_query(shabi)
print(f"\nQuery: {query}")

# Provon te gjeje Doberdolani
target_case_id = ObjectId("6aac1f79ef09232ccbe1ba13")
query_with_case = _build_case_access_query(shabi, case_id=target_case_id)

case = db.cases.find_one(query_with_case)
if case:
    print(f"\n✅ Shabi Test SHEH case: {case.get('title')}")
    print(f"   _id: {case['_id']}")
    print(f"   owner: {case.get('owner_id')}")
    print(f"   org_id: {case.get('org_id')}")
else:
    print(f"\n❌ Shabi Test NUK sheh case-in target")

# Sa case sheh totalisht
total_visible = db.cases.count_documents(query)
print(f"\n📊 Case totalisht te dukshme per Shabi Test: {total_visible}")