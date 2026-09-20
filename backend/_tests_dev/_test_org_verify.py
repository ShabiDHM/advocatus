# FILE: backend/_test_org_verify.py
# Verifikues i gjendjes së DB për test org end-to-end
# Përdorimi:
#   python _test_org_verify.py state       # gjendja aktuale
#   python _test_org_verify.py orphans     # gjej vektorë orphan
#   python _test_org_verify.py case <id>   # inspekto një case
#   python _test_org_verify.py user <id>   # inspekto një user

import os
import sys
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv()

uri = os.getenv("DATABASE_URI")
db_name = os.getenv("MONGO_DB_NAME", "advocatus_db")

if not uri:
    print("ERROR: DATABASE_URI nuk eshte konfiguruar ne .env")
    sys.exit(1)

db = MongoClient(uri)[db_name]


def cmd_state():
    print("=" * 70)
    print("GJENDJA AKTUALE E DATABAZES")
    print("=" * 70)

    print("\nUSERS ME ORG (max 10):")
    for u in db.users.find({"org_id": {"$exists": True, "$ne": None}}).limit(10):
        print(f"  {u['_id']} | {u.get('email', '?')} | org={u.get('org_id')} | "
              f"role={u.get('role', '?')} | access={u.get('org_access_level', '?')}")

    print("\nCASES (max 10):")
    for c in db.cases.find().sort("created_at", -1).limit(10):
        print(f"  {c['_id']} | {c.get('title', '?')} | "
              f"owner={c.get('owner_id')} | org={c.get('org_id')}")

    print("\nKOLEKSIONET:")
    for coll in ["users", "cases", "documents", "media_evidence", "user_vectors",
                 "findings", "calendar_events", "alerts", "chat_feedback",
                 "case_orders", "archives"]:
        try:
            n = db[coll].count_documents({})
            print(f"  {coll:20s}: {n}")
        except Exception as e:
            print(f"  {coll:20s}: ERROR - {e}")


def cmd_orphans():
    print("=" * 70)
    print("KERKIM PER VEKTORE ORPHAN")
    print("=" * 70)

    vector_doc_ids = db.user_vectors.distinct("document_id")
    print(f"\nuser_vectors: {len(vector_doc_ids)} document_id unike")

    orphans = []
    for doc_id_str in vector_doc_ids:
        if not doc_id_str:
            continue
        doc_id_str = str(doc_id_str)
        
        found = False
        try:
            if ObjectId.is_valid(doc_id_str):
                if db.documents.find_one({"_id": ObjectId(doc_id_str)}, {"_id": 1}):
                    found = True
                if not found and db.media_evidence.find_one({"_id": ObjectId(doc_id_str)}, {"_id": 1}):
                    found = True
        except Exception:
            pass
        
        if not found:
            orphans.append(doc_id_str)

    print(f"\nORPHAN document_ids ({len(orphans)}):")
    if not orphans:
        print("  OK - Asnje orphan i gjetur!")
    else:
        for oid in orphans[:20]:
            n = db.user_vectors.count_documents({"document_id": oid})
            print(f"  WARN: {oid} -> {n} chunks orphan")


def cmd_case(case_id):
    print(f"CASE: {case_id}")
    try:
        c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
        case = db.cases.find_one({"_id": c_oid})
        if not case:
            print(f"  Nuk u gjet")
            return
        print(f"  Title: {case.get('title')}")
        print(f"  Owner: {case.get('owner_id')}")
        print(f"  Org:   {case.get('org_id')}")
        
        any_q = {"case_id": {"$in": [c_oid, case_id]}}
        print(f"\n  Documents:       {db.documents.count_documents(any_q)}")
        print(f"  Media evidence:  {db.media_evidence.count_documents(any_q)}")
        print(f"  Findings:        {db.findings.count_documents(any_q)}")
        print(f"  Calendar:        {db.calendar_events.count_documents(any_q)}")
        print(f"  Alerts:          {db.alerts.count_documents(any_q)}")
        
        vq = {"case_id": {"$in": [c_oid, case_id]}}
        print(f"  User vectors:    {db.user_vectors.count_documents(vq)}")
    except Exception as e:
        print(f"  Gabim: {e}")


def cmd_user(user_id):
    print(f"USER: {user_id}")
    try:
        u_oid = ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id
        user = db.users.find_one({"_id": u_oid})
        if not user:
            print(f"  Nuk u gjet (mund te jete fshire)")
            return
        print(f"  Email: {user.get('email')}")
        print(f"  Org:   {user.get('org_id')}")
        print(f"  Role:  {user.get('role')}")
        
        owner_q = {"$or": [{"owner_id": u_oid}, {"owner_id": user_id},
                           {"user_id": u_oid}, {"user_id": user_id}]}
        print(f"\n  Cases:        {db.cases.count_documents(owner_q)}")
        print(f"  User vectors: {db.user_vectors.count_documents({'owner_id': user_id})}")
    except Exception as e:
        print(f"  Gabim: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    cmd = sys.argv[1]
    if cmd == "state":
        cmd_state()
    elif cmd == "orphans":
        cmd_orphans()
    elif cmd == "case":
        if len(sys.argv) < 3:
            print("Kerkohet case_id")
            sys.exit(1)
        cmd_case(sys.argv[2])
    elif cmd == "user":
        if len(sys.argv) < 3:
            print("Kerkohet user_id")
            sys.exit(1)
        cmd_user(sys.argv[2])
    else:
        print(__doc__)