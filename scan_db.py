# Phoenix Protocol: Atlas Database Scanner V2.0
import os
from dotenv import load_dotenv
from pymongo import MongoClient

def scan():
    load_dotenv("backend/.env")
    uri = os.getenv("DATABASE_URI")
    db_name = os.getenv("MONGO_DB_NAME", "advocatus_db")
    
    print(f"Connecting to Atlas...")
    client = MongoClient(uri)
    db = client[db_name]
    
    print("\n--- ATLAS DATABASE SCAN ---")
    
    # 1. Scan Vector Chunks
    if "user_vectors" in db.list_collection_names():
        count = db["user_vectors"].count_documents({})
        print(f"DATABASE: {db_name:<20} | Collection: user_vectors | Chunks: {count}")
    
    # 2. Scan Document Metadata Records (The visual cards)
    print("\n--- DOCUMENT METADATA RECORDS ---")
    if "documents" in db.list_collection_names():
        docs = list(db["documents"].find({}))
        if not docs:
            print("RESULT: No document records found in the database.")
        for d in docs:
            print(f"File: {d.get('file_name'):<40} | Status: {d.get('status'):<12} | ID: {str(d.get('_id'))}")
    else:
        print("RESULT: 'documents' collection does not exist.")

if __name__ == "__main__":
    scan()