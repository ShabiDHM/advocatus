import pymongo
import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)
load_dotenv()

# Automatically reads DATABASE_URI from your .env file
MONGO_URL = (
    os.getenv("DATABASE_URI") or
    os.getenv("MONGODB_URL") or 
    os.getenv("MONGO_URI") or 
    os.getenv("MONGODB_URI")
)

DB_NAME = os.getenv("MONGO_DB_NAME", "advocatus_db")
TARGET_EMAIL = "shabanbala@gmail.com"

def purge_everything():
    url = MONGO_URL
    if not url:
        print("⚠️ DATABASE_URI not found automatically in .env.")
        url = input("👉 Please paste your MongoDB Atlas connection string (mongodb+srv://...): ").strip()

    if not url:
        print("❌ Error: No connection string provided.")
        return

    print(f"🗑️ Connecting to MongoDB Atlas (DB: {DB_NAME}) and deep purging '{TARGET_EMAIL}'...")
    client = pymongo.MongoClient(url, serverSelectionTimeoutMS=15000)
    db = client[DB_NAME]
    
    for col_name in db.list_collection_names():
        col = db[col_name]
        try:
            res1 = col.delete_many({"email": TARGET_EMAIL})
            if res1.deleted_count > 0:
                print(f"✅ Deleted {res1.deleted_count} doc(s) by email from '{col_name}'")
            
            res2 = col.delete_many({"username": TARGET_EMAIL})
            if res2.deleted_count > 0:
                print(f"✅ Deleted {res2.deleted_count} doc(s) by username from '{col_name}'")
        except Exception as e:
            print(f"⚠️ Could not check collection '{col_name}': {e}")
            
    print("✨ Deep purge complete across all collections in MongoDB Atlas!")

if __name__ == "__main__":
    purge_everything()