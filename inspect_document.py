# Phoenix Protocol: Document Type Inspector (Type-Safe V2.1)
import os
import sys
from dotenv import load_dotenv
from pymongo import MongoClient

print("--- [PHOENIX] Starting Document Inspector ---")

def inspect():
    load_dotenv("backend/.env")
    uri = os.getenv("DATABASE_URI")
    db_name = os.getenv("MONGO_DB_NAME", "advocatus_db")
    
    client = MongoClient(uri)
    db = client[db_name]
    
    doc = db.documents.find_one({"file_name": "Seanca e par Get_com.pdf"})
    
    if not doc:
        print("RESULT: Document record not found.")
        return
        
    print("\n--- DOCUMENT RECORD DETAIL ---")
    print(f"File Name: {doc.get('file_name')}")
    print(f"Status:    {doc.get('status')}")
    print("-" * 40)
    
    # We convert type(...) to str() before formatting to prevent the Pylance/Runtime crash
    id_type = str(type(doc.get('_id')))
    case_type = str(type(doc.get('case_id')))
    owner_type = str(type(doc.get('owner_id')))
    
    print(f"Key: '_id'       | Type: {id_type:<30} | Value: {doc.get('_id')}")
    print(f"Key: 'case_id'   | Type: {case_type:<30} | Value: {doc.get('case_id')} (Raw: {repr(doc.get('case_id'))})")
    print(f"Key: 'owner_id'  | Type: {owner_type:<30} | Value: {doc.get('owner_id')} (Raw: {repr(doc.get('owner_id'))})")

if __name__ == "__main__":
    inspect()