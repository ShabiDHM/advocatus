import json
import os
from pymongo import MongoClient
from datetime import datetime

# --- DIRECT PATH CONFIGURATION ---
# We know the file is in /app/data inside the container
DATA_DIR = "/app/data"
# Let's target the largest, most important file directly
INPUT_FILE = os.path.join(DATA_DIR, "kjc_2025_part1.json") 
# Get MONGO_URI from environment, passed by Docker
MONGO_URI = os.getenv("MONGO_URI")

def direct_upload():
    print("🚀 STARTING DIRECT UPLOAD PROTOCOL...")

    if not MONGO_URI:
        print("❌ CRITICAL: MONGO_URI environment variable not found.")
        return

    if not os.path.exists(INPUT_FILE):
        print(f"❌ File not found inside container at: {INPUT_FILE}")
        # Let's see what IS in that folder
        if os.path.exists(DATA_DIR):
            print(f"   - Contents of {DATA_DIR}: {os.listdir(DATA_DIR)}")
        return

    print(f"   - Found data file: {INPUT_FILE}")

    # 1. Load Data
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"   - Loaded {len(data)} verdicts.")

    # 2. Process & Add Metadata
    all_verdicts = []
    for item in data:
        item["imported_at"] = datetime.utcnow()
        item["status"] = "indexed"
        all_verdicts.append(item)

    # 3. Connect & Upload
    try:
        client = MongoClient(MONGO_URI)
        db = client["juristi_knowledge"]
        collection = db["verdicts_metadata"]

        print("   - Connected to MongoDB. Clearing old data...")
        collection.delete_many({}) # Start fresh

        print(f"   - Inserting {len(all_verdicts)} new records...")
        result = collection.insert_many(all_verdicts)
        print(f"\n✅ SUCCESS! Uploaded {len(result.inserted_ids)} records.")

    except Exception as e:
        print(f"\n❌ DATABASE ERROR: {e}")

if __name__ == "__main__":
    direct_upload()