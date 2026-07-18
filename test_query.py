# Phoenix Protocol: Query Combinational Tester
import os
import sys
from dotenv import load_dotenv
from pymongo import MongoClient
from bson import ObjectId

def test_queries():
    load_dotenv("backend/.env")
    uri = os.getenv("DATABASE_URI")
    db_name = os.getenv("MONGO_DB_NAME", "advocatus_db")
    
    client = MongoClient(uri)
    db = client[db_name]
    
    case_id_str = "6a5970311f058763c47904e9"
    user_id_str = "6a590293c2808c18abb3bf72"
    
    print("--- Running Combinational Query Test ---")
    
    # Query 1: Both as ObjectIds
    q1 = db.documents.find_one({"case_id": ObjectId(case_id_str), "owner_id": ObjectId(user_id_str)})
    print(f"Query 1: (Case: ObjectId, Owner: ObjectId) -> Found: {q1 is not None}")

    # Query 2: Case as ObjectId, Owner as String
    q2 = db.documents.find_one({"case_id": ObjectId(case_id_str), "owner_id": user_id_str})
    print(f"Query 2: (Case: ObjectId, Owner: String)    -> Found: {q2 is not None}")

    # Query 3: Case as String, Owner as ObjectId
    q3 = db.documents.find_one({"case_id": case_id_str, "owner_id": ObjectId(user_id_str)})
    print(f"Query 3: (Case: String,   Owner: ObjectId) -> Found: {q3 is not None}")

    # Query 4: Both as Strings
    q4 = db.documents.find_one({"case_id": case_id_str, "owner_id": user_id_str})
    print(f"Query 4: (Case: String,   Owner: String)   -> Found: {q4 is not None}")

if __name__ == "__main__":
    test_queries()