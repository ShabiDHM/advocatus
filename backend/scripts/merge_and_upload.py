import json
import os
import glob
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv

# Load Environment Variables
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = "juristi_knowledge"
COLLECTION_NAME = "verdicts_metadata"

def merge_and_upload():
    print("🔄 STARTING DATA FUSION PROTOCOL...")
    
    # 1. Find all partial JSON files
    # We look for anything starting with 'kjc_' and ending in '.json'
    files = glob.glob("kjc_*.json")
    
    if not files:
        print("❌ No data files found (kjc_*.json).")
        return

    print(f"   - Found {len(files)} files to merge: {files}")

    all_verdicts = []
    seen_urls = set() # To prevent duplicates
    
    # 2. Merge Loop
    for filename in files:
        print(f"   - Processing {filename}...")
        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            for item in data:
                url = item.get("pdf_url")
                # Deduplication Strategy: Use PDF URL as unique key
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    
                    # Add Metadata
                    item["imported_at"] = datetime.utcnow()
                    item["status"] = "indexed" 
                    all_verdicts.append(item)
                    
        except Exception as e:
            print(f"     ⚠️ Error reading {filename}: {e}")

    print(f"   - Total Unique Verdicts: {len(all_verdicts)}")

    # 3. Database Upload
    if all_verdicts:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]
        
        # Optional: Clear old data to avoid massive duplicates during testing
        # collection.delete_many({}) 
        
        # Use bulk write for speed
        try:
            # We use insert_many but wrap in try/catch in case of ID conflicts
            result = collection.insert_many(all_verdicts)
            print(f"✅ SUCCESS! Uploaded {len(result.inserted_ids)} records to MongoDB.")
        except Exception as e:
            print(f"⚠️  Upload warning (some duplicates might exist): {e}")
            
    else:
        print("⚠️  No valid data found to merge.")

if __name__ == "__main__":
    merge_and_upload()