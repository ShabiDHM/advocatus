import json
import os
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv

# Load Env
load_dotenv()

# Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = "juristi_knowledge"
COLLECTION_NAME = "verdicts_metadata"
INPUT_FILE = "kjc_master_dataset_2024.json"

def import_data():
    print("📥 STARTING DATABASE INGESTION...")
    
    # 1. Check for File
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Waiting for file... '{INPUT_FILE}' not found in backend folder.")
        print("   (Keep waiting for the browser to finish!)")
        return

    # 2. Connect to DB
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]
    
    # 3. Load JSON
    print(f"   - Reading {INPUT_FILE}...")
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    print(f"   - Found {len(data)} verdicts.")

    # 4. Processing & Cleaning
    clean_docs = []
    print("   - Processing records...")
    
    for item in data:
        # Create a clean database object
        doc = {
            "case_number": item.get("case_number"),
            "judge_name": item.get("judge"),
            "court_name": item.get("court"),
            "date_text": item.get("date"),
            "pdf_url": item.get("pdf_url"),
            "year": 2024,
            "status": "indexed", # We have the link, but haven't read the PDF yet
            "imported_at": datetime.utcnow()
        }
        clean_docs.append(doc)

    # 5. Bulk Insert (Fast)
    if clean_docs:
        # Option: specific unique index to prevent duplicates?
        # For now, we wipe and reload for purity, or just insert
        # collection.delete_many({"year": 2024}) # Uncomment to clear old 2024 data
        
        result = collection.insert_many(clean_docs)
        print(f"✅ SUCCESS! Inserted {len(result.inserted_ids)} documents into MongoDB.")
        print(f"   - Collection: {DB_NAME}.{COLLECTION_NAME}")
    else:
        print("⚠️  No records found to insert.")

if __name__ == "__main__":
    import_data()