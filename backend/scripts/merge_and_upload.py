import json
import os
import glob
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv

# Load Environment Variables
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017")
DB_NAME = "juristi_knowledge"
COLLECTION_NAME = "verdicts_metadata"

# --- DOCKER AWARE PATH ---
# The script runs from /app, and our files are in /app/data
DATA_DIR = "/app/data"

def merge_and_upload():
    print("🔄 STARTING DATA FUSION PROTOCOL (DOCKER)...")
    
    # 1. Find all partial JSON files inside the data directory
    search_path = os.path.join(DATA_DIR, "kjc_*.json")
    files = glob.glob(search_path)
    
    if not files:
        print(f"❌ No data files found in {DATA_DIR} (kjc_*.json).")
        return

    print(f"   - Found {len(files)} files to merge: {files}")

    all_verdicts = []
    seen_urls = set()
    
    # 2. Merge Loop
    for filename in files:
        print(f"   - Processing {filename}...")
        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            for item in data:
                url = item.get("pdf_url")
                if url and url not in seen_urls:
                    seen_urls.add(url)
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
        
        try:
            # Clear old data to ensure a clean slate
            collection.delete_many({})
            result = collection.insert_many(all_verdicts)
            print(f"✅ SUCCESS! Uploaded {len(result.inserted_ids)} records to MongoDB.")
        except Exception as e:
            print(f"⚠️  Upload Failed: {e}")
            
if __name__ == "__main__":
    merge_and_upload()