# -*- coding: utf-8 -*-
"""Fikson case-in test duke konvertuar org_id ne ObjectId."""
from bson import ObjectId
from app.core.db import get_db

db = get_db()

case_id = "6ab32fcb1a5668dd074d9359"
org_id_str = "6a79133349ee7ee103bbeefa"
org_oid = ObjectId(org_id_str)

case = db["cases"].find_one({"_id": ObjectId(case_id)})
if not case:
    print(f"❌ Case {case_id} nuk gjendet!")
    exit(1)

print("=== PARA ===")
print(f"  org_id:          {case.get('org_id')} ({type(case.get('org_id')).__name__})")
print(f"  organization_id: {case.get('organization_id')} ({type(case.get('organization_id')).__name__})")

# Fixo
result = db["cases"].update_one(
    {"_id": ObjectId(case_id)},
    {"$set": {
        "org_id": org_oid,
        "organization_id": org_oid,
    }}
)
print(f"\n✅ Modified: {result.modified_count}")

# Verifiko
case_after = db["cases"].find_one({"_id": ObjectId(case_id)})
print("\n=== PAS ===")
print(f"  org_id:          {case_after.get('org_id')} ({type(case_after.get('org_id')).__name__})")
print(f"  organization_id: {case_after.get('organization_id')} ({type(case_after.get('organization_id')).__name__})")